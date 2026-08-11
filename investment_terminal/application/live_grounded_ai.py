"""
Concrete grounded AI application use case.

This service owns application orchestration over Knowledge query, grounded
generation, optional usage/cost guardrails, and safe trace projection.
It owns no CLI parsing, HTTP framework integration, provider composition,
credential lookup, or database construction.
"""

from decimal import Decimal
from typing import Any

from investment_terminal.ai.audit import (
    GroundedGenerationTraceService,
)
from investment_terminal.ai.context_selection import (
    GroundedContextSelectionPolicy,
)
from investment_terminal.ai.providers.cost_audit import (
    GroundedProviderCostTraceService,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.ai.providers.pricing import (
    GroundedProviderCost,
    GroundedProviderPricingPolicy,
)
from investment_terminal.application.errors import (
    GroundedAIApplicationError,
    map_application_failure,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)


def _require_callable(
    dependency: Any,
    *,
    method_name: str,
    dependency_name: str,
) -> None:
    method = getattr(
        dependency,
        method_name,
        None,
    )
    if not callable(method):
        raise TypeError(
            f"{dependency_name} must provide callable {method_name}()"
        )


class LiveGroundedAIApplicationService(
    GroundedAIApplicationService
):
    """Concrete read-only grounded AI application service."""

    def __init__(
        self,
        *,
        query: Any,
        generation_service: Any,
        pricing_policy: GroundedProviderPricingPolicy | None = None,
        budget_policy: GroundedProviderBudgetPolicy | None = None,
        requested_max_output_tokens: int | None = None,
    ) -> None:
        _require_callable(
            query,
            method_name="list_all",
            dependency_name="query",
        )
        _require_callable(
            generation_service,
            method_name="generate",
            dependency_name="generation_service",
        )

        if (
            pricing_policy is not None
            and not isinstance(
                pricing_policy,
                GroundedProviderPricingPolicy,
            )
        ):
            raise TypeError(
                "pricing_policy must be a "
                "GroundedProviderPricingPolicy or None"
            )
        if (
            budget_policy is not None
            and not isinstance(
                budget_policy,
                GroundedProviderBudgetPolicy,
            )
        ):
            raise TypeError(
                "budget_policy must be a "
                "GroundedProviderBudgetPolicy or None"
            )
        if (
            requested_max_output_tokens is not None
            and (
                isinstance(
                    requested_max_output_tokens,
                    bool,
                )
                or not isinstance(
                    requested_max_output_tokens,
                    int,
                )
                or requested_max_output_tokens <= 0
            )
        ):
            raise ValueError(
                "requested_max_output_tokens must be "
                "a positive integer or None"
            )
        if (
            budget_policy is not None
            and budget_policy.max_total_cost is not None
            and pricing_policy is None
        ):
            raise ValueError(
                "cost budget requires explicit pricing policy"
            )

        self._query = query
        self._generation_service = generation_service
        self._pricing_policy = pricing_policy
        self._budget_policy = budget_policy
        self._requested_max_output_tokens = (
            requested_max_output_tokens
        )

    def execute(
        self,
        request: GroundedAIApplicationRequest,
    ) -> GroundedAIApplicationResult:
        try:
            return self._execute(
                request
            )
        except GroundedAIApplicationError:
            raise
        except Exception as exc:
            mapped = map_application_failure(
                exc
            )
            raise mapped from exc

    def _execute(
        self,
        request: GroundedAIApplicationRequest,
    ) -> GroundedAIApplicationResult:
        if not isinstance(
            request,
            GroundedAIApplicationRequest,
        ):
            raise TypeError(
                "request must be a GroundedAIApplicationRequest"
            )

        if self._budget_policy is not None:
            self._budget_policy.require_request_allowed(
                requested_max_output_tokens=(
                    self._requested_max_output_tokens
                )
            )

        knowledge = self._query.list_all()

        generation = self._generation_service.generate(
            request_id=request.request_id,
            user_query=request.user_query,
            knowledge=knowledge,
            policy=GroundedContextSelectionPolicy(
                subject_keys=request.subject_keys,
                max_items=request.max_items,
            ),
        )

        if (
            self._budget_policy is not None
            and generation.response.usage is not None
        ):
            self._budget_policy.require_observed_usage_allowed(
                usage=generation.response.usage
            )

        trace = GroundedGenerationTraceService().build(
            generation
        )
        trace_data = trace.to_dict()

        if self._pricing_policy is not None:
            trace_data = (
                GroundedProviderCostTraceService().build(
                    trace=trace,
                    pricing_policy=self._pricing_policy,
                )
            )

            if (
                self._budget_policy is not None
                and self._budget_policy.max_total_cost is not None
            ):
                provider_cost = trace_data.get(
                    "provider_cost"
                )
                if provider_cost is None:
                    raise RuntimeError(
                        "provider cost is unavailable "
                        "for configured cost budget"
                    )
                self._budget_policy.require_observed_cost_allowed(
                    cost=GroundedProviderCost(
                        provider_identity=provider_cost[
                            "provider_identity"
                        ],
                        model_identity=provider_cost[
                            "model_identity"
                        ],
                        currency=provider_cost["currency"],
                        input_cost=Decimal(
                            provider_cost["input_cost"]
                        ),
                        output_cost=Decimal(
                            provider_cost["output_cost"]
                        ),
                        total_cost=Decimal(
                            provider_cost["total_cost"]
                        ),
                    )
                )

        return GroundedAIApplicationResult(
            generation=generation.to_dict(),
            trace=trace_data,
        )
