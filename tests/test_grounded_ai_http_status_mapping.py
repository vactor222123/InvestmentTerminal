from investment_terminal.api.grounded_ai import (
    GroundedAIAPIResponse,
)
from investment_terminal.api.http_mapping import (
    GroundedAIHTTPResponse,
    GroundedAIHTTPStatusMapper,
)


def error_response(
    category: str,
) -> GroundedAIAPIResponse:
    return GroundedAIAPIResponse(
        status="ERROR",
        request_id="request-1",
        error={
            "category": category,
            "code": "CODE",
            "message": "message",
        },
    )


def test_success_maps_to_200() -> None:
    mapped = GroundedAIHTTPStatusMapper().map(
        GroundedAIAPIResponse(
            status="SUCCESS",
            request_id="request-1",
            data={
                "generation": {},
                "trace": {},
            },
        )
    )

    assert mapped.status_code == 200
    assert mapped.body["status"] == "SUCCESS"


def test_invalid_request_maps_to_400() -> None:
    assert (
        GroundedAIHTTPStatusMapper().map(
            error_response(
                "INVALID_REQUEST"
            )
        ).status_code
        == 400
    )


def test_policy_denied_maps_to_403() -> None:
    assert (
        GroundedAIHTTPStatusMapper().map(
            error_response(
                "POLICY_DENIED"
            )
        ).status_code
        == 403
    )


def test_execution_failed_maps_to_503() -> None:
    assert (
        GroundedAIHTTPStatusMapper().map(
            error_response(
                "EXECUTION_FAILED"
            )
        ).status_code
        == 503
    )


def test_internal_error_maps_to_500() -> None:
    assert (
        GroundedAIHTTPStatusMapper().map(
            error_response(
                "INTERNAL_ERROR"
            )
        ).status_code
        == 500
    )


def test_unknown_error_category_fails_closed_to_500() -> None:
    assert (
        GroundedAIHTTPStatusMapper().map(
            error_response(
                "SOMETHING_NEW"
            )
        ).status_code
        == 500
    )


def test_http_wrapper_preserves_api_body_exactly() -> None:
    response = error_response(
        "POLICY_DENIED"
    )

    mapped = GroundedAIHTTPStatusMapper().map(
        response
    )

    assert mapped.to_dict() == {
        "status_code": 403,
        "body": response.to_dict(),
    }


def test_http_response_validates_status_code() -> None:
    try:
        GroundedAIHTTPResponse(
            status_code=99,
            body={},
        )
    except ValueError as exc:
        assert "HTTP status code" in str(
            exc
        )
    else:
        raise AssertionError(
            "invalid HTTP status code must fail"
        )
