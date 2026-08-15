import json
from datetime import datetime, timezone

import pytest

from investment_terminal.ai.audit import (
    GroundedGenerationTraceService,
)
from investment_terminal.ai.generation_persistence_projection import (
    GroundedGenerationPersistenceProjectionService,
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


GENERATED_AT = datetime(
    2026,
    8,
    15,
    12,
    0,
    tzinfo=timezone.utc,
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
                            "statement": (
                                "WORLD A was present historically."
                            ),
                            "provenance_status": "COMPLETE",
                        },
                        {
                            "knowledge_identity": "WORLD_B@1",
                            "statement": (
                                "WORLD B was present historically."
                            ),
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


def test_projects_existing_admissible_result_deterministically() -> None:
    result = generation_result()
    trace = GroundedGenerationTraceService().build(
        result
    )

    persisted = (
        GroundedGenerationPersistenceProjectionService()
        .project(
            result=result,
            trace=trace,
            generated_at=GENERATED_AT,
        )
    )

    assert persisted.request_id == result.prompt.request_id
    assert persisted.generated_at == GENERATED_AT
    assert persisted.generation == result.to_dict()
    assert persisted.trace == trace.to_dict()
    assert (
        persisted.selected_knowledge_identities
        == result.selection.selected_identities
    )
    assert (
        persisted.cited_knowledge_identities
        == result.answer.cited_knowledge_identities
    )


def test_projection_accepts_exact_enriched_application_trace() -> None:
    result = generation_result()
    trace = GroundedGenerationTraceService().build(
        result
    )
    enriched = trace.to_dict()
    enriched["provider_cost"] = {
        "provider_identity": trace.provider_identity,
        "model_identity": trace.model_identity,
        "currency": "EUR",
        "input_cost": "0.001",
        "output_cost": "0.002",
        "total_cost": "0.003",
    }

    persisted = (
        GroundedGenerationPersistenceProjectionService()
        .project(
            result=result,
            trace=trace,
            generated_at=GENERATED_AT,
            trace_data=enriched,
        )
    )

    assert (
        persisted.trace["provider_cost"]["total_cost"]
        == "0.003"
    )


def test_projection_rejects_mismatched_enriched_trace_identity() -> None:
    result = generation_result()
    trace = GroundedGenerationTraceService().build(
        result
    )
    enriched = trace.to_dict()
    enriched["request_id"] = "other-request"

    with pytest.raises(
        ValueError,
        match="trace_data request_id",
    ):
        GroundedGenerationPersistenceProjectionService().project(
            result=result,
            trace=trace,
            generated_at=GENERATED_AT,
            trace_data=enriched,
        )


def test_projection_requires_explicit_aware_generated_at() -> None:
    result = generation_result()
    trace = GroundedGenerationTraceService().build(
        result
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        GroundedGenerationPersistenceProjectionService().project(
            result=result,
            trace=trace,
            generated_at=datetime(
                2026,
                8,
                15,
                12,
                0,
            ),
        )
