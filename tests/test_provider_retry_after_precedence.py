from decimal import Decimal

from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
    GroundedProviderRetryDelayService,
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


def policy():
    return GroundedProviderRetryDelayPolicy(
        initial_delay_seconds=Decimal("1"),
        multiplier=Decimal("2"),
        maximum_delay_seconds=Decimal("4"),
    )


def test_policy_delay_wins_when_provider_delay_is_shorter() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=2,
        provider_retry_after_seconds=Decimal("1.5"),
    )

    assert decision.policy_delay_seconds == Decimal("2")
    assert decision.provider_retry_after_seconds == Decimal("1.5")
    assert decision.effective_delay_seconds == Decimal("2")


def test_provider_delay_wins_when_longer_than_policy() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=2,
        provider_retry_after_seconds=Decimal("10"),
    )

    assert decision.policy_delay_seconds == Decimal("2")
    assert decision.effective_delay_seconds == Decimal("10")


def test_provider_delay_is_not_capped_by_local_policy_maximum() -> None:
    decision = GroundedProviderRetryDelayService().decide(
        policy=policy(),
        retry_number=5,
        provider_retry_after_seconds=Decimal("30"),
    )

    assert decision.policy_delay_seconds == Decimal("4")
    assert decision.effective_delay_seconds == Decimal("30")


class RecordingSleeper(GroundedProviderSleeper):
    def __init__(self):
        self.delays = []

    def sleep(self, *, delay_seconds):
        self.delays.append(delay_seconds)


class RetryAfterThenSuccessTransport(
    GroundedProviderTransport
):
    def __init__(self):
        self.calls = 0

    def send(self, request):
        self.calls += 1
        if self.calls == 1:
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message="rate limited",
                retryable=True,
                retry_after_seconds=Decimal("5"),
            )
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body="{}",
        )


def test_execution_uses_effective_provider_aware_delay() -> None:
    sleeper = RecordingSleeper()
    service = GroundedProviderExecutionService(
        transport=RetryAfterThenSuccessTransport(),
        retry_delay_policy=policy(),
        sleeper=sleeper,
    )

    result = service.execute(
        request=GroundedProviderTransportRequest(
            request_id="r1",
            method="POST",
            url="https://example.test",
            headers=(),
            body="{}",
            timeout_seconds=10,
        ),
        config=GroundedProviderConfig(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=1,
        ),
    )

    assert result.attempt_count == 2
    assert sleeper.delays == [
        Decimal("5")
    ]
