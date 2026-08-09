from datetime import datetime, timezone

import pytest

from investment_terminal.ai.models import (
    GroundedAIAnswer,
    GroundedAIClaim,
    GroundedKnowledgeCitation,
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
    knowledge_id: str = "WORLD_CONTEXT",
):
    record = KnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="WORLD was present in the archived recommendation set.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(2),
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id="11111111-1111-4111-8111-111111111111",
                observed_at=dt(1),
                checksum_sha256="a" * 64,
            ),
        ),
    )
    return KnowledgeRecordEnvelopeService().build(
        record
    )


def citation():
    return GroundedKnowledgeCitation.from_envelope(
        envelope()
    )


def test_citation_is_derived_from_exact_knowledge_envelope() -> None:
    item = citation()

    assert item.knowledge_identity == "WORLD_CONTEXT@1"
    assert item.statement == (
        "WORLD was present in the archived recommendation set."
    )
    assert item.provenance_status == "COMPLETE"


def test_claim_requires_explicit_citation() -> None:
    with pytest.raises(
        ValueError,
        match="at least one citation",
    ):
        GroundedAIClaim(
            text="WORLD was present historically.",
            citations=(),
        )


def test_duplicate_knowledge_citations_are_rejected() -> None:
    item = citation()

    with pytest.raises(
        ValueError,
        match="unique knowledge identities",
    ):
        GroundedAIClaim(
            text="WORLD was present historically.",
            citations=(
                item,
                item,
            ),
        )


def test_answer_uses_versioned_protocol_identity() -> None:
    answer = GroundedAIAnswer(
        answer_id="answer-1",
        protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        claims=(
            GroundedAIClaim(
                text="WORLD was present historically.",
                citations=(
                    citation(),
                ),
            ),
        ),
    )

    assert answer.protocol_identity == (
        "EVIDENCE_GROUNDED_ANSWER@1"
    )
    assert answer.cited_knowledge_identities == (
        "WORLD_CONTEXT@1",
    )


def test_answer_rejects_unknown_protocol_identity() -> None:
    with pytest.raises(
        ValueError,
        match="EVIDENCE_GROUNDED_ANSWER@1",
    ):
        GroundedAIAnswer(
            answer_id="answer-1",
            protocol_identity="UNVERSIONED_AI",
            claims=(
                GroundedAIClaim(
                    text="Claim.",
                    citations=(
                        citation(),
                    ),
                ),
            ),
        )


def test_serialization_preserves_claim_to_knowledge_lineage() -> None:
    answer = GroundedAIAnswer(
        answer_id="answer-1",
        protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        claims=(
            GroundedAIClaim(
                text="WORLD was present historically.",
                citations=(
                    citation(),
                ),
            ),
        ),
    )

    data = answer.to_dict()

    assert data["claims"][0]["citations"][0][
        "knowledge_identity"
    ] == "WORLD_CONTEXT@1"
    assert data["claims"][0]["citations"][0][
        "provenance_status"
    ] == "COMPLETE"


def test_answer_contains_no_prediction_or_effectiveness_semantics() -> None:
    data = GroundedAIAnswer(
        answer_id="answer-1",
        protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        claims=(
            GroundedAIClaim(
                text="WORLD was present historically.",
                citations=(
                    citation(),
                ),
            ),
        ),
    ).to_dict()

    forbidden = (
        "confidence",
        "prediction",
        "success_probability",
        "effectiveness",
        "causal",
        "recommended_action",
    )

    serialized = str(
        data
    ).lower()
    for key in forbidden:
        assert key not in serialized


def test_ai_contract_does_not_mutate_knowledge_envelope() -> None:
    source = envelope()
    before = source.to_dict()

    GroundedKnowledgeCitation.from_envelope(
        source
    )

    assert source.to_dict() == before
