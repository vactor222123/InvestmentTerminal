import pytest

from investment_terminal.ai.providers.governance import GroundedProviderGovernancePolicy
from investment_terminal.cli.grounded_ai_live import (
    _governance_policy,
    _run_live,
    build_argument_parser,
)


def test_cli_allow_model_is_explicit_and_repeatable() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id", "r1",
            "--query", "Question",
            "--model", "gpt-a",
            "--allow-model", "gpt-a",
            "--allow-model", "gpt-b",
        ]
    )
    assert options.allow_model == ["gpt-a", "gpt-b"]


def test_cli_default_allowlist_is_empty_fail_closed() -> None:
    options = build_argument_parser().parse_args(
        [
            "--live",
            "--request-id", "r1",
            "--query", "Question",
            "--model", "gpt-a",
        ]
    )
    assert options.allow_model == []
    policy = _governance_policy(tuple(options.allow_model))
    with pytest.raises(PermissionError):
        policy.require_allowed(
            provider_identity="OPENAI",
            model_identity="gpt-a",
        )


def test_cli_policy_allows_only_explicit_models() -> None:
    policy = _governance_policy(("gpt-a", "gpt-b"))
    assert isinstance(policy, GroundedProviderGovernancePolicy)
    policy.require_allowed(provider_identity="OPENAI", model_identity="gpt-a")
    with pytest.raises(PermissionError):
        policy.require_allowed(provider_identity="OPENAI", model_identity="gpt-c")


def test_run_live_requires_policy_when_building_production_service() -> None:
    class Query:
        def list_all(self):
            raise AssertionError("query must not run before governance failure")

    with pytest.raises(
        PermissionError,
        match="explicit governance policy",
    ):
        _run_live(
            query=Query(),  # type: ignore[arg-type]
            request_id="r1",
            user_query="Question",
            model_identity="gpt-a",
            api_key_environment_variable="KEY",
            timeout_seconds=10,
            max_retries=1,
            subjects=(),
            max_items=None,
            governance_policy=None,
            generation_service=None,
        )
