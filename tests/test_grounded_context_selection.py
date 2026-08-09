from datetime import datetime, timezone

import pytest

from investment_terminal.ai.context_selection import (
    GroundedContextSelectionPolicy,
    GroundedContextSelectionService,
)
from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelopeService,
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


def envelope(
    knowledge_id: str,
    *,
    subject: str,
    valid_from,
    generated_at,
    complete: bool = True,
):
    evidence = (
        KnowledgeEvidenceReference(
            evidence_type="HISTORICAL_SNAPSHOT",
            evidence_id=(
                "11111111-1111-4111-8111-"
                + f"{abs(hash(knowledge_id)) % 10**12:012d}"
            ),
            observed_at=valid_from,
            checksum_sha256="a" * 64,
        )
        if complete
        else KnowledgeEvidenceReference(
            evidence_type="SNAPSHOT_COMPARISON",
            evidence_id=f"comparison-{knowledge_id}",
            observed_at=valid_from,
        )
    )
    record = KnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_type="FACT",
        version=1,
        subject_key=subject,
        statement=f"Statement for {knowledge_id}.",
        valid_from=valid_from,
        valid_to=None,
        generated_at=generated_at,
        evidence=(
            evidence,
        ),
    )
    return KnowledgeRecordEnvelopeService().build(
        record
    )


def test_default_policy_selects_complete_only() -> None:
    complete = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )
    partial = envelope(
        "WORLD_B",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
        complete=False,
    )

    result = GroundedContextSelectionService().select(
        (
            partial,
            complete,
        )
    )

    assert result.selected == (
        complete,
    )
    assert result.excluded_partial_count == 1
    assert result.excluded_subject_count == 0


def test_subject_allowlist_is_explicit() -> None:
    world = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )
    em = envelope(
        "EM_A",
        subject="EM",
        valid_from=dt(1),
        generated_at=dt(2),
    )

    result = GroundedContextSelectionService().select(
        (
            world,
            em,
        ),
        policy=GroundedContextSelectionPolicy(
            subject_keys=(
                "WORLD",
            ),
        ),
    )

    assert result.selected == (
        world,
    )
    assert result.excluded_subject_count == 1


def test_order_is_deterministic_and_independent_of_input_order() -> None:
    later = envelope(
        "WORLD_Z",
        subject="WORLD",
        valid_from=dt(3),
        generated_at=dt(4),
    )
    earlier_b = envelope(
        "WORLD_B",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )
    earlier_a = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )
    em = envelope(
        "EM_A",
        subject="EM",
        valid_from=dt(1),
        generated_at=dt(2),
    )

    result = GroundedContextSelectionService().select(
        (
            later,
            earlier_b,
            em,
            earlier_a,
        )
    )

    assert result.selected_identities == (
        "EM_A@1",
        "WORLD_A@1",
        "WORLD_B@1",
        "WORLD_Z@1",
    )


def test_max_items_applies_after_deterministic_order() -> None:
    items = (
        envelope(
            "WORLD_C",
            subject="WORLD",
            valid_from=dt(3),
            generated_at=dt(4),
        ),
        envelope(
            "WORLD_A",
            subject="WORLD",
            valid_from=dt(1),
            generated_at=dt(2),
        ),
        envelope(
            "WORLD_B",
            subject="WORLD",
            valid_from=dt(2),
            generated_at=dt(3),
        ),
    )

    result = GroundedContextSelectionService().select(
        items,
        policy=GroundedContextSelectionPolicy(
            max_items=2,
        ),
    )

    assert result.selected_identities == (
        "WORLD_A@1",
        "WORLD_B@1",
    )


def test_selection_accounting_is_serializable() -> None:
    selected = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )

    data = GroundedContextSelectionService().select(
        (
            selected,
        )
    ).to_dict()

    assert data["source_count"] == 1
    assert data["selected_count"] == 1
    assert data["selected_identities"] == [
        "WORLD_A@1",
    ]
    assert data["policy"][
        "required_provenance_status"
    ] == "COMPLETE"


def test_duplicate_envelope_identity_is_rejected() -> None:
    item = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )

    with pytest.raises(
        ValueError,
        match="unique identities",
    ):
        GroundedContextSelectionService().select(
            (
                item,
                item,
            )
        )


def test_policy_rejects_duplicate_subjects() -> None:
    with pytest.raises(
        ValueError,
        match="subject_keys must be unique",
    ):
        GroundedContextSelectionPolicy(
            subject_keys=(
                "WORLD",
                "WORLD",
            )
        )


def test_policy_rejects_invalid_max_items() -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        GroundedContextSelectionPolicy(
            max_items=0
        )


def test_selection_contains_no_relevance_score_or_model_semantics() -> None:
    item = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )

    serialized = str(
        GroundedContextSelectionService().select(
            (
                item,
            )
        ).to_dict()
    ).lower()

    for key in (
        "relevance_score",
        "embedding",
        "model",
        "confidence",
        "semantic_similarity",
    ):
        assert key not in serialized
