"""
Deterministic Knowledge projection from an explicit snapshot-evidence input.

The Knowledge Domain must not import the History package. History-to-Knowledge
composition belongs to an application/CLI boundary that may translate verified
History values into this neutral input contract.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.provenance import (
    KnowledgeEvidenceProvenanceService,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalSnapshotKnowledgeSource:
    """
    Neutral, immutable source contract for snapshot-backed knowledge.

    This mirrors only the evidence fields required by Knowledge and deliberately
    does not depend on the History Domain model.
    """

    snapshot_id: str
    generated_at: datetime
    archived_at: datetime
    checksum_sha256: str
    package_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            self._normalize_uuid(
                self.snapshot_id
            ),
        )
        validate_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )
        validate_aware_datetime(
            self.archived_at,
            field_name="archived_at",
        )
        if self.archived_at < self.generated_at:
            raise ValueError(
                "archived_at must not be earlier than generated_at"
            )

        checksum = self.checksum_sha256.strip().lower()
        if (
            len(checksum) != 64
            or any(
                character not in "0123456789abcdef"
                for character in checksum
            )
        ):
            raise ValueError(
                "checksum_sha256 must be a 64-character hexadecimal digest"
            )
        object.__setattr__(
            self,
            "checksum_sha256",
            checksum,
        )
        object.__setattr__(
            self,
            "package_id",
            normalize_optional_text(
                self.package_id,
                field_name="package_id",
            ),
        )

    @staticmethod
    def _normalize_uuid(
        value: object,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(
                "snapshot_id must be a valid UUID string"
            )
        try:
            return str(
                UUID(
                    value.strip()
                )
            )
        except ValueError as exc:
            raise ValueError(
                "snapshot_id must be a valid UUID string"
            ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at.isoformat(),
            "archived_at": self.archived_at.isoformat(),
            "checksum_sha256": self.checksum_sha256,
            "package_id": self.package_id,
        }


class HistoricalSnapshotKnowledgeProjectionService:
    """
    Project explicit snapshot evidence into one deterministic descriptive fact.

    No History repository access, no external I/O, and no inference occur here.
    """

    KNOWLEDGE_TYPE = "FACT"
    KNOWLEDGE_ID_PREFIX = "HISTORICAL_SNAPSHOT_FACT"

    def __init__(
        self,
        *,
        provenance_service: KnowledgeEvidenceProvenanceService | None = None,
    ) -> None:
        self._provenance_service = (
            provenance_service
            if provenance_service is not None
            else KnowledgeEvidenceProvenanceService()
        )

    def project(
        self,
        source: HistoricalSnapshotKnowledgeSource,
        *,
        subject_key: str,
        generated_at: datetime,
        version: int = 1,
    ) -> KnowledgeRecord:
        if not isinstance(
            source,
            HistoricalSnapshotKnowledgeSource,
        ):
            raise TypeError(
                "source must be a HistoricalSnapshotKnowledgeSource"
            )

        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )
        validate_aware_datetime(
            generated_at,
            field_name="generated_at",
        )
        if generated_at < source.generated_at:
            raise ValueError(
                "generated_at must not be earlier than source.generated_at"
            )
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version <= 0
        ):
            raise ValueError(
                "version must be a positive integer"
            )

        evidence = KnowledgeEvidenceReference(
            evidence_type="HISTORICAL_SNAPSHOT",
            evidence_id=source.snapshot_id,
            observed_at=source.generated_at,
            checksum_sha256=source.checksum_sha256,
        )

        record = KnowledgeRecord(
            knowledge_id=self._knowledge_id(
                source
            ),
            knowledge_type=self.KNOWLEDGE_TYPE,
            version=version,
            subject_key=normalized_subject,
            statement=self._statement(
                source
            ),
            valid_from=source.generated_at,
            valid_to=None,
            generated_at=generated_at,
            evidence=(
                evidence,
            ),
            status="ACTIVE",
        )

        assessment = self._provenance_service.assess(
            record
        )
        if assessment.status != "COMPLETE":
            raise RuntimeError(
                "Snapshot-backed knowledge projection must produce "
                "COMPLETE provenance"
            )

        return record

    @classmethod
    def _knowledge_id(
        cls,
        source: HistoricalSnapshotKnowledgeSource,
    ) -> str:
        return (
            f"{cls.KNOWLEDGE_ID_PREFIX}:"
            f"{source.snapshot_id}"
        )

    @staticmethod
    def _statement(
        source: HistoricalSnapshotKnowledgeSource,
    ) -> str:
        package = (
            "without package_id"
            if source.package_id is None
            else f"with package_id {source.package_id}"
        )
        return (
            f"Historical snapshot {source.snapshot_id} "
            f"{package} was generated at "
            f"{source.generated_at.isoformat()} and archived at "
            f"{source.archived_at.isoformat()}."
        )
