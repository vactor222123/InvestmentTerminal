import json
from datetime import datetime, timezone
from pathlib import Path

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
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.query_service import (
    KnowledgeQueryService,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


def dt(day: int):
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def query_service(
    database: Path,
) -> KnowledgeQueryService:
    repository = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(database)
    )
    repository.add(
        KnowledgeRecord(
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
                    evidence_id=(
                        "11111111-1111-4111-8111-111111111111"
                    ),
                    observed_at=dt(1),
                    checksum_sha256="a" * 64,
                ),
            ),
        )
    )
    return KnowledgeQueryService(
        repository=repository
    )


def generation_service():
    answer = json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": (
                "EVIDENCE_GROUNDED_ANSWER@1"
            ),
            "claims": [
                {
                    "text": "Historical context is available.",
                    "citations": [
                        {
                            "knowledge_identity": "WORLD_CONTEXT@1",
                            "statement": (
                                "WORLD was present historically."
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
            provider_identity="STATIC",
            model_identity="STATIC@1",
            raw_text=answer,
        )
    )


def test_concrete_application_service_executes_grounded_use_case(
    tmp_path: Path,
) -> None:
    service = LiveGroundedAIApplicationService(
        query=query_service(
            tmp_path / "knowledge.db"
        ),
        generation_service=generation_service(),
    )

    result = service.execute(
        GroundedAIApplicationRequest(
            request_id="request-1",
            user_query="Question",
            subject_keys=("WORLD",),
            max_items=1,
        )
    )

    assert result.request_id == "request-1"
    assert (
        result.generation["validation"]["status"]
        == "ADMISSIBLE"
    )
    assert result.trace["request_id"] == "request-1"
    assert result.trace[
        "selected_knowledge_identities"
    ] == ["WORLD_CONTEXT@1"]


def test_application_result_preserves_existing_report_shape(
    tmp_path: Path,
) -> None:
    service = LiveGroundedAIApplicationService(
        query=query_service(
            tmp_path / "knowledge.db"
        ),
        generation_service=generation_service(),
    )

    result = service.execute(
        GroundedAIApplicationRequest(
            request_id="request-1",
            user_query="Question",
        )
    )

    assert set(result.to_dict()) == {
        "generation",
        "trace",
    }
