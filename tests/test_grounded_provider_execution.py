import pytest

from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportRequest,
    GroundedProviderTransportResponse,
)


def config(*, max_retries: int) -> GroundedProviderConfig:
    return GroundedProviderConfig(
        provider_identity="TEST",
        model_identity="TEST_MODEL@1",
        timeout_seconds=30,
        max_retries=max_retries,
    )


def request() -> GroundedProviderTransportRequest:
    return GroundedProviderTransportRequest(
        request_id="request-1",
        method="POST",
        url="https://provider.invalid",
        headers=(),
        body="{}",
        timeout_seconds=30,
    )


def response() -> GroundedProviderTransportResponse:
    return GroundedProviderTransportResponse(
        request_id="request-1",
        status_code=200,
        headers=(),
        body='{"ok":true}',
    )


class SequenceTransport(GroundedProviderTransport):
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def send(self, request):
        self.calls += 1
        outcome = self.outcomes[self.calls - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def retryable(kind="RETRYABLE"):
    return GroundedProviderTransportFailure(
        kind=kind,
        message="temporary failure",
        retryable=True,
    )


def terminal():
    return GroundedProviderTransportFailure(
        kind="TERMINAL",
        message="terminal failure",
        retryable=False,
    )


def test_success_on_first_attempt_has_zero_retries() -> None:
    transport = SequenceTransport([response()])
    result = GroundedProviderExecutionService(
        transport=transport
    ).execute(
        request=request(),
        config=config(max_retries=3),
    )
    assert result.attempt_count == 1
    assert result.retry_count == 0
    assert transport.calls == 1


def test_retryable_failure_then_success_retries() -> None:
    transport = SequenceTransport([retryable(), response()])
    result = GroundedProviderExecutionService(
        transport=transport
    ).execute(
        request=request(),
        config=config(max_retries=2),
    )
    assert result.attempt_count == 2
    assert result.retry_count == 1
    assert transport.calls == 2


def test_timeout_is_retryable() -> None:
    transport = SequenceTransport([retryable("TIMEOUT"), response()])
    result = GroundedProviderExecutionService(
        transport=transport
    ).execute(
        request=request(),
        config=config(max_retries=1),
    )
    assert result.attempt_count == 2


def test_terminal_failure_stops_immediately() -> None:
    transport = SequenceTransport([terminal(), response()])
    with pytest.raises(GroundedProviderTransportFailure) as exc:
        GroundedProviderExecutionService(
            transport=transport
        ).execute(
            request=request(),
            config=config(max_retries=5),
        )
    assert exc.value.kind == "TERMINAL"
    assert transport.calls == 1


def test_retry_budget_is_bounded() -> None:
    transport = SequenceTransport(
        [retryable(), retryable(), retryable()]
    )
    with pytest.raises(GroundedProviderTransportFailure):
        GroundedProviderExecutionService(
            transport=transport
        ).execute(
            request=request(),
            config=config(max_retries=2),
        )
    assert transport.calls == 3


def test_zero_retries_means_one_attempt_total() -> None:
    transport = SequenceTransport([retryable()])
    with pytest.raises(GroundedProviderTransportFailure):
        GroundedProviderExecutionService(
            transport=transport
        ).execute(
            request=request(),
            config=config(max_retries=0),
        )
    assert transport.calls == 1


def test_request_timeout_must_match_config() -> None:
    bad_request = GroundedProviderTransportRequest(
        request_id="request-1",
        method="POST",
        url="https://provider.invalid",
        headers=(),
        body="{}",
        timeout_seconds=10,
    )
    with pytest.raises(
        ValueError,
        match="must match provider config",
    ):
        GroundedProviderExecutionService(
            transport=SequenceTransport([response()])
        ).execute(
            request=bad_request,
            config=config(max_retries=0),
        )


def test_execution_service_contains_no_sleep_or_backoff_policy() -> None:
    import investment_terminal.ai.providers.execution as module
    names = {name.lower() for name in module.__dict__}
    for forbidden in ("sleep", "backoff", "jitter", "random", "time"):
        assert forbidden not in names
