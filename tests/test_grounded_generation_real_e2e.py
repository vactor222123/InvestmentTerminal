import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from investment_terminal.ai.generation_recording import (
    GroundedGenerationRecordingService,
)
from investment_terminal.ai.generation_sqlite_repository import (
    SQLiteGroundedGenerationRepository,
)
from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.ai.model_adapter import (
    StaticGroundedModelAdapter,
)
from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
)
from investment_terminal.api.http_handler import (
    GroundedAIHTTPHandler,
)
from investment_terminal.application.grounded_generation_history import (
    GroundedGenerationHistoryService,
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
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)
from investment_terminal.server.fastapi_app import (
    create_grounded_ai_fastapi_app,
)


RECORDED_AT = datetime(
    2026,
    8,
    15,
    15,
    0,
    tzinfo=timezone.utc,
)


def knowledge_record() -> KnowledgeRecord:
    return KnowledgeRecord(
        knowledge_id="WORLD_A",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="WORLD A was present historically.",
        valid_from=datetime(
            2026,
            8,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        valid_to=None,
        generated_at=datetime(
            2026,
            8,
            2,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id=(
                    "11111111-1111-4111-8111-"
                    "111111111111"
                ),
                observed_at=datetime(
                    2026,
                    8,
                    1,
                    12,
                    0,
                    tzinfo=timezone.utc,
                ),
                checksum_sha256="a" * 64,
            ),
        ),
    )


def grounded_raw_answer() -> str:
    return json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": (
                "EVIDENCE_GROUNDED_ANSWER@1"
            ),
            "claims": [
                {
                    "text": (
                        "Historical context is available."
                    ),
                    "citations": [
                        {
                            "knowledge_identity": (
                                "WORLD_A@1"
                            ),
                            "statement": (
                                "WORLD A was present "
                                "historically."
                            ),
                            "provenance_status": (
                                "COMPLETE"
                            ),
                        }
                    ],
                }
            ],
        }
    )


def build_handler(
    *,
    knowledge_database: Path,
    generation_repository: (
        SQLiteGroundedGenerationRepository
    ),
) -> GroundedAIHTTPHandler:
    query = KnowledgeQueryService(
        repository=SQLiteKnowledgeRecordRepository(
            KnowledgeSQLiteStore(
                knowledge_database
            )
        )
    )
    generation_service = GroundedGenerationService(
        adapter=StaticGroundedModelAdapter(
            provider_identity="STATIC_TEST",
            model_identity="STATIC_MODEL@1",
            raw_text=grounded_raw_answer(),
        )
    )
    application = LiveGroundedAIApplicationService(
        query=query,
        generation_service=generation_service,
        generation_recording_service=(
            GroundedGenerationRecordingService(
                repository=generation_repository,
                clock=lambda: RECORDED_AT,
            )
        ),
    )
    return GroundedAIHTTPHandler(
        application_service=application
    )


def test_real_grounded_generation_persistence_flow_end_to_end(
    tmp_path: Path,
) -> None:
    knowledge_database = (
        tmp_path
        / "knowledge.db"
    )
    knowledge_repository = (
        SQLiteKnowledgeRecordRepository(
            KnowledgeSQLiteStore(
                knowledge_database
            )
        )
    )
    knowledge_repository.add(
        knowledge_record()
    )

    generation_database = (
        tmp_path
        / "grounded_generations.db"
    )
    generation_repository = (
        SQLiteGroundedGenerationRepository(
            GroundedGenerationSQLiteStore(
                generation_database
            )
        )
    )

    authenticator = (
        GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret"
        )
    )

    write_app = create_grounded_ai_fastapi_app(
        handler=build_handler(
            knowledge_database=knowledge_database,
            generation_repository=(
                generation_repository
            ),
        ),
        authenticator=authenticator,
        grounded_generation_history_service=(
            GroundedGenerationHistoryService(
                repository=generation_repository
            )
        ),
    )
    write_client = TestClient(
        write_app,
        raise_server_exceptions=False,
    )

    generated = write_client.post(
        "/v1/grounded-ai",
        headers={
            "X-API-Key": "server-secret",
        },
        json={
            "request_id": "request-e2e-1",
            "query": (
                "What historical context "
                "is available?"
            ),
            "subjects": [
                "WORLD",
            ],
        },
    )

    assert generated.status_code == 200
    generated_payload = generated.json()
    assert generated_payload["status"] == "SUCCESS"
    assert generated_payload["request_id"] == (
        "request-e2e-1"
    )
    assert generated_payload["data"]["trace"][
        "validation_status"
    ] == "ADMISSIBLE"

    reopened_repository = (
        SQLiteGroundedGenerationRepository(
            GroundedGenerationSQLiteStore(
                generation_database
            )
        )
    )
    persisted = reopened_repository.require(
        "request-e2e-1"
    )

    assert persisted.generated_at == RECORDED_AT
    assert persisted.request_id == "request-e2e-1"
    assert persisted.provider_identity == (
        "STATIC_TEST"
    )
    assert persisted.model_identity == (
        "STATIC_MODEL@1"
    )
    assert persisted.selected_knowledge_identities == (
        "WORLD_A@1",
    )
    assert persisted.cited_knowledge_identities == (
        "WORLD_A@1",
    )
    assert persisted.trace[
        "validation_status"
    ] == "ADMISSIBLE"

    read_app = create_grounded_ai_fastapi_app(
        handler=build_handler(
            knowledge_database=knowledge_database,
            generation_repository=(
                reopened_repository
            ),
        ),
        authenticator=authenticator,
        grounded_generation_history_service=(
            GroundedGenerationHistoryService(
                repository=reopened_repository
            )
        ),
    )
    read_client = TestClient(
        read_app,
        raise_server_exceptions=False,
    )

    exact = read_client.get(
        "/v1/grounded-generations/request-e2e-1",
        headers={
            "X-API-Key": "server-secret",
        },
    )

    assert exact.status_code == 200
    exact_record = exact.json()["data"]["record"]

    assert exact_record == persisted.to_dict()
    assert exact_record["generation"] == (
        generated_payload["data"]["generation"]
    )
    assert exact_record["trace"] == (
        generated_payload["data"]["trace"]
    )

    recent = read_client.get(
        "/v1/grounded-generations",
        params={
            "limit": 1,
        },
        headers={
            "X-API-Key": "server-secret",
        },
    )

    assert recent.status_code == 200
    assert recent.json()["data"][
        "count"
    ] == 1
    assert recent.json()["data"]["records"][
        0
    ] == persisted.to_dict()
