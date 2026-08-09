"""
Canonical read/result envelope for Knowledge records and derived provenance.

The provenance assessment is rebuildable and intentionally not persisted in
Knowledge SQLite.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.knowledge.models import (
    KnowledgeRecord,
)
from investment_terminal.knowledge.provenance import (
    KnowledgeEvidenceProvenanceService,
    KnowledgeProvenanceAssessment,
)


@dataclass(frozen=True, slots=True)
class KnowledgeRecordEnvelope:
    """Immutable record + provenance read contract."""

    record: KnowledgeRecord
    provenance: KnowledgeProvenanceAssessment

    def __post_init__(self) -> None:
        if not isinstance(
            self.record,
            KnowledgeRecord,
        ):
            raise TypeError(
                "record must be a KnowledgeRecord"
            )
        if not isinstance(
            self.provenance,
            KnowledgeProvenanceAssessment,
        ):
            raise TypeError(
                "provenance must be a KnowledgeProvenanceAssessment"
            )

        if (
            self.provenance.evidence_count
            != len(self.record.evidence)
        ):
            raise ValueError(
                "provenance evidence_count must match record evidence"
            )

        canonical_count = sum(
            1
            for item in self.record.evidence
            if item.evidence_type == "HISTORICAL_SNAPSHOT"
        )
        derived_count = (
            len(self.record.evidence)
            - canonical_count
        )
        checksum_count = sum(
            1
            for item in self.record.evidence
            if item.checksum_sha256 is not None
        )

        if (
            self.provenance.canonical_snapshot_count
            != canonical_count
        ):
            raise ValueError(
                "provenance canonical_snapshot_count must match record evidence"
            )
        if (
            self.provenance.derived_evidence_count
            != derived_count
        ):
            raise ValueError(
                "provenance derived_evidence_count must match record evidence"
            )
        if (
            self.provenance.checksum_backed_count
            != checksum_count
        ):
            raise ValueError(
                "provenance checksum_backed_count must match record evidence"
            )

    @property
    def identity_key(self) -> str:
        return self.record.identity_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "provenance": self.provenance.to_dict(),
            "identity_key": self.identity_key,
        }


class KnowledgeRecordEnvelopeService:
    """Build canonical read envelopes from KnowledgeRecord values."""

    def __init__(
        self,
        *,
        provenance_service: (
            KnowledgeEvidenceProvenanceService | None
        ) = None,
    ) -> None:
        self._provenance_service = (
            provenance_service
            if provenance_service is not None
            else KnowledgeEvidenceProvenanceService()
        )

    def build(
        self,
        record: KnowledgeRecord,
    ) -> KnowledgeRecordEnvelope:
        if not isinstance(
            record,
            KnowledgeRecord,
        ):
            raise TypeError(
                "record must be a KnowledgeRecord"
            )

        provenance = self._provenance_service.assess(
            record
        )
        return KnowledgeRecordEnvelope(
            record=record,
            provenance=provenance,
        )

    def build_many(
        self,
        records,
    ) -> tuple[KnowledgeRecordEnvelope, ...]:
        materialized = tuple(
            records
        )
        if any(
            not isinstance(
                record,
                KnowledgeRecord,
            )
            for record in materialized
        ):
            raise TypeError(
                "records must contain only KnowledgeRecord values"
            )

        return tuple(
            self.build(
                record
            )
            for record in materialized
        )
