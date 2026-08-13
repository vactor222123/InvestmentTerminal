from investment_terminal.server.openapi_contract import (
    grounded_ai_openapi_extra,
)


def test_openapi_documents_rate_limit_response_and_retry_after() -> None:
    responses = grounded_ai_openapi_extra()["responses"]

    assert "429" in responses
    assert responses["429"]["description"] == (
        "Inbound request rate limit exceeded"
    )
    assert (
        responses["429"]["headers"]["Retry-After"]["schema"]["minimum"]
        == 1
    )
