"""Bounded provider transport execution with deterministic retry delays."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from investment_terminal.ai.providers.contracts import GroundedProviderConfig
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


@dataclass(frozen=True, slots=True)
class GroundedProviderExecutionResult:
    response: GroundedProviderTransportResponse
    attempt_count: int
    retry_count: int
    retry_delay_seconds: tuple[Decimal, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.response,
            GroundedProviderTransportResponse,
        ):
            raise TypeError(
                "response must be a GroundedProviderTransportResponse"
            )
        for field_name in (
            "attempt_count",
            "retry_count",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )
        if self.attempt_count < 1:
            raise ValueError(
                "attempt_count must be at least 1"
            )
        if self.retry_count != self.attempt_count - 1:
            raise ValueError(
                "retry_count must equal attempt_count - 1"
            )
        if not isinstance(
            self.retry_delay_seconds,
            tuple,
        ):
            raise TypeError(
                "retry_delay_seconds must be a tuple"
            )
        if len(self.retry_delay_seconds) > self.retry_count:
            raise ValueError(
                "retry delay count cannot exceed retry_count"
            )

        normalized = []
        for value in self.retry_delay_seconds:
            if isinstance(value, bool):
                raise TypeError(
                    "retry delays must be Decimal-compatible"
                )
            try:
                parsed = Decimal(str(value))
            except Exception as exc:
                raise TypeError(
                    "retry delays must be Decimal-compatible"
                ) from exc
            if not parsed.is_finite() or parsed < 0:
                raise ValueError(
                    "retry delays must be finite and non-negative"
                )
            normalized.append(parsed)

        object.__setattr__(
            self,
            "retry_delay_seconds",
            tuple(normalized),
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "response": self.response.to_dict(),
            "attempt_count": self.attempt_count,
            "retry_count": self.retry_count,
        }
        if self.retry_delay_seconds:
            data["retry_delay_seconds"] = [
                str(value)
                for value in self.retry_delay_seconds
            ]
        return data


class GroundedProviderExecutionService:
    def __init__(
        self,
        *,
        transport: GroundedProviderTransport,
        retry_delay_policy: (
            GroundedProviderRetryDelayPolicy | None
        ) = None,
        sleeper: GroundedProviderSleeper | None = None,
    ) -> None:
        if not isinstance(
            transport,
            GroundedProviderTransport,
        ):
            raise TypeError(
                "transport must be a GroundedProviderTransport"
            )

        if (
            retry_delay_policy is None
        ) != (
            sleeper is None
        ):
            raise ValueError(
                "retry_delay_policy and sleeper must be configured together"
            )

        if (
            retry_delay_policy is not None
            and not isinstance(
                retry_delay_policy,
                GroundedProviderRetryDelayPolicy,
            )
        ):
            raise TypeError(
                "retry_delay_policy must be a "
                "GroundedProviderRetryDelayPolicy or None"
            )

        if (
            sleeper is not None
            and not isinstance(
                sleeper,
                GroundedProviderSleeper,
            )
        ):
            raise TypeError(
                "sleeper must be a GroundedProviderSleeper or None"
            )

        self._transport = transport
        self._retry_delay_policy = retry_delay_policy
        self._sleeper = sleeper
        self._retry_delay_service = (
            GroundedProviderRetryDelayService()
        )

    def execute(
        self,
        *,
        request: GroundedProviderTransportRequest,
        config: GroundedProviderConfig,
    ) -> GroundedProviderExecutionResult:
        if not isinstance(
            request,
            GroundedProviderTransportRequest,
        ):
            raise TypeError(
                "request must be a GroundedProviderTransportRequest"
            )
        if not isinstance(
            config,
            GroundedProviderConfig,
        ):
            raise TypeError(
                "config must be a GroundedProviderConfig"
            )
        if (
            request.timeout_seconds
            != config.timeout_seconds
        ):
            raise ValueError(
                "request timeout_seconds must match provider config"
            )

        maximum_attempts = 1 + config.max_retries
        applied_retry_delays: list[Decimal] = []

        for attempt_number in range(
            1,
            maximum_attempts + 1,
        ):
            try:
                response = self._transport.send(
                    request
                )
            except GroundedProviderTransportFailure as exc:
                if (
                    not exc.retryable
                    or attempt_number >= maximum_attempts
                ):
                    raise

                delay = self._apply_retry_delay(
                    retry_number=attempt_number,
                    provider_retry_after_seconds=(
                        exc.retry_after_seconds
                    ),
                )
                if delay is not None:
                    applied_retry_delays.append(
                        delay
                    )
                continue

            return GroundedProviderExecutionResult(
                response=response,
                attempt_count=attempt_number,
                retry_count=attempt_number - 1,
                retry_delay_seconds=tuple(
                    applied_retry_delays
                ),
            )

        raise RuntimeError(
            "provider execution exhausted without response or failure"
        )

    def _apply_retry_delay(
        self,
        *,
        retry_number: int,
        provider_retry_after_seconds=None,
    ) -> Decimal | None:
        if self._retry_delay_policy is None:
            return None

        assert self._sleeper is not None

        decision = (
            self._retry_delay_service.decide(
                policy=self._retry_delay_policy,
                retry_number=retry_number,
                provider_retry_after_seconds=(
                    provider_retry_after_seconds
                ),
            )
        )
        self._sleeper.sleep(
            delay_seconds=(
                decision.effective_delay_seconds
            )
        )
        return decision.effective_delay_seconds
