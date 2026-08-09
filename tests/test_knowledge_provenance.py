from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.provenance import (
    KnowledgeEvidenceProvenanceService,
)


def dt(day: int) -> datetime:
    return datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc)


def snapshot(
    identifier: str = "11111111-1111-4111-8111-111111111111",
    *,
    observed_at=None,
    checksum=True,
) -> KnowledgeEvidenceReference:
    return KnowledgeEvidenceReference(
        evidence_type="HISTORICAL_SNAPSHOT",
        evidence_id=identifier,
        observed_at=dt(1) if observed_at is None else observed_at,
        checksum_sha256=("a" * 64) if checksum else None,
    )


def derived(
    evidence_type: str = "SNAPSHOT_COMPARISON",
    identifier: str = "comparison-1",
) -> KnowledgeEvidenceReference:
    return KnowledgeEvidenceReference(
        evidence_type=evidence_type,
        evidence_id=identifier,
        observed_at=dt(2),
    )


def record(
    evidence,
    *,
    generated_at=None,
) -> KnowledgeRecord:
    return KnowledgeRecord(
        knowledge_id="WORLD_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="Traceable historical statement.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(3) if generated_at is None else generated_at,
        evidence=tuple(evidence),
    )


def test_checksum_backed_snapshot_lineage_is_complete() -> None:
    assessment = KnowledgeEvidenceProvenanceService().assess(
        record((snapshot(),))
    )

    assert assessment.status == "COMPLETE"
    assert assessment.evidence_count == 1
    assert assessment.canonical_snapshot_count == 1
    assert assessment.checksum_backed_count == 1
    assert assessment.derived_evidence_count == 0
    assert assessment.fully_checksum_backed is True
    assert assessment.warnings == ()


def test_snapshot_reference_without_checksum_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must include checksum_sha256",
    ):
        KnowledgeEvidenceProvenanceService().assess(
            record((snapshot(checksum=False),))
        )


def test_derived_only_lineage_is_partial_not_invented_as_canonical() -> None:
    assessment = KnowledgeEvidenceProvenanceService().assess(
        record((derived(),))
    )

    assert assessment.status == "PARTIAL"
    assert assessment.canonical_snapshot_count == 0
    assert assessment.derived_evidence_count == 1
    assert any(
        "no checksum-backed canonical historical snapshot" in warning
        for warning in assessment.warnings
    )


def test_mixed_snapshot_and_derived_lineage_is_complete_with_warning() -> None:
    assessment = KnowledgeEvidenceProvenanceService().assess(
        record((
            snapshot(),
            derived(),
        ))
    )

    assert assessment.status == "COMPLETE"
    assert assessment.canonical_snapshot_count == 1
    assert assessment.derived_evidence_count == 1
    assert assessment.fully_checksum_backed is False
    assert any(
        "Not every evidence reference is checksum-backed" in warning
        for warning in assessment.warnings
    )


def test_future_evidence_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must not be later",
    ):
        KnowledgeEvidenceProvenanceService().assess(
            record(
                (snapshot(observed_at=dt(4)),),
                generated_at=dt(3),
            )
        )


def test_serialization_is_stable() -> None:
    data = KnowledgeEvidenceProvenanceService().assess(
        record((
            snapshot(),
            derived(),
        ))
    ).to_dict()

    assert data["status"] == "COMPLETE"
    assert data["evidence_count"] == 2
    assert data["canonical_snapshot_count"] == 1
    assert data["derived_evidence_count"] == 1
    assert data["fully_checksum_backed"] is False


def test_service_rejects_non_record() -> None:
    with pytest.raises(
        TypeError,
        match="record must be",
    ):
        KnowledgeEvidenceProvenanceService().assess(
            object()  # type: ignore[arg-type]
        )
