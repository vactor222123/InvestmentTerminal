import pytest

from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)


def generation(
    request_id: str = "request-1",
):
    return {
        "prompt": {
            "request_id": request_id,
        },
        "answer": {
            "claims": [],
        },
    }


def trace(
    request_id: str = "request-1",
):
    return {
        "request_id": request_id,
        "validation_status": "ADMISSIBLE",
    }


def test_application_request_is_provider_neutral() -> None:
    request = GroundedAIApplicationRequest(
        request_id="request-1",
        user_query="Question",
        subject_keys=(
            "WORLD",
            "PORTFOLIO",
        ),
        max_items=5,
    )

    assert request.to_dict() == {
        "request_id": "request-1",
        "user_query": "Question",
        "subject_keys": [
            "WORLD",
            "PORTFOLIO",
        ],
        "max_items": 5,
    }


def test_application_request_rejects_duplicate_subjects() -> None:
    with pytest.raises(
        ValueError,
        match="unique",
    ):
        GroundedAIApplicationRequest(
            request_id="request-1",
            user_query="Question",
            subject_keys=(
                "WORLD",
                "WORLD",
            ),
        )


def test_application_request_rejects_invalid_max_items() -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        GroundedAIApplicationRequest(
            request_id="request-1",
            user_query="Question",
            max_items=0,
        )


def test_application_result_preserves_safe_generation_and_trace() -> None:
    result = GroundedAIApplicationResult(
        generation=generation(),
        trace=trace(),
    )

    assert result.request_id == "request-1"
    assert result.to_dict() == {
        "generation": generation(),
        "trace": trace(),
    }


def test_application_result_rejects_request_identity_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="request_id must match",
    ):
        GroundedAIApplicationResult(
            generation=generation(
                "request-1"
            ),
            trace=trace(
                "request-2"
            ),
        )


def test_application_service_is_abstract_boundary() -> None:
    with pytest.raises(TypeError):
        GroundedAIApplicationService()
