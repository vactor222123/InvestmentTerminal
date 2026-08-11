import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
    build_openai_grounded_generation_service,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.ai.providers.pricing import (
    GroundedProviderPricingEntry,
    GroundedProviderPricingPolicy,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportResponse,
)
from investment_terminal.cli.grounded_ai_live import _run_live
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.query_service import KnowledgeQueryService
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import KnowledgeSQLiteStore


def dt(day: int) -> datetime:
    return datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc)


def query_service(database: Path) -> KnowledgeQueryService:
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
                    evidence_id="11111111-1111-4111-8111-111111111111",
                    observed_at=dt(1),
                    checksum_sha256="a" * 64,
                ),
            ),
        )
    )
    return KnowledgeQueryService(repository=repository)


def governance() -> GroundedProviderGovernancePolicy:
    return GroundedProviderGovernancePolicy(
        allowed_models=(
            GroundedProviderModelAllowance(
                provider_identity="OPENAI",
                model_identity="gpt-test",
            ),
        )
    )


def pricing() -> GroundedProviderPricingPolicy:
    return GroundedProviderPricingPolicy(
        entries=(
            GroundedProviderPricingEntry(
                provider_identity="OPENAI",
                model_identity="gpt-test",
                currency="USD",
                input_cost_per_million_tokens=Decimal("2.50"),
                output_cost_per_million_tokens=Decimal("10.00"),
            ),
        )
    )


def response_body(
    *,
    input_tokens: int = 1000,
    output_tokens: int = 200,
) -> str:
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
                                                "Historical context is available."
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
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }
    )


class CapturingTransport(GroundedProviderTransport):
    def __init__(
        self,
        *,
        input_tokens: int = 1000,
        output_tokens: int = 200,
    ) -> None:
        self.requests = []
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def send(self, request):
        self.requests.append(request)
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body=response_body(
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        )


def build_service(
    *,
    transport: CapturingTransport,
    max_output_tokens: int,
):
    return build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=0,
        governance_policy=governance(),
        max_output_tokens=max_output_tokens,
        transport=transport,
    )


def test_sprint22_full_control_path_is_admissible_within_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "secret-value",
    )
    transport = CapturingTransport()
    service = build_service(
        transport=transport,
        max_output_tokens=300,
    )

    report = _run_live(
        query=query_service(tmp_path / "knowledge.db"),
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
        timeout_seconds=10,
        max_retries=0,
        subjects=("WORLD",),
        max_items=1,
        governance_policy=governance(),
        pricing_policy=pricing(),
        budget_policy=GroundedProviderBudgetPolicy(
            max_output_tokens=300,
            max_total_tokens=1500,
            max_total_cost=Decimal("0.010000"),
            currency="USD",
        ),
        requested_max_output_tokens=300,
        generation_service=service,
    )

    assert report["generation"]["validation"]["status"] == "ADMISSIBLE"
    assert report["trace"]["provider_usage"] == {
        "input_tokens": 1000,
        "output_tokens": 200,
        "total_tokens": 1200,
    }
    assert report["trace"]["provider_cost"]["total_cost"] == "0.004500"

    request_payload = json.loads(
        transport.requests[0].body
    )
    assert request_payload["max_output_tokens"] == 300


def test_pre_execution_budget_denial_happens_before_query_or_network() -> None:
    class Query:
        def list_all(self):
            raise AssertionError(
                "query must not execute before pre-execution denial"
            )

    class Service:
        def generate(self, **kwargs):
            raise AssertionError(
                "provider service must not execute before budget denial"
            )

    with pytest.raises(
        PermissionError,
        match="requested output token limit",
    ):
        _run_live(
            query=Query(),  # type: ignore[arg-type]
            request_id="request-1",
            user_query="Question",
            model_identity="gpt-test",
            api_key_environment_variable="KEY",
            timeout_seconds=10,
            max_retries=0,
            subjects=(),
            max_items=None,
            pricing_policy=pricing(),
            budget_policy=GroundedProviderBudgetPolicy(
                max_output_tokens=100,
            ),
            requested_max_output_tokens=101,
            generation_service=Service(),
        )


def test_post_execution_total_token_budget_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "secret-value",
    )
    transport = CapturingTransport(
        input_tokens=1000,
        output_tokens=300,
    )
    service = build_service(
        transport=transport,
        max_output_tokens=300,
    )

    with pytest.raises(
        PermissionError,
        match="observed total token usage",
    ):
        _run_live(
            query=query_service(tmp_path / "knowledge.db"),
            request_id="request-1",
            user_query="Question",
            model_identity="gpt-test",
            api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
            timeout_seconds=10,
            max_retries=0,
            subjects=("WORLD",),
            max_items=1,
            governance_policy=governance(),
            pricing_policy=pricing(),
            budget_policy=GroundedProviderBudgetPolicy(
                max_output_tokens=300,
                max_total_tokens=1200,
            ),
            requested_max_output_tokens=300,
            generation_service=service,
        )


def test_post_execution_cost_budget_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        DEFAULT_OPENAI_API_KEY_ENV,
        "secret-value",
    )
    transport = CapturingTransport()
    service = build_service(
        transport=transport,
        max_output_tokens=300,
    )

    with pytest.raises(
        PermissionError,
        match="observed provider cost",
    ):
        _run_live(
            query=query_service(tmp_path / "knowledge.db"),
            request_id="request-1",
            user_query="Question",
            model_identity="gpt-test",
            api_key_environment_variable=DEFAULT_OPENAI_API_KEY_ENV,
            timeout_seconds=10,
            max_retries=0,
            subjects=("WORLD",),
            max_items=1,
            governance_policy=governance(),
            pricing_policy=pricing(),
            budget_policy=GroundedProviderBudgetPolicy(
                max_output_tokens=300,
                max_total_tokens=1500,
                max_total_cost=Decimal("0.004000"),
                currency="USD",
            ),
            requested_max_output_tokens=300,
            generation_service=service,
        )
