"""Application decorator for durable provider usage/cost recording."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import GroundedProviderCost
from investment_terminal.ai.providers.usage_ledger_recording import (
    GroundedProviderUsageCostLedgerRecordingService,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)


class UsageCostRecordingGroundedAIApplicationService(
    GroundedAIApplicationService
):
    """Record successful priced provider usage after application execution."""

    def __init__(self, *, application_service: GroundedAIApplicationService, recording_service: GroundedProviderUsageCostLedgerRecordingService) -> None:
        if not isinstance(application_service, GroundedAIApplicationService):
            raise TypeError("application_service must be a GroundedAIApplicationService")
        if not isinstance(recording_service, GroundedProviderUsageCostLedgerRecordingService):
            raise TypeError("recording_service must be a GroundedProviderUsageCostLedgerRecordingService")
        self._application_service = application_service
        self._recording_service = recording_service

    def execute(self, request: GroundedAIApplicationRequest) -> GroundedAIApplicationResult:
        result = self._application_service.execute(request)
        trace: dict[str, Any] = result.trace
        provider_cost = trace.get("provider_cost")
        input_tokens = trace.get("provider_input_tokens")
        output_tokens = trace.get("provider_output_tokens")
        total_tokens = trace.get("provider_total_tokens")
        if provider_cost is None or input_tokens is None or output_tokens is None or total_tokens is None:
            raise RuntimeError("successful production generation must expose priced provider usage")
        usage = GroundedProviderUsage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens)
        cost = GroundedProviderCost(
            provider_identity=provider_cost["provider_identity"],
            model_identity=provider_cost["model_identity"],
            currency=provider_cost["currency"],
            input_cost=Decimal(provider_cost["input_cost"]),
            output_cost=Decimal(provider_cost["output_cost"]),
            total_cost=Decimal(provider_cost["total_cost"]),
        )
        self._recording_service.record(
            request_id=request.request_id,
            usage=usage,
            cost=cost,
            recorded_at=datetime.now(timezone.utc),
        )
        return result
