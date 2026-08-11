from investment_terminal.api.http_handler import (
    GroundedAIHTTPHandler,
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


class PolicyDeniedService(
    GroundedAIApplicationService
):
    def execute(self, request):
        raise GroundedAIApplicationError(
            category="POLICY_DENIED",
            code="APPLICATION_POLICY_DENIED",
            message="denied",
        )


def test_handler_maps_valid_payload_to_success_http_response() -> None:
    response = GroundedAIHTTPHandler(
        application_service=SuccessService(),
    ).handle(
        {
            "request_id": "request-1",
            "query": "Question",
            "subjects": [
                "WORLD",
            ],
            "max_items": 3,
        }
    )

    assert response.status_code == 200
    assert response.body["status"] == "SUCCESS"
    assert response.body["request_id"] == "request-1"
    assert (
        response.body["data"]["trace"]["request_id"]
        == "request-1"
    )


def test_handler_maps_application_policy_denial_to_403() -> None:
    response = GroundedAIHTTPHandler(
        application_service=PolicyDeniedService(),
    ).handle(
        {
            "request_id": "request-1",
            "query": "Question",
        }
    )

    assert response.status_code == 403
    assert response.body == {
        "status": "ERROR",
        "request_id": "request-1",
        "error": {
            "category": "POLICY_DENIED",
            "code": "APPLICATION_POLICY_DENIED",
            "message": "denied",
        },
    }


def test_handler_maps_unknown_request_field_to_400() -> None:
    response = GroundedAIHTTPHandler(
        application_service=SuccessService(),
    ).handle(
        {
            "request_id": "request-1",
            "query": "Question",
            "unexpected": True,
        }
    )

    assert response.status_code == 400
    assert response.body["status"] == "ERROR"
    assert response.body["request_id"] == "request-1"
    assert response.body["error"]["category"] == "INVALID_REQUEST"
    assert response.body["error"]["code"] == "API_INVALID_REQUEST"


def test_handler_maps_missing_request_id_to_400_with_unknown_identity() -> None:
    response = GroundedAIHTTPHandler(
        application_service=SuccessService(),
    ).handle(
        {
            "query": "Question",
        }
    )

    assert response.status_code == 400
    assert response.body["request_id"] == "UNKNOWN"
    assert response.body["error"]["category"] == "INVALID_REQUEST"


def test_handler_maps_non_dictionary_payload_to_400() -> None:
    response = GroundedAIHTTPHandler(
        application_service=SuccessService(),
    ).handle(  # type: ignore[arg-type]
        ["not", "a", "dictionary"]
    )

    assert response.status_code == 400
    assert response.body["request_id"] == "UNKNOWN"
    assert response.body["error"]["code"] == "API_INVALID_REQUEST"


def test_handler_does_not_call_application_for_invalid_payload() -> None:
    class NeverCallService(
        GroundedAIApplicationService
    ):
        def execute(self, request):
            raise AssertionError(
                "application must not execute for invalid API payload"
            )

    response = GroundedAIHTTPHandler(
        application_service=NeverCallService(),
    ).handle(
        {
            "request_id": "request-1",
            "query": "",
        }
    )

    assert response.status_code == 400
