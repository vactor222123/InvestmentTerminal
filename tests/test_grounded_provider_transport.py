import pytest

from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportRequest,
    GroundedProviderTransportResponse,
    StaticGroundedProviderTransport,
)


def request():
    return GroundedProviderTransportRequest(
        request_id="request-1",
        method="post",
        url="https://provider.invalid/v1/generate",
        headers=(
            (
                "Content-Type",
                "application/json",
            ),
        ),
        body='{"input":"test"}',
        timeout_seconds=30,
    )


def response():
    return GroundedProviderTransportResponse(
        request_id="request-1",
        status_code=200,
        headers=(
            (
                "Content-Type",
                "application/json",
            ),
        ),
        body='{"output":"ok"}',
    )


def test_request_normalizes_method_and_serializes() -> None:
    item = request()

    assert item.method == "POST"
    assert item.timeout_seconds == 30.0
    assert item.to_dict()["request_id"] == "request-1"


def test_duplicate_headers_are_rejected_case_insensitively() -> None:
    with pytest.raises(
        ValueError,
        match="unique case-insensitively",
    ):
        GroundedProviderTransportRequest(
            request_id="request-1",
            method="POST",
            url="https://provider.invalid",
            headers=(
                ("Authorization", "one"),
                ("authorization", "two"),
            ),
            body="{}",
            timeout_seconds=10,
        )


def test_failure_retryability_is_derived_from_kind_contract() -> None:
    timeout = GroundedProviderTransportFailure(
        kind="TIMEOUT",
        message="timed out",
        retryable=True,
    )
    retryable = GroundedProviderTransportFailure(
        kind="RETRYABLE",
        message="temporary",
        retryable=True,
    )
    terminal = GroundedProviderTransportFailure(
        kind="TERMINAL",
        message="bad request",
        retryable=False,
    )

    assert timeout.retryable is True
    assert retryable.retryable is True
    assert terminal.retryable is False


def test_inconsistent_failure_retryable_flag_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="retryable flag",
    ):
        GroundedProviderTransportFailure(
            kind="TERMINAL",
            message="bad request",
            retryable=True,
        )


def test_static_transport_returns_matching_response() -> None:
    transport = StaticGroundedProviderTransport(
        response=response(),
    )

    result = transport.send(
        request()
    )

    assert result.status_code == 200
    assert result.body == '{"output":"ok"}'


def test_static_transport_raises_typed_failure() -> None:
    failure = GroundedProviderTransportFailure(
        kind="TIMEOUT",
        message="timed out",
        retryable=True,
    )
    transport = StaticGroundedProviderTransport(
        failure=failure,
    )

    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as exc:
        transport.send(
            request()
        )

    assert exc.value.kind == "TIMEOUT"
    assert exc.value.retryable is True


def test_response_request_correlation_is_enforced() -> None:
    transport = StaticGroundedProviderTransport(
        response=GroundedProviderTransportResponse(
            request_id="other",
            status_code=200,
            headers=(),
            body="ok",
        )
    )

    with pytest.raises(
        ValueError,
        match="request_id must match",
    ):
        transport.send(
            request()
        )


def test_transport_is_abstract_boundary() -> None:
    with pytest.raises(
        TypeError,
    ):
        GroundedProviderTransport()  # type: ignore[abstract]


def test_module_imports_no_network_client() -> None:
    import investment_terminal.ai.providers.transport as module

    names = {
        name.lower()
        for name in module.__dict__
    }

    forbidden = (
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
        "openai",
        "anthropic",
    )

    assert not any(
        item in names
        for item in forbidden
    )
