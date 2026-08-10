import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
    build_openai_grounded_generation_service,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportResponse,
)
from investment_terminal.cli.grounded_ai_live import (
    _run_live,
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


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def seed(database: Path) -> KnowledgeQueryService:
    repository = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            database
        )
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


def grounded_answer_json() -> str:
    return json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
            "claims": [
                {
                    "text": "Historical context is available.",
                    "citations": [
                        {
                            "knowledge_identity": "WORLD_CONTEXT@1",
                            "statement": "WORLD was present historically.",
                            "provenance_status": "COMPLETE",
                        }
                    ],
                }
            ],
        }
    )


def openai_response_body() -> str:
    return json.dumps(
        {
            "id": "resp_test",
            "object": "response",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "id": "msg_test",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": grounded_answer_json(),
                        }
                    ],
                }
            ],
        }
    )


class RetryThenSuccessOpenAITransport(
    GroundedProviderTransport
):
    def __init__(self) -> None:
        self.calls = 0
        self.requests = []

    def send(self, request):
        self.calls += 1
        self.requests.append(
            request
        )

        if self.calls == 1:
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message="simulated transient provider failure",
                retryable=True,
            )

        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(
                (
                    "x-request-id",
                    "provider-internal-id",
                ),
            ),
            body=openai_response_body(),
        )


def test_real_knowledge_to_openai_composition_e2e_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "knowledge.db"
    query = seed(
        database
    )

    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "test-secret-value",
    )

    transport = RetryThenSuccessOpenAITransport()
    generation_service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=15,
        max_retries=2,
        transport=transport,
    )

    report = _run_live(
        query=query,
        request_id="request-1",
        user_query="What historical context is available?",
        model_identity="gpt-test",
        api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
        timeout_seconds=15,
        max_retries=2,
        subjects=("WORLD",),
        max_items=1,
        generation_service=generation_service,
    )

    generation = report["generation"]
    trace = report["trace"]

    assert generation["prompt"]["protocol_identity"] == (
        "EVIDENCE_GROUNDED_PROMPT@1"
    )
    assert generation["answer"]["protocol_identity"] == (
        "EVIDENCE_GROUNDED_ANSWER@1"
    )
    assert generation["validation"]["status"] == "ADMISSIBLE"

    assert trace["provider_identity"] == "OPENAI"
    assert trace["model_identity"] == "gpt-test"
    assert trace["selected_knowledge_identities"] == [
        "WORLD_CONTEXT@1"
    ]
    assert trace["cited_knowledge_identities"] == [
        "WORLD_CONTEXT@1"
    ]
    assert trace["provider_operation"] == {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
    }

    assert transport.calls == 2
    assert all(
        request.url
        == "https://api.openai.com/v1/responses"
        for request in transport.requests
    )
    assert all(
        request.request_id == "request-1"
        for request in transport.requests
    )


def test_provider_e2e_preserves_secret_and_transport_output_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = seed(
        tmp_path / "knowledge.db"
    )
    secret = "test-secret-value"

    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        secret,
    )

    transport = RetryThenSuccessOpenAITransport()
    service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=15,
        max_retries=2,
        transport=transport,
    )

    report = _run_live(
        query=query,
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
        timeout_seconds=15,
        max_retries=2,
        subjects=("WORLD",),
        max_items=1,
        generation_service=service,
    )

    serialized = json.dumps(
        report,
        sort_keys=True,
    ).lower()

    for forbidden in (
        secret,
        "authorization",
        "bearer ",
        "provider-internal-id",
        "https://api.openai.com",
        "x-client-request-id",
    ):
        assert forbidden.lower() not in serialized

    sent_headers = dict(
        transport.requests[0].headers
    )
    assert sent_headers["Authorization"] == (
        f"Bearer {secret}"
    )
    assert sent_headers["X-Client-Request-Id"] == (
        "request-1"
    )


def test_provider_e2e_creates_no_history_or_ai_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "knowledge.db"
    query = seed(
        database
    )
    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "test-secret-value",
    )

    service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=15,
        max_retries=2,
        transport=RetryThenSuccessOpenAITransport(),
    )

    _run_live(
        query=query,
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
        timeout_seconds=15,
        max_retries=2,
        subjects=("WORLD",),
        max_items=1,
        generation_service=service,
    )

    assert database.exists()
    assert not (
        tmp_path / "history.db"
    ).exists()
    assert not (
        tmp_path / "ai.db"
    ).exists()
