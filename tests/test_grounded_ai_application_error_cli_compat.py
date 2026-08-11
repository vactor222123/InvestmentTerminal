import pytest

from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.application.errors import (
    GroundedAIApplicationError,
)
from investment_terminal.cli import grounded_ai_live


def test_main_accepts_application_error_contract(
    monkeypatch,
    tmp_path,
) -> None:
    class Application:
        def execute(self, request):
            raise GroundedAIApplicationError(
                category="POLICY_DENIED",
                code="APPLICATION_POLICY_DENIED",
                message="denied",
            )

    monkeypatch.setattr(
        grounded_ai_live,
        "build_live_grounded_ai_application",
        lambda **kwargs: Application(),
    )

    with pytest.raises(
        SystemExit,
    ):
        grounded_ai_live.main(
            [
                "--live",
                "--database",
                str(tmp_path / "knowledge.db"),
                "--request-id",
                "r",
                "--query",
                "Q",
                "--model",
                "gpt-test",
                "--allow-model",
                "gpt-test",
            ]
        )


def test_legacy_run_live_preserves_permission_error_contract() -> None:
    class Query:
        def list_all(self):
            raise AssertionError(
                "query must not execute before budget denial"
            )

    class Service:
        def generate(self, **kwargs):
            raise AssertionError(
                "provider must not execute before budget denial"
            )

    with pytest.raises(
        PermissionError,
        match="requested output token limit",
    ):
        grounded_ai_live._run_live(
            query=Query(),  # type: ignore[arg-type]
            request_id="request-1",
            user_query="Question",
            model_identity="gpt-test",
            api_key_environment_variable="KEY",
            timeout_seconds=10,
            max_retries=0,
            subjects=(),
            max_items=None,
            budget_policy=GroundedProviderBudgetPolicy(
                max_output_tokens=100,
            ),
            requested_max_output_tokens=101,
            generation_service=Service(),
        )
