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
    GroundedProviderTransportResponse,
)
from investment_terminal.cli.grounded_ai_live import (
    _run_live,
    build_argument_parser,
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


def query_service(
    tmp_path: Path,
) -> KnowledgeQueryService:
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            tmp_path / "knowledge.db"
        )
    )
    repo.add(
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
        repository=repo
    )


def answer_json() -> str:
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


class FakeOpenAITransport(
    GroundedProviderTransport
):
    def __init__(self) -> None:
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        body = json.dumps(
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": answer_json(),
                            }
                        ],
                    }
                ],
            }
        )
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body=body,
        )


def test_composition_uses_environment_credentials_and_injected_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "secret-value",
    )
    transport = FakeOpenAITransport()

    service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=1,
        transport=transport,
    )

    assert service is not None


def test_composed_service_runs_offline_with_fake_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "secret-value",
    )
    transport = FakeOpenAITransport()
    service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=1,
        transport=transport,
    )

    report = _run_live(
        query=query_service(tmp_path),
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
        timeout_seconds=10,
        max_retries=1,
        subjects=("WORLD",),
        max_items=1,
        generation_service=service,
    )

    assert report["trace"]["provider_identity"] == "OPENAI"
    assert report["trace"]["model_identity"] == "gpt-test"
    assert report["trace"]["validation_status"] == "ADMISSIBLE"
    assert transport.requests[0].url == (
        "https://api.openai.com/v1/responses"
    )


def test_live_cli_requires_explicit_live_flag() -> None:
    options = build_argument_parser().parse_args(
        [
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--model",
            "gpt-test",
        ]
    )
    assert options.live is False


def test_cli_accepts_env_name_not_secret_value() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--model",
            "gpt-test",
            "--api-key-env",
            "CUSTOM_OPENAI_KEY",
        ]
    )

    assert options.api_key_env == "CUSTOM_OPENAI_KEY"
    assert not hasattr(
        options,
        "api_key",
    )


def test_default_api_key_environment_name_is_explicit() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--model",
            "gpt-test",
        ]
    )

    assert options.api_key_env == (
        "INVESTMENT_TERMINAL_OPENAI_API_KEY"
    )


def test_invalid_operational_values_are_rejected() -> None:
    with pytest.raises(SystemExit):
        build_argument_parser().parse_args(
            [
                "--live",
                "--request-id",
                "request-1",
                "--query",
                "Question",
                "--model",
                "gpt-test",
                "--timeout-seconds",
                "0",
            ]
        )

    with pytest.raises(SystemExit):
        build_argument_parser().parse_args(
            [
                "--live",
                "--request-id",
                "request-1",
                "--query",
                "Question",
                "--model",
                "gpt-test",
                "--max-retries",
                "-1",
            ]
        )
