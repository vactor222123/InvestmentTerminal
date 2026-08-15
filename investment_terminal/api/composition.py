"""API composition root for live grounded AI HTTP handling."""

from decimal import Decimal
from pathlib import Path

from investment_terminal.ai.providers.composition import DEFAULT_OPENAI_API_KEY_ENV
from investment_terminal.ai.providers.governance import GroundedProviderGovernancePolicy
from investment_terminal.ai.providers.guardrails import GroundedProviderBudgetPolicy
from investment_terminal.ai.providers.pricing import GroundedProviderPricingPolicy
from investment_terminal.ai.providers.usage_ledger_recording import GroundedProviderUsageCostLedgerRecordingService
from investment_terminal.api.http_handler import GroundedAIHTTPHandler
from investment_terminal.application.composition import build_live_grounded_ai_application
from investment_terminal.application.usage_ledger import UsageCostRecordingGroundedAIApplicationService


def build_live_grounded_ai_http_handler(
    *, database: Path, model_identity: str, timeout_seconds: float, max_retries: int,
    governance_policy: GroundedProviderGovernancePolicy, requested_max_output_tokens: int | None = None,
    retry_initial_delay_seconds: Decimal | None = None, retry_delay_multiplier: Decimal | None = None,
    retry_maximum_delay_seconds: Decimal | None = None, api_key_environment_variable: str = DEFAULT_OPENAI_API_KEY_ENV,
    pricing_policy: GroundedProviderPricingPolicy | None = None, budget_policy: GroundedProviderBudgetPolicy | None = None,
    usage_cost_recording_service: GroundedProviderUsageCostLedgerRecordingService | None = None,
) -> GroundedAIHTTPHandler:
    application = build_live_grounded_ai_application(
        database=database, model_identity=model_identity, timeout_seconds=timeout_seconds, max_retries=max_retries,
        governance_policy=governance_policy, requested_max_output_tokens=requested_max_output_tokens,
        retry_initial_delay_seconds=retry_initial_delay_seconds, retry_delay_multiplier=retry_delay_multiplier,
        retry_maximum_delay_seconds=retry_maximum_delay_seconds, api_key_environment_variable=api_key_environment_variable,
        pricing_policy=pricing_policy, budget_policy=budget_policy,
    )
    if usage_cost_recording_service is not None:
        application = UsageCostRecordingGroundedAIApplicationService(
            application_service=application, recording_service=usage_cost_recording_service,
        )
    return GroundedAIHTTPHandler(application_service=application)
