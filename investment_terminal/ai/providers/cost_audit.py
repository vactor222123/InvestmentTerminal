"""
Safe cost-audit projection from canonical provider usage and explicit pricing.

This layer derives estimated cost without changing the base generation trace,
provider adapter, or grounding semantics.
"""

from typing import Any

from investment_terminal.ai.audit import GroundedGenerationTrace
from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import (
    GroundedProviderPricingPolicy,
)


class GroundedProviderCostTraceService:
    """Attach deterministic estimated cost to an existing trace dictionary."""

    def build(
        self,
        *,
        trace: GroundedGenerationTrace,
        pricing_policy: GroundedProviderPricingPolicy,
    ) -> dict[str, Any]:
        if not isinstance(trace, GroundedGenerationTrace):
            raise TypeError(
                "trace must be a GroundedGenerationTrace"
            )
        if not isinstance(
            pricing_policy,
            GroundedProviderPricingPolicy,
        ):
            raise TypeError(
                "pricing_policy must be a GroundedProviderPricingPolicy"
            )

        data = trace.to_dict()

        if trace.provider_input_tokens is None:
            return data

        assert trace.provider_output_tokens is not None
        assert trace.provider_total_tokens is not None

        usage = GroundedProviderUsage(
            input_tokens=trace.provider_input_tokens,
            output_tokens=trace.provider_output_tokens,
            total_tokens=trace.provider_total_tokens,
        )
        cost = pricing_policy.estimate_cost(
            provider_identity=trace.provider_identity,
            model_identity=trace.model_identity,
            usage=usage,
        )
        data["provider_cost"] = cost.to_dict()
        return data
