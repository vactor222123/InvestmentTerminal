import json
from datetime import datetime, timezone

import pytest

from investment_terminal.ai.audit import (
    GroundedGenerationTrace,
    GroundedGenerationTraceService,
)
from investment_terminal.ai.model_adapter import (
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


def envelope(
    knowledge_id: str,
    statement: str,
):
    record = KnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement=statement,
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(2),
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id=(
                    "11111111-1111-4111-8111-"
                    + f"{len(knowledge_id):012d}"
                ),
                observed_at=dt(1),
                checksum_sha256="a" * 64,
            ),
        ),
    )
    return KnowledgeRecordEnvelopeService().build(
        record
    )


def generation_result():
    first = envelope(
        "WORLD_A",
        "WORLD A was present historically.",
    )
    second = envelope(
        "WORLD_B",
        "WORLD B was present historically.",
    )

    raw = json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
            "claims": [
                {
                    "text": "Historical context is available.",
                    "citations": [
                        {
                            "knowledge_identity": "WORLD_A@1",
                            "statement": "WORLD A was present historically.",
                            "provenance_status": "COMPLETE",
                        },
                        {
                            "knowledge_identity": "WORLD_B@1",
                            "statement": "WORLD B was present historically.",
                            "provenance_status": "COMPLETE",
                        },
                    ],
                }
            ],
        }
    )

    service = GroundedGenerationService(
        adapter=StaticGroundedModelAdapter(
            provider_identity="STATIC_TEST",
            model_identity="STATIC_MODEL@1",
            raw_text=raw,
        )
    )

    return service.generate(
        request_id="request-1",
        user_query="What historical context is available?",
        knowledge=(
            second,
            first,
        ),
    )


def test_trace_is_derived_from_successful_generation() -> None:
    result = generation_result()

    trace = GroundedGenerationTraceService().build(
        result
    )

    assert trace.request_id == "request-1"
    assert trace.prompt_protocol_identity == (
        "EVIDENCE_GROUNDED_PROMPT@1"
    )
    assert trace.answer_protocol_identity == (
        "EVIDENCE_GROUNDED_ANSWER@1"
    )
    assert trace.provider_identity == "STATIC_TEST"
    assert trace.model_identity == "STATIC_MODEL@1"
    assert trace.validation_status == "ADMISSIBLE"


def test_trace_preserves_selected_and_cited_identities() -> None:
    trace = GroundedGenerationTraceService().build(
        generation_result()
    )

    assert trace.selected_knowledge_identities == (
        "WORLD_A@1",
        "WORLD_B@1",
    )
    assert trace.cited_knowledge_identities == (
        "WORLD_A@1",
        "WORLD_B@1",
    )


def test_trace_reports_claim_and_citation_counts() -> None:
    trace = GroundedGenerationTraceService().build(
        generation_result()
    )

    assert trace.claim_count == 1
    assert trace.citation_count == 2


def test_trace_serialization_is_compact_and_excludes_raw_text() -> None:
    data = GroundedGenerationTraceService().build(
        generation_result()
    ).to_dict()

    assert data["request_id"] == "request-1"
    assert data["claim_count"] == 1
    assert data["citation_count"] == 2

    serialized = str(data).lower()
    assert "raw_text" not in serialized
    assert "user_query" not in serialized
    assert "statement" not in serialized


def test_trace_rejects_citation_outside_selected_context() -> None:
    with pytest.raises(
        ValueError,
        match="subset of selected context",
    ):
        GroundedGenerationTrace(
            request_id="request-1",
            prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
            answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
            provider_identity="TEST",
            model_identity="TEST@1",
            selected_knowledge_identities=(
                "WORLD_A@1",
            ),
            cited_knowledge_identities=(
                "MISSING@1",
            ),
            claim_count=1,
            citation_count=1,
            validation_status="ADMISSIBLE",
        )


def test_trace_requires_admissible_validation() -> None:
    with pytest.raises(
        ValueError,
        match="ADMISSIBLE",
    ):
        GroundedGenerationTrace(
            request_id="request-1",
            prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
            answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
            provider_identity="TEST",
            model_identity="TEST@1",
            selected_knowledge_identities=(),
            cited_knowledge_identities=(),
            claim_count=0,
            citation_count=0,
            validation_status="REJECTED",
        )


def test_trace_service_rejects_wrong_result_type() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedGenerationResult",
    ):
        GroundedGenerationTraceService().build(
            object()  # type: ignore[arg-type]
        )
