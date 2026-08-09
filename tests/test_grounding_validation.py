from datetime import datetime, timezone

import pytest

from investment_terminal.ai.models import (
    GroundedAIAnswer,
    GroundedAIClaim,
    GroundedKnowledgeCitation,
)
from investment_terminal.ai.validation import (
    GroundingValidationService,
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


def complete_envelope():
    record = KnowledgeRecord(
        knowledge_id="WORLD_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="WORLD was present historically.",
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


def partial_envelope():
    record = KnowledgeRecord(
        knowledge_id="DERIVED_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="Derived-only historical context.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(2),
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="SNAPSHOT_COMPARISON",
                evidence_id="comparison-1",
                observed_at=dt(1),
            ),
        ),
    )
    return KnowledgeRecordEnvelopeService().build(
        record
    )


def answer_for(envelope):
    return GroundedAIAnswer(
        answer_id="answer-1",
        protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        claims=(
            GroundedAIClaim(
                text="Historical context is available.",
                citations=(
                    GroundedKnowledgeCitation.from_envelope(
                        envelope
                    ),
                ),
            ),
        ),
    )


def test_complete_exact_knowledge_is_admissible() -> None:
    envelope = complete_envelope()

    assessment = GroundingValidationService().validate_answer(
        answer_for(
            envelope
        ),
        knowledge=(
            envelope,
        ),
    )

    assert assessment.status == "ADMISSIBLE"
    assert assessment.claim_count == 1
    assert assessment.citation_count == 1
    assert assessment.resolved_citation_count == 1
    assert assessment.inadmissible_citation_count == 0
    assert assessment.warnings == ()


def test_unresolved_citation_is_rejected() -> None:
    envelope = complete_envelope()

    assessment = GroundingValidationService().validate_answer(
        answer_for(
            envelope
        ),
        knowledge=(),
    )

    assert assessment.status == "REJECTED"
    assert assessment.resolved_citation_count == 0
    assert any(
        "does not resolve" in warning
        for warning in assessment.warnings
    )


def test_forged_statement_is_rejected() -> None:
    envelope = complete_envelope()
    answer = GroundedAIAnswer(
        answer_id="answer-1",
        protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        claims=(
            GroundedAIClaim(
                text="Claim.",
                citations=(
                    GroundedKnowledgeCitation(
                        knowledge_identity=envelope.identity_key,
                        statement="Forged statement.",
                        provenance_status="COMPLETE",
                    ),
                ),
            ),
        ),
    )

    assessment = GroundingValidationService().validate_answer(
        answer,
        knowledge=(
            envelope,
        ),
    )

    assert assessment.status == "REJECTED"
    assert any(
        "statement does not match" in warning
        for warning in assessment.warnings
    )


def test_forged_provenance_status_is_rejected() -> None:
    envelope = complete_envelope()
    answer = GroundedAIAnswer(
        answer_id="answer-1",
        protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        claims=(
            GroundedAIClaim(
                text="Claim.",
                citations=(
                    GroundedKnowledgeCitation(
                        knowledge_identity=envelope.identity_key,
                        statement=envelope.record.statement,
                        provenance_status="PARTIAL",
                    ),
                ),
            ),
        ),
    )

    assessment = GroundingValidationService().validate_answer(
        answer,
        knowledge=(
            envelope,
        ),
    )

    assert assessment.status == "REJECTED"
    assert any(
        "provenance_status does not match" in warning
        for warning in assessment.warnings
    )


def test_partial_lineage_is_traceable_but_not_admissible_v1() -> None:
    envelope = partial_envelope()

    assessment = GroundingValidationService().validate_answer(
        answer_for(
            envelope
        ),
        knowledge=(
            envelope,
        ),
    )

    assert envelope.provenance.status == "PARTIAL"
    assert assessment.status == "REJECTED"
    assert assessment.resolved_citation_count == 1
    assert assessment.inadmissible_citation_count == 1
    assert any(
        "traceable but is not admissible" in warning
        for warning in assessment.warnings
    )


def test_require_admissible_returns_same_answer() -> None:
    envelope = complete_envelope()
    answer = answer_for(
        envelope
    )

    assert GroundingValidationService().require_admissible(
        answer,
        knowledge=(
            envelope,
        ),
    ) is answer


def test_require_admissible_raises_for_partial() -> None:
    envelope = partial_envelope()

    with pytest.raises(
        ValueError,
        match="not admissible",
    ):
        GroundingValidationService().require_admissible(
            answer_for(
                envelope
            ),
            knowledge=(
                envelope,
            ),
        )


def test_duplicate_knowledge_registry_identity_is_rejected() -> None:
    envelope = complete_envelope()

    with pytest.raises(
        ValueError,
        match="unique identities",
    ):
        GroundingValidationService().validate_answer(
            answer_for(
                envelope
            ),
            knowledge=(
                envelope,
                envelope,
            ),
        )


def test_validation_does_not_claim_semantic_entailment() -> None:
    envelope = complete_envelope()
    assessment = GroundingValidationService().validate_answer(
        GroundedAIAnswer(
            answer_id="answer-1",
            protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
            claims=(
                GroundedAIClaim(
                    text="A text that is not semantically evaluated by v1.",
                    citations=(
                        GroundedKnowledgeCitation.from_envelope(
                            envelope
                        ),
                    ),
                ),
            ),
        ),
        knowledge=(
            envelope,
        ),
    )

    assert assessment.status == "ADMISSIBLE"
    serialized = str(
        assessment.to_dict()
    ).lower()
    assert "entailment" not in serialized
    assert "truth_score" not in serialized
    assert "confidence" not in serialized
