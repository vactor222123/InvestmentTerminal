"""Provider-neutral request and observed-usage budget guardrails."""

from dataclasses import dataclass
from decimal import Decimal

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import GroundedProviderCost


@dataclass(frozen=True, slots=True)
class GroundedProviderBudgetPolicy:
    """Explicit optional limits for one provider invocation."""

    max_output_tokens: int | None = None
    max_total_tokens: int | None = None
    max_total_cost: Decimal | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("max_output_tokens", "max_total_tokens"):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(
                    f"{field_name} must be a positive integer or None"
                )

        if self.max_total_cost is not None:
            if isinstance(self.max_total_cost, bool):
                raise TypeError(
                    "max_total_cost must be Decimal-compatible or None"
                )
            value = Decimal(str(self.max_total_cost))
            if not value.is_finite() or value < 0:
                raise ValueError(
                    "max_total_cost must be finite and non-negative"
                )
            object.__setattr__(self, "max_total_cost", value)
            if self.currency is None or not self.currency.strip():
                raise ValueError(
                    "currency is required when max_total_cost is configured"
                )
            object.__setattr__(self, "currency", self.currency.strip().upper())
        elif self.currency is not None:
            raise ValueError("currency requires max_total_cost")

    def require_request_allowed(
        self,
        *,
        requested_max_output_tokens: int | None,
    ) -> None:
        if requested_max_output_tokens is None:
            return
        if (
            isinstance(requested_max_output_tokens, bool)
            or not isinstance(requested_max_output_tokens, int)
            or requested_max_output_tokens <= 0
        ):
            raise ValueError(
                "requested_max_output_tokens must be a positive integer or None"
            )
        if (
            self.max_output_tokens is not None
            and requested_max_output_tokens > self.max_output_tokens
        ):
            raise PermissionError(
                "requested output token limit exceeds provider budget policy"
            )

    def require_observed_usage_allowed(
        self,
        *,
        usage: GroundedProviderUsage,
    ) -> None:
        if not isinstance(usage, GroundedProviderUsage):
            raise TypeError("usage must be a GroundedProviderUsage")
        if (
            self.max_output_tokens is not None
            and usage.output_tokens > self.max_output_tokens
        ):
            raise PermissionError(
                "observed output token usage exceeds provider budget policy"
            )
        if (
            self.max_total_tokens is not None
            and usage.total_tokens > self.max_total_tokens
        ):
            raise PermissionError(
                "observed total token usage exceeds provider budget policy"
            )

    def require_observed_cost_allowed(
        self,
        *,
        cost: GroundedProviderCost,
    ) -> None:
        if not isinstance(cost, GroundedProviderCost):
            raise TypeError("cost must be a GroundedProviderCost")
        if self.max_total_cost is None:
            return
        assert self.currency is not None
        if cost.currency != self.currency:
            raise PermissionError(
                "provider cost currency does not match budget policy currency"
            )
        if cost.total_cost > self.max_total_cost:
            raise PermissionError(
                "observed provider cost exceeds budget policy"
            )
