from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.projection import (
    HistoricalSnapshotKnowledgeProjectionService,
    HistoricalSnapshotKnowledgeSource,
)
from investment_terminal.knowledge.provenance import (
    KnowledgeEvidenceProvenanceService,
)


def dt(
    day: int,
    hour: int = 12,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        0,
        tzinfo=timezone.utc,
    )


def source(
    *,
    package_id: str | None = "review-001",
) -> HistoricalSnapshotKnowledgeSource:
    return HistoricalSnapshotKnowledgeSource(
        snapshot_id="11111111-1111-4111-8111-111111111111",
        package_id=package_id,
        generated_at=dt(1),
        archived_at=dt(1, 13),
        checksum_sha256="a" * 64,
    )


def service() -> HistoricalSnapshotKnowledgeProjectionService:
    return HistoricalSnapshotKnowledgeProjectionService()


def test_projection_is_deterministic_descriptive_fact() -> None:
    item = service().project(
        source(),
        subject_key="WORLD",
        generated_at=dt(2),
    )

    assert item.knowledge_id == (
        "HISTORICAL_SNAPSHOT_FACT:"
        "11111111-1111-4111-8111-111111111111"
    )
    assert item.knowledge_type == "FACT"
    assert item.version == 1
    assert item.subject_key == "WORLD"
    assert item.valid_from == dt(1)
    assert item.valid_to is None
    assert item.generated_at == dt(2)
    assert item.status == "ACTIVE"


def test_projection_preserves_canonical_snapshot_evidence_identity() -> None:
    src = source()

    item = service().project(
        src,
        subject_key="WORLD",
        generated_at=dt(2),
    )

    evidence = item.evidence[0]
    assert evidence.evidence_type == "HISTORICAL_SNAPSHOT"
    assert evidence.evidence_id == src.snapshot_id
    assert evidence.observed_at == src.generated_at
    assert evidence.checksum_sha256 == src.checksum_sha256


def test_projection_provenance_is_complete() -> None:
    item = service().project(
        source(),
        subject_key="WORLD",
        generated_at=dt(2),
    )

    assessment = KnowledgeEvidenceProvenanceService().assess(
        item
    )

    assert assessment.status == "COMPLETE"
    assert assessment.canonical_snapshot_count == 1
    assert assessment.checksum_backed_count == 1
    assert assessment.warnings == ()


def test_statement_is_exact_and_stable() -> None:
    item = service().project(
        source(),
        subject_key="WORLD",
        generated_at=dt(2),
    )

    assert item.statement == (
        "Historical snapshot "
        "11111111-1111-4111-8111-111111111111 "
        "with package_id review-001 was generated at "
        "2026-08-01T12:00:00+00:00 and archived at "
        "2026-08-01T13:00:00+00:00."
    )


def test_missing_package_id_has_explicit_statement() -> None:
    item = service().project(
        source(
            package_id=None
        ),
        subject_key="WORLD",
        generated_at=dt(2),
    )

    assert "without package_id" in item.statement


def test_same_input_produces_equal_record() -> None:
    src = source()
    projector = service()

    assert projector.project(
        src,
        subject_key="WORLD",
        generated_at=dt(2),
    ) == projector.project(
        src,
        subject_key="WORLD",
        generated_at=dt(2),
    )


def test_projection_generation_cannot_precede_source_observation() -> None:
    with pytest.raises(
        ValueError,
        match="must not be earlier than source.generated_at",
    ):
        service().project(
            source(),
            subject_key="WORLD",
            generated_at=datetime(
                2026,
                8,
                1,
                11,
                59,
                tzinfo=timezone.utc,
            ),
        )


def test_projection_rejects_wrong_source_type() -> None:
    with pytest.raises(
        TypeError,
        match="source must be",
    ):
        service().project(
            object(),  # type: ignore[arg-type]
            subject_key="WORLD",
            generated_at=dt(2),
        )


def test_source_contract_rejects_bad_snapshot_uuid() -> None:
    with pytest.raises(
        ValueError,
        match="snapshot_id must be a valid UUID",
    ):
        HistoricalSnapshotKnowledgeSource(
            snapshot_id="not-a-uuid",
            generated_at=dt(1),
            archived_at=dt(1, 13),
            checksum_sha256="a" * 64,
        )


def test_projection_contains_no_prediction_or_effectiveness_fields() -> None:
    data = service().project(
        source(),
        subject_key="WORLD",
        generated_at=dt(2),
    ).to_dict()

    for key in (
        "prediction",
        "confidence",
        "effectiveness",
        "success_probability",
        "ai_generated",
    ):
        assert key not in data
