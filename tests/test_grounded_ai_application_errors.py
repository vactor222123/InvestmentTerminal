import pytest

from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.application.errors import (
    GroundedAIApplicationError,
    map_application_failure,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
)
from investment_terminal.application.live_grounded_ai import (
    LiveGroundedAIApplicationService,
)


def test_policy_denial_maps_to_stable_application_error() -> None:
    class Query:
        def list_all(self):
            raise AssertionError

    class Service:
        def generate(self, **kwargs):
            raise AssertionError

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

    error = caught.value
    assert error.category == "POLICY_DENIED"
    assert error.code == "APPLICATION_POLICY_DENIED"
    assert "requested output token limit" in str(error)
    assert isinstance(
        error.__cause__,
        PermissionError,
    )


def test_invalid_request_maps_to_stable_application_error() -> None:
    class Query:
        def list_all(self):
            return ()

    class Service:
        def generate(self, **kwargs):
            raise ValueError("bad generation input")

    application = LiveGroundedAIApplicationService(
        query=Query(),
        generation_service=Service(),
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

    assert caught.value.category == "INVALID_REQUEST"
    assert caught.value.code == "APPLICATION_INVALID_REQUEST"


def test_runtime_failure_maps_to_execution_failed() -> None:
    mapped = map_application_failure(
        RuntimeError(
            "provider failed"
        )
    )

    assert mapped.category == "EXECUTION_FAILED"
    assert mapped.code == "APPLICATION_EXECUTION_FAILED"


def test_unknown_failure_does_not_expose_raw_message() -> None:
    mapped = map_application_failure(
        Exception(
            "secret low-level detail"
        )
    )

    assert mapped.category == "INTERNAL_ERROR"
    assert mapped.code == "APPLICATION_INTERNAL_ERROR"
    assert "secret low-level detail" not in str(mapped)


def test_error_serialization_is_stable() -> None:
    error = GroundedAIApplicationError(
        category="POLICY_DENIED",
        code="APPLICATION_POLICY_DENIED",
        message="denied",
    )

    assert error.to_dict() == {
        "category": "POLICY_DENIED",
        "code": "APPLICATION_POLICY_DENIED",
        "message": "denied",
    }
