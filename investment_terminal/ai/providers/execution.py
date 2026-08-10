"""
Bounded provider transport execution with deterministic retry semantics.

max_retries means retries after the initial attempt. This module performs no
sleep, backoff, jitter, rate-limit interpretation, or provider-specific logic.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.ai.providers.contracts import GroundedProviderConfig
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

    def __post_init__(self) -> None:
        if not isinstance(self.response, GroundedProviderTransportResponse):
            raise TypeError(
                "response must be a GroundedProviderTransportResponse"
            )
        for field_name in ("attempt_count", "retry_count"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )
        if self.attempt_count < 1:
            raise ValueError("attempt_count must be at least 1")
        if self.retry_count != self.attempt_count - 1:
            raise ValueError(
                "retry_count must equal attempt_count - 1"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "response": self.response.to_dict(),
            "attempt_count": self.attempt_count,
            "retry_count": self.retry_count,
        }


class GroundedProviderExecutionService:
    def __init__(self, *, transport: GroundedProviderTransport) -> None:
        if not isinstance(transport, GroundedProviderTransport):
            raise TypeError(
                "transport must be a GroundedProviderTransport"
            )
        self._transport = transport

    def execute(
        self,
        *,
        request: GroundedProviderTransportRequest,
        config: GroundedProviderConfig,
    ) -> GroundedProviderExecutionResult:
        if not isinstance(request, GroundedProviderTransportRequest):
            raise TypeError(
                "request must be a GroundedProviderTransportRequest"
            )
        if not isinstance(config, GroundedProviderConfig):
            raise TypeError(
                "config must be a GroundedProviderConfig"
            )
        if request.timeout_seconds != config.timeout_seconds:
            raise ValueError(
                "request timeout_seconds must match provider config"
            )

        maximum_attempts = 1 + config.max_retries

        for attempt_number in range(1, maximum_attempts + 1):
            try:
                response = self._transport.send(request)
            except GroundedProviderTransportFailure as exc:
                if (
                    not exc.retryable
                    or attempt_number >= maximum_attempts
                ):
                    raise
                continue

            return GroundedProviderExecutionResult(
                response=response,
                attempt_count=attempt_number,
                retry_count=attempt_number - 1,
            )

        raise RuntimeError(
            "provider execution exhausted without response or failure"
        )
