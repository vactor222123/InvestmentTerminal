import json
from datetime import datetime, timezone

import pytest

from investment_terminal.ai.generation_recording import (
    GroundedGenerationRecordingService,
)
from investment_terminal.ai.generation_repository import (
    InMemoryGroundedGenerationRepository,
)
from investment_terminal.ai.model_adapter import (
    StaticGroundedModelAdapter,
)
from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
)
from investment_terminal.application.live_grounded_ai import (
    LiveGroundedAIApplicationService,
)
from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelopeService,
)
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)


RECORDED_AT = datetime(
    2026,
    8,
    15,
    13,
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


def envelope():
    return KnowledgeRecordEnvelopeService().build(
        KnowledgeRecord(
            knowledge_id="WORLD_A",
            knowledge_type="FACT",
            version=1,
            subject_key="WORLD",
            statement="WORLD A was present historically.",
            valid_from=dt(1),
            valid_to=None,
            generated_at=dt(2),
            evidence=(
                KnowledgeEvidenceReference(
                    evidence_type="HISTORICAL_SNAPSHOT",
                    evidence_id=(
                        "11111111-1111-4111-8111-"
                        "111111111111"
                    ),
                    observed_at=dt(1),
                    checksum_sha256="a" * 64,
                ),
            ),
        )
    )


class Query:
    def list_all(self):
        return (
            envelope(),
        )


def generation_service(
    *,
    valid_citation: bool = True,
):
    identity = (
        "WORLD_A@1"
        if valid_citation
        else "MISSING@1"
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
                            "knowledge_identity": identity,
                            "statement": (
                                "WORLD A was present historically."
                            ),
                            "provenance_status": "COMPLETE",
                        }
                    ],
                }
            ],
        }
    )
    return GroundedGenerationService(
        adapter=StaticGroundedModelAdapter(
            provider_identity="STATIC_TEST",
            model_identity="STATIC_MODEL@1",
            raw_text=raw,
        )
    )


def request():
    return GroundedAIApplicationRequest(
        request_id="request-1",
        user_query="What context is available?",
    )


def test_successful_admissible_generation_is_recorded() -> None:
    repository = InMemoryGroundedGenerationRepository()
    recorder = GroundedGenerationRecordingService(
        repository=repository,
        clock=lambda: RECORDED_AT,
    )
    service = LiveGroundedAIApplicationService(
        query=Query(),
        generation_service=generation_service(),
        generation_recording_service=recorder,
    )

    result = service.execute(
        request()
    )

    persisted = repository.require(
        "request-1"
    )
    assert persisted.generated_at == RECORDED_AT
    assert persisted.generation == result.generation
    assert persisted.trace == result.trace
    assert persisted.trace[
        "validation_status"
    ] == "ADMISSIBLE"


def test_without_recorder_existing_behavior_is_unchanged() -> None:
    service = LiveGroundedAIApplicationService(
        query=Query(),
        generation_service=generation_service(),
    )

    result = service.execute(
        request()
    )

    assert result.request_id == "request-1"
    assert result.trace[
        "validation_status"
    ] == "ADMISSIBLE"


def test_rejected_generation_is_never_recorded() -> None:
    repository = InMemoryGroundedGenerationRepository()
    recorder = GroundedGenerationRecordingService(
        repository=repository,
        clock=lambda: RECORDED_AT,
    )
    service = LiveGroundedAIApplicationService(
        query=Query(),
        generation_service=generation_service(
            valid_citation=False
        ),
        generation_recording_service=recorder,
    )

    with pytest.raises(Exception):
        service.execute(
            request()
        )

    assert repository.list_all() == ()


def test_duplicate_request_identity_fails_closed() -> None:
    repository = InMemoryGroundedGenerationRepository()
    recorder = GroundedGenerationRecordingService(
        repository=repository,
        clock=lambda: RECORDED_AT,
    )
    service = LiveGroundedAIApplicationService(
        query=Query(),
        generation_service=generation_service(),
        generation_recording_service=recorder,
    )

    service.execute(
        request()
    )

    with pytest.raises(Exception):
        service.execute(
            request()
        )

    assert len(repository.list_all()) == 1
