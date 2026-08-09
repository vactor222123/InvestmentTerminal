from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelope,
    KnowledgeRecordEnvelopeService,
)
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.provenance import (
    KnowledgeEvidenceProvenanceService,
    KnowledgeProvenanceAssessment,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def snapshot_evidence():
    return KnowledgeEvidenceReference(
        evidence_type="HISTORICAL_SNAPSHOT",
        evidence_id="11111111-1111-4111-8111-111111111111",
        observed_at=dt(1),
        checksum_sha256="a" * 64,
    )


def derived_evidence():
    return KnowledgeEvidenceReference(
        evidence_type="SNAPSHOT_COMPARISON",
        evidence_id="comparison-1",
        observed_at=dt(2),
    )


def record(
    *,
    evidence=None,
) -> KnowledgeRecord:
    return KnowledgeRecord(
        knowledge_id="WORLD_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="Traceable knowledge statement.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(3),
        evidence=(
            (snapshot_evidence(),)
            if evidence is None
            else tuple(evidence)
        ),
    )


def test_service_builds_complete_envelope() -> None:
    item = record()

    envelope = KnowledgeRecordEnvelopeService().build(
        item
    )

    assert envelope.record is item
    assert envelope.identity_key == "WORLD_CONTEXT@1"
    assert envelope.provenance.status == "COMPLETE"
    assert envelope.provenance.evidence_count == 1


def test_derived_only_record_builds_partial_envelope() -> None:
    envelope = KnowledgeRecordEnvelopeService().build(
        record(
            evidence=(
                derived_evidence(),
            )
        )
    )

    assert envelope.provenance.status == "PARTIAL"
    assert envelope.provenance.canonical_snapshot_count == 0
    assert envelope.provenance.derived_evidence_count == 1


def test_serialization_contains_record_and_provenance() -> None:
    data = KnowledgeRecordEnvelopeService().build(
        record()
    ).to_dict()

    assert data["identity_key"] == "WORLD_CONTEXT@1"
    assert data["record"]["identity_key"] == "WORLD_CONTEXT@1"
    assert data["provenance"]["status"] == "COMPLETE"
    assert data["provenance"]["evidence_count"] == 1


def test_build_many_preserves_input_order() -> None:
    first = record()
    second = KnowledgeRecord(
        knowledge_id="EM_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="EM",
        statement="Second statement.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(3),
        evidence=(
            snapshot_evidence(),
        ),
    )

    output = KnowledgeRecordEnvelopeService().build_many(
        (
            second,
            first,
        )
    )

    assert tuple(
        item.record
        for item in output
    ) == (
        second,
        first,
    )


def test_envelope_rejects_mismatched_evidence_count() -> None:
    item = record()
    assessment = KnowledgeProvenanceAssessment(
        status="COMPLETE",
        evidence_count=2,
        checksum_backed_count=1,
        canonical_snapshot_count=1,
        derived_evidence_count=1,
        warnings=(),
    )

    with pytest.raises(
        ValueError,
        match="evidence_count must match",
    ):
        KnowledgeRecordEnvelope(
            record=item,
            provenance=assessment,
        )


def test_envelope_rejects_mismatched_checksum_count() -> None:
    item = record()
    assessment = KnowledgeProvenanceAssessment(
        status="COMPLETE",
        evidence_count=1,
        checksum_backed_count=0,
        canonical_snapshot_count=1,
        derived_evidence_count=0,
        warnings=(),
    )

    with pytest.raises(
        ValueError,
        match="checksum_backed_count must match",
    ):
        KnowledgeRecordEnvelope(
            record=item,
            provenance=assessment,
        )


def test_service_matches_direct_provenance_assessment() -> None:
    item = record(
        evidence=(
            snapshot_evidence(),
            derived_evidence(),
        )
    )

    envelope = KnowledgeRecordEnvelopeService().build(
        item
    )
    direct = KnowledgeEvidenceProvenanceService().assess(
        item
    )

    assert envelope.provenance == direct


def test_no_persistence_fields_added_to_envelope() -> None:
    data = KnowledgeRecordEnvelopeService().build(
        record()
    ).to_dict()

    for key in (
        "database_id",
        "persisted_at",
        "row_id",
        "history_snapshot",
    ):
        assert key not in data
