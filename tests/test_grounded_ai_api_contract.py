from investment_terminal.api.grounded_ai import (
    GroundedAIAPIAdapter,
    GroundedAIAPIRequest,
)
from investment_terminal.application.errors import (
    GroundedAIApplicationError,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)


class SuccessService(
    GroundedAIApplicationService
):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={
                "prompt": {
                    "request_id": request.request_id,
                }
            },
            trace={
                "request_id": request.request_id,
            },
        )


class FailureService(
    GroundedAIApplicationService
):
    def execute(self, request):
        raise GroundedAIApplicationError(
            category="POLICY_DENIED",
            code="APPLICATION_POLICY_DENIED",
            message="denied",
        )


def test_api_request_maps_to_application_request() -> None:
    request = GroundedAIAPIRequest.from_dict(
        {
            "request_id": "request-1",
            "query": "Question",
            "subjects": [
                "WORLD",
            ],
            "max_items": 3,
        }
    )

    mapped = request.to_application_request()

    assert mapped.request_id == "request-1"
    assert mapped.user_query == "Question"
    assert mapped.subject_keys == (
        "WORLD",
    )
    assert mapped.max_items == 3


def test_api_request_rejects_unknown_fields() -> None:
    try:
        GroundedAIAPIRequest.from_dict(
            {
                "request_id": "r",
                "query": "Q",
                "unexpected": True,
            }
        )
    except ValueError as exc:
        assert "unknown API request fields" in str(
            exc
        )
    else:
        raise AssertionError(
            "unknown fields must fail closed"
        )


def test_api_adapter_returns_stable_success_response() -> None:
    adapter = GroundedAIAPIAdapter(
        application_service=SuccessService()
    )

    response = adapter.handle(
        GroundedAIAPIRequest(
            request_id="request-1",
            query="Question",
        )
    )

    assert response.to_dict() == {
        "status": "SUCCESS",
        "request_id": "request-1",
        "data": {
            "generation": {
                "prompt": {
                    "request_id": "request-1",
                }
            },
            "trace": {
                "request_id": "request-1",
            },
        },
    }


def test_api_adapter_returns_application_error_without_exception_leak() -> None:
    adapter = GroundedAIAPIAdapter(
        application_service=FailureService()
    )

    response = adapter.handle(
        GroundedAIAPIRequest(
            request_id="request-1",
            query="Question",
        )
    )

    assert response.to_dict() == {
        "status": "ERROR",
        "request_id": "request-1",
        "error": {
            "category": "POLICY_DENIED",
            "code": "APPLICATION_POLICY_DENIED",
            "message": "denied",
        },
    }


def test_api_contract_contains_no_framework_or_http_status_semantics() -> None:
    response = GroundedAIAPIAdapter(
        application_service=SuccessService()
    ).handle(
        GroundedAIAPIRequest(
            request_id="request-1",
            query="Question",
        )
    )

    serialized = response.to_dict()
    assert "http_status" not in serialized
    assert "headers" not in serialized
