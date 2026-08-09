from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.comparison import (
    KnowledgeTemporalComparisonService,
)
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
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


def evidence(
    evidence_type: str,
    evidence_id: str,
    *,
    observed_at=None,
    checksum=None,
):
    return KnowledgeEvidenceReference(
        evidence_type=evidence_type,
        evidence_id=evidence_id,
        observed_at=dt(1) if observed_at is None else observed_at,
        checksum_sha256=checksum,
    )


def record(
    *,
    version: int,
    statement: str = "Same statement.",
    status: str = "ACTIVE",
    valid_from=None,
    valid_to=None,
    generated_at=None,
    evidence_items=None,
    knowledge_id: str = "WORLD_CONTEXT",
) -> KnowledgeRecord:
    return KnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_type="FACT",
        version=version,
        subject_key="WORLD",
        statement=statement,
        valid_from=dt(1) if valid_from is None else valid_from,
        valid_to=valid_to,
        generated_at=(
            dt(version)
            if generated_at is None
            else generated_at
        ),
        evidence=(
            (
                evidence(
                    "HISTORICAL_SNAPSHOT",
                    f"snapshot-{version}",
                    checksum="a" * 64,
                ),
            )
            if evidence_items is None
            else tuple(evidence_items)
        ),
        status=status,
    )


def test_comparison_orders_by_generated_at_then_version() -> None:
    earlier = record(
        version=1,
        generated_at=dt(1),
    )
    later = record(
        version=2,
        generated_at=dt(2),
    )

    result = KnowledgeTemporalComparisonService().compare(
        later,
        earlier,
    )

    assert result.earlier_identity == "WORLD_CONTEXT@1"
    assert result.later_identity == "WORLD_CONTEXT@2"


def test_statement_status_and_validity_changes_are_explicit() -> None:
    earlier = record(
        version=1,
        statement="Old.",
        status="ACTIVE",
        valid_from=dt(1),
        valid_to=None,
    )
    later = record(
        version=2,
        statement="New.",
        status="SUPERSEDED",
        valid_from=dt(2),
        valid_to=dt(4),
    )

    result = KnowledgeTemporalComparisonService().compare(
        earlier,
        later,
    )

    assert result.statement_changed is True
    assert result.status_changed is True
    assert result.validity_changed is True
    assert result.any_change is True


def test_evidence_identity_changes_are_set_based_and_sorted() -> None:
    shared = evidence(
        "HISTORICAL_SNAPSHOT",
        "snapshot-shared",
        checksum="a" * 64,
    )
    removed = evidence(
        "SNAPSHOT_COMPARISON",
        "comparison-old",
    )
    added = evidence(
        "OUTCOME_RESEARCH",
        "research-new",
    )

    earlier = record(
        version=1,
        evidence_items=(
            removed,
            shared,
        ),
    )
    later = record(
        version=2,
        evidence_items=(
            shared,
            added,
        ),
    )

    result = KnowledgeTemporalComparisonService().compare(
        earlier,
        later,
    )

    assert result.evidence_removed == (
        "SNAPSHOT_COMPARISON:comparison-old",
    )
    assert result.evidence_added == (
        "OUTCOME_RESEARCH:research-new",
    )
    assert result.evidence_changed is True


def test_no_semantic_change_is_reported_as_unchanged() -> None:
    shared = evidence(
        "HISTORICAL_SNAPSHOT",
        "snapshot-shared",
        checksum="a" * 64,
    )
    first = record(
        version=1,
        generated_at=dt(1),
        evidence_items=(shared,),
    )
    second = record(
        version=2,
        generated_at=dt(2),
        evidence_items=(shared,),
    )

    result = KnowledgeTemporalComparisonService().compare(
        first,
        second,
    )

    assert result.statement_changed is False
    assert result.status_changed is False
    assert result.validity_changed is False
    assert result.evidence_changed is False
    assert result.any_change is False


def test_same_exact_identity_is_rejected() -> None:
    first = record(version=1)
    second = record(version=1)

    with pytest.raises(
        ValueError,
        match="different identities",
    ):
        KnowledgeTemporalComparisonService().compare(
            first,
            second,
        )


def test_different_knowledge_ids_are_rejected() -> None:
    first = record(
        version=1,
        knowledge_id="WORLD_CONTEXT",
    )
    second = record(
        version=2,
        knowledge_id="EM_CONTEXT",
    )

    with pytest.raises(
        ValueError,
        match="same knowledge_id",
    ):
        KnowledgeTemporalComparisonService().compare(
            first,
            second,
        )


def test_serialization_contains_no_score_or_prediction_fields() -> None:
    result = KnowledgeTemporalComparisonService().compare(
        record(version=1),
        record(version=2),
    ).to_dict()

    for key in (
        "score",
        "confidence",
        "prediction",
        "effectiveness",
        "success_probability",
    ):
        assert key not in result


def test_invalid_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="first must be",
    ):
        KnowledgeTemporalComparisonService().compare(
            object(),  # type: ignore[arg-type]
            record(version=2),
        )
