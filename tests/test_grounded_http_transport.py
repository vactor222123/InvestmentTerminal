import io
import socket
from email.message import Message
from urllib import error

import pytest

from investment_terminal.ai.providers.http_transport import (
    UrllibGroundedProviderTransport,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransportFailure,
    GroundedProviderTransportRequest,
)


def request():
    return GroundedProviderTransportRequest(
        request_id="request-1",
        method="POST",
        url="https://provider.invalid/v1/generate",
        headers=(
            (
                "Content-Type",
                "application/json",
            ),
        ),
        body='{"input":"test"}',
        timeout_seconds=12,
    )


class FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        body: str,
        headers=None,
    ):
        self.status = status
        self._body = body.encode("utf-8")
        self.headers = (
            headers
            if headers is not None
            else Message()
        )

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_successful_http_response_is_mapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = Message()
    headers["Content-Type"] = "application/json"

    def fake_urlopen(req, timeout):
        assert timeout == 12.0
        assert req.get_method() == "POST"
        return FakeResponse(
            status=200,
            body='{"output":"ok"}',
            headers=headers,
        )

    monkeypatch.setattr(
        "investment_terminal.ai.providers.http_transport."
        "urllib_request.urlopen",
        fake_urlopen,
    )

    response = UrllibGroundedProviderTransport().send(
        request()
    )

    assert response.request_id == "request-1"
    assert response.status_code == 200
    assert response.body == '{"output":"ok"}'


@pytest.mark.parametrize(
    "status_code",
    [
        408,
        425,
        429,
        500,
        503,
        599,
    ],
)
def test_retryable_http_statuses_are_classified(
    status_code: int,
) -> None:
    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as exc:
        UrllibGroundedProviderTransport._raise_for_http_status(
            status_code=status_code,
            body="temporary",
        )

    assert exc.value.kind == "RETRYABLE"
    assert exc.value.retryable is True


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        403,
        404,
        409,
        422,
    ],
)
def test_terminal_http_statuses_are_classified(
    status_code: int,
) -> None:
    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as exc:
        UrllibGroundedProviderTransport._raise_for_http_status(
            status_code=status_code,
            body="bad request",
        )

    assert exc.value.kind == "TERMINAL"
    assert exc.value.retryable is False


def test_socket_timeout_maps_to_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(req, timeout):
        raise socket.timeout()

    monkeypatch.setattr(
        "investment_terminal.ai.providers.http_transport."
        "urllib_request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as exc:
        UrllibGroundedProviderTransport().send(
            request()
        )

    assert exc.value.kind == "TIMEOUT"
    assert exc.value.retryable is True


def test_url_error_maps_to_retryable_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(req, timeout):
        raise error.URLError(
            "connection refused"
        )

    monkeypatch.setattr(
        "investment_terminal.ai.providers.http_transport."
        "urllib_request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as exc:
        UrllibGroundedProviderTransport().send(
            request()
        )

    assert exc.value.kind == "RETRYABLE"
    assert exc.value.retryable is True


def test_http_error_body_is_not_silently_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(req, timeout):
        raise error.HTTPError(
            req.full_url,
            401,
            "unauthorized",
            Message(),
            io.BytesIO(
                b'{"error":"unauthorized"}'
            ),
        )

    monkeypatch.setattr(
        "investment_terminal.ai.providers.http_transport."
        "urllib_request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(
        GroundedProviderTransportFailure,
    ) as exc:
        UrllibGroundedProviderTransport().send(
            request()
        )

    assert exc.value.kind == "TERMINAL"
    assert "401" in exc.value.message


def test_transport_rejects_wrong_request_type() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedProviderTransportRequest",
    ):
        UrllibGroundedProviderTransport().send(
            object()  # type: ignore[arg-type]
        )


def test_module_imports_no_provider_sdk() -> None:
    import investment_terminal.ai.providers.http_transport as module

    names = {
        name.lower()
        for name in module.__dict__
    }

    for forbidden in (
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "aiohttp",
    ):
        assert forbidden not in names
