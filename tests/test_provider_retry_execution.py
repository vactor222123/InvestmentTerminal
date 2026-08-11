from decimal import Decimal

import pytest

from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
)
from investment_terminal.ai.providers.sleeper import (
    GroundedProviderSleeper,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportRequest,
    GroundedProviderTransportResponse,
)


def request():
    return GroundedProviderTransportRequest(
        request_id="r1",
        method="POST",
        url="https://example.test",
        headers=(),
        body="{}",
        timeout_seconds=10,
    )


def config(max_retries=3):
    return GroundedProviderConfig(
        provider_identity="OPENAI",
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=max_retries,
    )


def delay_policy():
    return GroundedProviderRetryDelayPolicy(
        initial_delay_seconds=Decimal("0.5"),
        multiplier=Decimal("2"),
        maximum_delay_seconds=Decimal("4"),
    )


class RecordingSleeper(GroundedProviderSleeper):
    def __init__(self):
        self.delays = []

    def sleep(self, *, delay_seconds):
        self.delays.append(delay_seconds)


class FailTwiceThenSucceedTransport(
    GroundedProviderTransport
):
    def __init__(self):
        self.calls = 0

    def send(self, request):
        self.calls += 1
        if self.calls <= 2:
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message="temporary",
                retryable=True,
            )
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body="{}",
        )


class TerminalTransport(
    GroundedProviderTransport
):
    def send(self, request):
        raise GroundedProviderTransportFailure(
            kind="TERMINAL",
            message="terminal",
            retryable=False,
        )


class AlwaysRetryableTransport(
    GroundedProviderTransport
):
    def __init__(self):
        self.calls = 0

    def send(self, request):
        self.calls += 1
        raise GroundedProviderTransportFailure(
            kind="RETRYABLE",
            message="temporary",
            retryable=True,
        )


def test_retryable_failures_sleep_between_attempts() -> None:
    transport = FailTwiceThenSucceedTransport()
    sleeper = RecordingSleeper()
    service = GroundedProviderExecutionService(
        transport=transport,
        retry_delay_policy=delay_policy(),
        sleeper=sleeper,
    )

    result = service.execute(
        request=request(),
        config=config(),
    )

    assert result.attempt_count == 3
    assert result.retry_count == 2
    assert transport.calls == 3
    assert sleeper.delays == [
        Decimal("0.5"),
        Decimal("1.0"),
    ]


def test_terminal_failure_never_sleeps() -> None:
    sleeper = RecordingSleeper()
    service = GroundedProviderExecutionService(
        transport=TerminalTransport(),
        retry_delay_policy=delay_policy(),
        sleeper=sleeper,
    )

    with pytest.raises(
        GroundedProviderTransportFailure,
    ):
        service.execute(
            request=request(),
            config=config(),
        )

    assert sleeper.delays == []


def test_retry_exhaustion_does_not_sleep_after_last_attempt() -> None:
    sleeper = RecordingSleeper()
    transport = AlwaysRetryableTransport()
    service = GroundedProviderExecutionService(
        transport=transport,
        retry_delay_policy=delay_policy(),
        sleeper=sleeper,
    )

    with pytest.raises(
        GroundedProviderTransportFailure,
    ):
        service.execute(
            request=request(),
            config=config(max_retries=2),
        )

    assert transport.calls == 3
    assert sleeper.delays == [
        Decimal("0.5"),
        Decimal("1.0"),
    ]


def test_existing_execution_path_remains_zero_delay_by_default() -> None:
    transport = FailTwiceThenSucceedTransport()
    service = GroundedProviderExecutionService(
        transport=transport
    )

    result = service.execute(
        request=request(),
        config=config(),
    )

    assert result.attempt_count == 3


def test_policy_and_sleeper_must_be_configured_together() -> None:
    with pytest.raises(
        ValueError,
        match="configured together",
    ):
        GroundedProviderExecutionService(
            transport=FailTwiceThenSucceedTransport(),
            retry_delay_policy=delay_policy(),
        )

    with pytest.raises(
        ValueError,
        match="configured together",
    ):
        GroundedProviderExecutionService(
            transport=FailTwiceThenSucceedTransport(),
            sleeper=RecordingSleeper(),
        )
