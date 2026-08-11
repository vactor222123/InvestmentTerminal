import pytest

from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.application.errors import (
    GroundedAIApplicationError,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
)
from investment_terminal.application.live_grounded_ai import (
    LiveGroundedAIApplicationService,
)


def test_request_budget_denial_precedes_query_and_generation() -> None:
    class Query:
        def list_all(self):
            raise AssertionError(
                "query must not execute before budget denial"
            )

    class Service:
        def generate(self, **kwargs):
            raise AssertionError(
                "generation must not execute before budget denial"
            )

    application = LiveGroundedAIApplicationService(
        query=Query(),
        generation_service=Service(),
        budget_policy=GroundedProviderBudgetPolicy(
            max_output_tokens=100,
        ),
        requested_max_output_tokens=101,
    )

    with pytest.raises(
        GroundedAIApplicationError,
    ) as caught:
        application.execute(
            GroundedAIApplicationRequest(
                request_id="request-1",
                user_query="Question",
            )
        )

    assert caught.value.category == "POLICY_DENIED"
    assert caught.value.code == "APPLICATION_POLICY_DENIED"
    assert "requested output token limit" in str(
        caught.value
    )
    assert isinstance(
        caught.value.__cause__,
        PermissionError,
    )


def test_structural_query_dependency_requires_list_all() -> None:
    class Query:
        pass

    class Service:
        def generate(self, **kwargs):
            raise AssertionError

    with pytest.raises(
        TypeError,
        match="query must provide callable list_all",
    ):
        LiveGroundedAIApplicationService(
            query=Query(),
            generation_service=Service(),
        )


def test_structural_generation_dependency_requires_generate() -> None:
    class Query:
        def list_all(self):
            return ()

    class Service:
        pass

    with pytest.raises(
        TypeError,
        match="generation_service must provide callable generate",
    ):
        LiveGroundedAIApplicationService(
            query=Query(),
            generation_service=Service(),
        )
