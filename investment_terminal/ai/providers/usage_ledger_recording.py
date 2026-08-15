"""
Recording service for durable provider usage/cost accounting.

The service translates already-observed provider usage plus already-estimated
cost into one immutable ledger record. It performs no provider call, pricing
lookup, budget decision, or persistence-specific operation.
"""

from datetime import datetime

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import GroundedProviderCost
from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    GroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.utils.validation import normalize_required_text


class GroundedProviderUsageCostLedgerRecordingService:
    """Record one successful provider usage/cost observation."""

    def __init__(
        self,
        *,
        repository: GroundedProviderUsageCostLedgerRepository,
    ) -> None:
        if not isinstance(
            repository,
            GroundedProviderUsageCostLedgerRepository,
        ):
            raise TypeError(
                "repository must be a "
                "GroundedProviderUsageCostLedgerRepository"
            )
        self._repository = repository

    def record(
        self,
        *,
        request_id: str,
        usage: GroundedProviderUsage,
        cost: GroundedProviderCost,
        recorded_at: datetime,
    ) -> GroundedProviderUsageCostLedgerRecord:
        normalized_request_id = normalize_required_text(
            request_id,
            field_name="request_id",
        )
        if not isinstance(
            usage,
            GroundedProviderUsage,
        ):
            raise TypeError(
                "usage must be a GroundedProviderUsage"
            )
        if not isinstance(
            cost,
            GroundedProviderCost,
        ):
            raise TypeError(
                "cost must be a GroundedProviderCost"
            )

        record = GroundedProviderUsageCostLedgerRecord(
            request_id=normalized_request_id,
            provider_identity=cost.provider_identity,
            model_identity=cost.model_identity,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            currency=cost.currency,
            input_cost=cost.input_cost,
            output_cost=cost.output_cost,
            total_cost=cost.total_cost,
            recorded_at=recorded_at,
        )
        return self._repository.add(record)
