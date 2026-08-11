import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
)
from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
    StaticGroundedProviderCredentialSource,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.openai_adapter import (
    OpenAIGroundedModelAdapter,
)
from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
)
from investment_terminal.ai.providers.sleeper import (
    GroundedProviderSleeper,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportResponse,
)
from investment_terminal.cli.grounded_ai_live import (
    _print_human,
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


def response_body() -> str:
    return json.dumps(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "answer_id": "answer-1",
                                    "protocol_identity": (
                                        "EVIDENCE_GROUNDED_ANSWER@1"
                                    ),
                                    "claims": [
                                        {
                                            "text": (
                                                "Historical context "
                                                "is available."
                                            ),
                                            "citations": [
                                                {
                                                    "knowledge_identity": (
                                                        "WORLD_CONTEXT@1"
                                                    ),
                                                    "statement": (
                                                        "WORLD was present "
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
                            ),
                        }
                    ],
                }
            ],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        }
    )


class RecordingSleeper(
    GroundedProviderSleeper
):
    def __init__(self) -> None:
        self.delays: list[Decimal] = []

    def sleep(
        self,
        *,
        delay_seconds: Decimal,
    ) -> None:
        self.delays.append(delay_seconds)


class RateLimitThenSuccessTransport(
    GroundedProviderTransport
):
    """
    Offline-realistic representation of a provider 429 followed by success.

    The first failure carries the canonical retry_after_seconds metadata that
    the HTTP transport derives from Retry-After.
    """

    def __init__(self) -> None:
        self.calls = 0

    def send(self, request):
        self.calls += 1

        if self.calls == 1:
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message=(
                    "provider HTTP 429: "
                    "raw-rate-limit-body-must-not-appear"
                ),
                retryable=True,
                retry_after_seconds=Decimal("5"),
            )

        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(
                (
                    "x-provider-secret-header",
                    "must-not-appear",
                ),
            ),
            body=response_body(),
        )


def generation_service(
    *,
    transport: RateLimitThenSuccessTransport,
    sleeper: RecordingSleeper,
) -> GroundedGenerationService:
    execution = GroundedProviderExecutionService(
        transport=transport,
        retry_delay_policy=(
            GroundedProviderRetryDelayPolicy(
                initial_delay_seconds=Decimal("1"),
                multiplier=Decimal("2"),
                maximum_delay_seconds=Decimal("4"),
            )
        ),
        sleeper=sleeper,
    )

    adapter = OpenAIGroundedModelAdapter(
        config=GroundedProviderConfig(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=2,
        ),
        credentials=(
            StaticGroundedProviderCredentialSource(
                provider_identity="OPENAI",
                api_key="secret-value",
            )
        ),
        execution=execution,
    )
    return GroundedGenerationService(
        adapter=adapter
    )


def test_sprint23_resilience_path_retries_after_rate_limit_and_audits_delay(
    tmp_path: Path,
    capsys,
) -> None:
    transport = RateLimitThenSuccessTransport()
    sleeper = RecordingSleeper()

    report = _run_live(
        query=query_service(
            tmp_path / "knowledge.db"
        ),
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable="UNUSED",
        timeout_seconds=10,
        max_retries=2,
        subjects=("WORLD",),
        max_items=1,
        generation_service=generation_service(
            transport=transport,
            sleeper=sleeper,
        ),
    )

    assert transport.calls == 2

    # Local retry policy says 1 second, provider asks for 5.
    # Conservative precedence must therefore apply 5 seconds.
    assert sleeper.delays == [
        Decimal("5")
    ]

    assert (
        report["generation"]["validation"]["status"]
        == "ADMISSIBLE"
    )
    assert report["trace"]["provider_operation"] == {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
        "retry_delay_seconds": ["5"],
    }
    assert report["trace"]["provider_usage"] == {
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
    }

    _print_human(report)
    human = capsys.readouterr().out

    assert "Attempts     : 2" in human
    assert "Retries      : 1" in human
    assert "Retry Delays : 5 s" in human
    assert "HTTP Status  : 200" in human
    assert "Transport    : SUCCESS" in human

    serialized = json.dumps(
        report,
        sort_keys=True,
    ).lower()
    human_lower = human.lower()

    for forbidden in (
        "secret-value",
        "x-provider-secret-header",
        "must-not-appear",
        "raw-rate-limit-body-must-not-appear",
        "authorization",
        "retry-after",
    ):
        assert forbidden not in serialized
        assert forbidden not in human_lower


def test_sprint23_resilience_path_is_deterministic_without_real_sleep(
    tmp_path: Path,
) -> None:
    transport = RateLimitThenSuccessTransport()
    sleeper = RecordingSleeper()

    report = _run_live(
        query=query_service(
            tmp_path / "knowledge.db"
        ),
        request_id="request-2",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable="UNUSED",
        timeout_seconds=10,
        max_retries=2,
        subjects=("WORLD",),
        max_items=1,
        generation_service=generation_service(
            transport=transport,
            sleeper=sleeper,
        ),
    )

    assert sleeper.delays == [
        Decimal("5")
    ]
    assert (
        report["trace"]["provider_operation"][
            "retry_delay_seconds"
        ]
        == ["5"]
    )
