import json
from datetime import datetime, timezone

import pytest

from investment_terminal.ai.context_selection import (
    GroundedContextSelectionPolicy,
)
from investment_terminal.ai.model_adapter import (
    GroundedModelAdapter,
    GroundedModelResponse,
    StaticGroundedModelAdapter,
)
from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
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


def envelope():
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


def raw_answer(
    *,
    knowledge_identity="WORLD_CONTEXT@1",
    statement="WORLD was present historically.",
    provenance_status="COMPLETE",
):
    return json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
            "claims": [
                {
                    "text": "Historical context is available.",
                    "citations": [
                        {
                            "knowledge_identity": knowledge_identity,
                            "statement": statement,
                            "provenance_status": provenance_status,
                        }
                    ],
                }
            ],
        }
    )


def service(raw_text=None):
    return GroundedGenerationService(
        adapter=StaticGroundedModelAdapter(
            provider_identity="STATIC_TEST",
            model_identity="STATIC_MODEL@1",
            raw_text=(
                raw_answer()
                if raw_text is None
                else raw_text
            ),
        )
    )


def test_orchestration_runs_complete_admissible_flow() -> None:
    source = envelope()

    result = service().generate(
        request_id="request-1",
        user_query="What historical context is available?",
        knowledge=(
            source,
        ),
    )

    assert result.selection.selected == (
        source,
    )
    assert result.prompt.request_id == "request-1"
    assert result.response.request_id == "request-1"
    assert result.parsed.request_id == "request-1"
    assert result.validation.status == "ADMISSIBLE"
    assert result.answer.answer_id == "answer-1"


def test_orchestration_preserves_selection_policy() -> None:
    source = envelope()

    result = service().generate(
        request_id="request-1",
        user_query="Question",
        knowledge=(
            source,
        ),
        policy=GroundedContextSelectionPolicy(
            subject_keys=(
                "WORLD",
            ),
            max_items=1,
        ),
    )

    assert result.selection.policy.subject_keys == (
        "WORLD",
    )
    assert result.selection.policy.max_items == 1


def test_unresolved_model_citation_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="not admissible",
    ):
        service(
            raw_answer(
                knowledge_identity="MISSING@1",
            )
        ).generate(
            request_id="request-1",
            user_query="Question",
            knowledge=(
                envelope(),
            ),
        )


def test_forged_model_statement_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="not admissible",
    ):
        service(
            raw_answer(
                statement="Forged statement.",
            )
        ).generate(
            request_id="request-1",
            user_query="Question",
            knowledge=(
                envelope(),
            ),
        )


def test_malformed_model_json_stops_before_grounding() -> None:
    with pytest.raises(
        ValueError,
        match="valid JSON",
    ):
        service(
            "{bad-json"
        ).generate(
            request_id="request-1",
            user_query="Question",
            knowledge=(
                envelope(),
            ),
        )


class WrongCorrelationAdapter(
    GroundedModelAdapter
):
    def generate(self, prompt):
        return GroundedModelResponse(
            request_id="different-request",
            provider_identity="TEST",
            model_identity="TEST@1",
            raw_text=raw_answer(),
        )


def test_request_correlation_mismatch_fails_closed() -> None:
    generation = GroundedGenerationService(
        adapter=WrongCorrelationAdapter()
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        generation.generate(
            request_id="request-1",
            user_query="Question",
            knowledge=(
                envelope(),
            ),
        )


def test_partial_or_excluded_context_cannot_be_cited() -> None:
    with pytest.raises(
        ValueError,
        match="not admissible",
    ):
        service().generate(
            request_id="request-1",
            user_query="Question",
            knowledge=(),
        )


def test_result_serializes_all_boundary_artifacts() -> None:
    result = service().generate(
        request_id="request-1",
        user_query="Question",
        knowledge=(
            envelope(),
        ),
    )

    data = result.to_dict()

    assert data["selection"]["selected_count"] == 1
    assert data["prompt"]["request_id"] == "request-1"
    assert data["response"]["provider_identity"] == "STATIC_TEST"
    assert data["parsed"]["answer"]["answer_id"] == "answer-1"
    assert data["validation"]["status"] == "ADMISSIBLE"
    assert data["answer"]["answer_id"] == "answer-1"


def test_orchestration_rejects_non_adapter() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedModelAdapter",
    ):
        GroundedGenerationService(
            adapter=object(),  # type: ignore[arg-type]
        )
