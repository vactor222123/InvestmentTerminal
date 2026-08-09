"""
Knowledge evidence provenance rules.

These rules validate lineage quality without resolving or mutating source
evidence. Persistence/repository verification belongs to later application
boundaries.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Iterable

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)


@dataclass(frozen=True, slots=True)
class KnowledgeProvenanceAssessment:
    """Immutable assessment of one knowledge record's evidence lineage."""

    status: str
    evidence_count: int
    checksum_backed_count: int
    canonical_snapshot_count: int
    derived_evidence_count: int
    warnings: tuple[str, ...]

    COMPLETE: ClassVar[str] = "COMPLETE"
    PARTIAL: ClassVar[str] = "PARTIAL"

    def __post_init__(self) -> None:
        if self.status not in (self.COMPLETE, self.PARTIAL):
            raise ValueError(
                "status must be COMPLETE or PARTIAL"
            )
        for field_name in (
            "evidence_count",
            "checksum_backed_count",
            "canonical_snapshot_count",
            "derived_evidence_count",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )
        if self.canonical_snapshot_count + self.derived_evidence_count != self.evidence_count:
            raise ValueError(
                "canonical_snapshot_count + derived_evidence_count "
                "must equal evidence_count"
            )
        if self.checksum_backed_count > self.evidence_count:
            raise ValueError(
                "checksum_backed_count must not exceed evidence_count"
            )
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.warnings):
            raise ValueError("warnings must contain non-empty strings")

    @property
    def fully_checksum_backed(self) -> bool:
        return (
            self.evidence_count > 0
            and self.checksum_backed_count == self.evidence_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "evidence_count": self.evidence_count,
            "checksum_backed_count": self.checksum_backed_count,
            "canonical_snapshot_count": self.canonical_snapshot_count,
            "derived_evidence_count": self.derived_evidence_count,
            "fully_checksum_backed": self.fully_checksum_backed,
            "warnings": list(self.warnings),
        }


class KnowledgeEvidenceProvenanceService:
    """
    Validate knowledge evidence lineage without performing repository I/O.

    Rules:
    - HISTORICAL_SNAPSHOT evidence must carry the source archive SHA-256.
    - derived evidence may be referenced without an archive checksum because
      it is rebuildable and not itself canonical archive bytes.
    - no evidence observation may occur after the knowledge record was
      generated.
    - evidence identity ordering is preserved and must already be unique
      through KnowledgeRecord validation.
    """

    CANONICAL_SNAPSHOT = "HISTORICAL_SNAPSHOT"

    WARNING_DERIVED_ONLY = (
        "Knowledge lineage contains no checksum-backed canonical historical "
        "snapshot; derived evidence is traceable but rebuildable"
    )
    WARNING_NOT_FULLY_CHECKSUM_BACKED = (
        "Not every evidence reference is checksum-backed; this is expected "
        "for rebuildable derived evidence"
    )

    def assess(
        self,
        record: KnowledgeRecord,
    ) -> KnowledgeProvenanceAssessment:
        if not isinstance(record, KnowledgeRecord):
            raise TypeError(
                "record must be a KnowledgeRecord"
            )

        self.validate_evidence(
            record.evidence,
            generated_at=record.generated_at,
        )

        canonical = tuple(
            item
            for item in record.evidence
            if item.evidence_type == self.CANONICAL_SNAPSHOT
        )
        derived = tuple(
            item
            for item in record.evidence
            if item.evidence_type != self.CANONICAL_SNAPSHOT
        )
        checksum_backed = tuple(
            item
            for item in record.evidence
            if item.checksum_sha256 is not None
        )

        warnings: list[str] = []
        if not canonical:
            warnings.append(
                self.WARNING_DERIVED_ONLY
            )
        if len(checksum_backed) != len(record.evidence):
            warnings.append(
                self.WARNING_NOT_FULLY_CHECKSUM_BACKED
            )

        status = (
            KnowledgeProvenanceAssessment.COMPLETE
            if canonical
            else KnowledgeProvenanceAssessment.PARTIAL
        )

        return KnowledgeProvenanceAssessment(
            status=status,
            evidence_count=len(record.evidence),
            checksum_backed_count=len(checksum_backed),
            canonical_snapshot_count=len(canonical),
            derived_evidence_count=len(derived),
            warnings=tuple(warnings),
        )

    def validate_evidence(
        self,
        evidence: Iterable[KnowledgeEvidenceReference],
        *,
        generated_at,
    ) -> None:
        materialized = tuple(evidence)
        for item in materialized:
            if not isinstance(item, KnowledgeEvidenceReference):
                raise TypeError(
                    "evidence must contain only "
                    "KnowledgeEvidenceReference values"
                )

            if (
                item.evidence_type == self.CANONICAL_SNAPSHOT
                and item.checksum_sha256 is None
            ):
                raise ValueError(
                    "HISTORICAL_SNAPSHOT evidence must include checksum_sha256"
                )

            if item.observed_at > generated_at:
                raise ValueError(
                    "evidence observed_at must not be later than "
                    "knowledge generated_at"
                )
