from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from investment_terminal.ai.providers.composition import DEFAULT_OPENAI_API_KEY_ENV
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.ai.providers.pricing import (
    GroundedProviderPricingEntry,
    GroundedProviderPricingPolicy,
)

DATABASE_ENV = "INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE"
MODEL_ENV = "INVESTMENT_TERMINAL_OPENAI_MODEL"
ALLOWED_MODELS_ENV = "INVESTMENT_TERMINAL_ALLOWED_OPENAI_MODELS"
TIMEOUT_ENV = "INVESTMENT_TERMINAL_PROVIDER_TIMEOUT_SECONDS"
MAX_RETRIES_ENV = "INVESTMENT_TERMINAL_PROVIDER_MAX_RETRIES"
API_KEY_ENV_NAME_ENV = "INVESTMENT_TERMINAL_OPENAI_API_KEY_ENV"
SERVER_API_KEY_ENV_NAME_ENV = "INVESTMENT_TERMINAL_SERVER_API_KEY_ENV"
DEFAULT_SERVER_API_KEY_ENV = "INVESTMENT_TERMINAL_SERVER_API_KEY"
MAX_REQUEST_BODY_BYTES_ENV = "INVESTMENT_TERMINAL_MAX_REQUEST_BODY_BYTES"
DEFAULT_MAX_REQUEST_BODY_BYTES = 65536

PROVIDER_MAX_OUTPUT_TOKENS_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_MAX_OUTPUT_TOKENS"
)
PROVIDER_MAX_TOTAL_TOKENS_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_TOKENS"
)
PROVIDER_MAX_TOTAL_COST_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_COST"
)
PROVIDER_BUDGET_CURRENCY_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_BUDGET_CURRENCY"
)
PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_INPUT_COST_PER_MILLION_TOKENS"
)
PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS"
)
PROVIDER_PRICING_CURRENCY_ENV = (
    "INVESTMENT_TERMINAL_PROVIDER_PRICING_CURRENCY"
)

RATE_LIMIT_CAPACITY_ENV = "INVESTMENT_TERMINAL_RATE_LIMIT_CAPACITY"
RATE_LIMIT_REFILL_PER_SECOND_ENV = (
    "INVESTMENT_TERMINAL_RATE_LIMIT_REFILL_TOKENS_PER_SECOND"
)
DEFAULT_RATE_LIMIT_CAPACITY = 10
DEFAULT_RATE_LIMIT_REFILL_PER_SECOND = Decimal("1")


@dataclass(frozen=True, slots=True)
class GroundedAIServerRuntimeConfig:
    database: Path
    model_identity: str
    allowed_models: tuple[str, ...]
    timeout_seconds: float
    max_retries: int
    api_key_environment_variable: str
    server_api_key_environment_variable: str
    max_request_body_bytes: int
    provider_max_output_tokens: int
    provider_max_total_tokens: int
    provider_max_total_cost: Decimal
    provider_budget_currency: str
    provider_input_cost_per_million_tokens: Decimal
    provider_output_cost_per_million_tokens: Decimal
    provider_pricing_currency: str
    rate_limit_capacity: int
    rate_limit_refill_tokens_per_second: Decimal

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]):
        database = Path(_required(environment, DATABASE_ENV))
        model_identity = _required(environment, MODEL_ENV)
        allowed_models = _csv_required(environment, ALLOWED_MODELS_ENV)
        timeout_seconds = _positive_float(
            environment.get(TIMEOUT_ENV, "30"),
            TIMEOUT_ENV,
        )
        max_retries = _non_negative_int(
            environment.get(MAX_RETRIES_ENV, "2"),
            MAX_RETRIES_ENV,
        )
        api_key_environment_variable = environment.get(
            API_KEY_ENV_NAME_ENV,
            DEFAULT_OPENAI_API_KEY_ENV,
        ).strip()
        if not api_key_environment_variable:
            raise ValueError(
                f"{API_KEY_ENV_NAME_ENV} must not be empty"
            )

        server_api_key_environment_variable = environment.get(
            SERVER_API_KEY_ENV_NAME_ENV,
            DEFAULT_SERVER_API_KEY_ENV,
        ).strip()
        if not server_api_key_environment_variable:
            raise ValueError(
                f"{SERVER_API_KEY_ENV_NAME_ENV} must not be empty"
            )

        max_request_body_bytes = _positive_int(
            environment.get(
                MAX_REQUEST_BODY_BYTES_ENV,
                str(DEFAULT_MAX_REQUEST_BODY_BYTES),
            ),
            MAX_REQUEST_BODY_BYTES_ENV,
        )

        provider_max_output_tokens = _positive_int(
            _required(environment, PROVIDER_MAX_OUTPUT_TOKENS_ENV),
            PROVIDER_MAX_OUTPUT_TOKENS_ENV,
        )
        provider_max_total_tokens = _positive_int(
            _required(environment, PROVIDER_MAX_TOTAL_TOKENS_ENV),
            PROVIDER_MAX_TOTAL_TOKENS_ENV,
        )
        provider_max_total_cost = _non_negative_decimal(
            _required(environment, PROVIDER_MAX_TOTAL_COST_ENV),
            PROVIDER_MAX_TOTAL_COST_ENV,
        )
        provider_budget_currency = _currency_required(
            environment,
            PROVIDER_BUDGET_CURRENCY_ENV,
        )
        provider_input_cost_per_million_tokens = _non_negative_decimal(
            _required(
                environment,
                PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
            ),
            PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
        )
        provider_output_cost_per_million_tokens = _non_negative_decimal(
            _required(
                environment,
                PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
            ),
            PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
        )
        provider_pricing_currency = _currency_required(
            environment,
            PROVIDER_PRICING_CURRENCY_ENV,
        )

        if provider_budget_currency != provider_pricing_currency:
            raise ValueError(
                f"{PROVIDER_BUDGET_CURRENCY_ENV} must match "
                f"{PROVIDER_PRICING_CURRENCY_ENV}"
            )

        rate_limit_capacity = _positive_int(
            environment.get(
                RATE_LIMIT_CAPACITY_ENV,
                str(DEFAULT_RATE_LIMIT_CAPACITY),
            ),
            RATE_LIMIT_CAPACITY_ENV,
        )
        rate_limit_refill_tokens_per_second = _positive_decimal(
            environment.get(
                RATE_LIMIT_REFILL_PER_SECOND_ENV,
                str(DEFAULT_RATE_LIMIT_REFILL_PER_SECOND),
            ),
            RATE_LIMIT_REFILL_PER_SECOND_ENV,
        )

        if model_identity not in allowed_models:
            raise ValueError(
                f"{MODEL_ENV} must be explicitly present in "
                f"{ALLOWED_MODELS_ENV}"
            )

        return cls(
            database=database,
            model_identity=model_identity,
            allowed_models=allowed_models,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            api_key_environment_variable=api_key_environment_variable,
            server_api_key_environment_variable=server_api_key_environment_variable,
            max_request_body_bytes=max_request_body_bytes,
            provider_max_output_tokens=provider_max_output_tokens,
            provider_max_total_tokens=provider_max_total_tokens,
            provider_max_total_cost=provider_max_total_cost,
            provider_budget_currency=provider_budget_currency,
            provider_input_cost_per_million_tokens=provider_input_cost_per_million_tokens,
            provider_output_cost_per_million_tokens=provider_output_cost_per_million_tokens,
            provider_pricing_currency=provider_pricing_currency,
            rate_limit_capacity=rate_limit_capacity,
            rate_limit_refill_tokens_per_second=rate_limit_refill_tokens_per_second,
        )

    def governance_policy(self) -> GroundedProviderGovernancePolicy:
        return GroundedProviderGovernancePolicy(
            allowed_models=tuple(
                GroundedProviderModelAllowance(
                    provider_identity="OPENAI",
                    model_identity=model,
                )
                for model in self.allowed_models
            )
        )

    def pricing_policy(self) -> GroundedProviderPricingPolicy:
        return GroundedProviderPricingPolicy(
            entries=(
                GroundedProviderPricingEntry(
                    provider_identity="OPENAI",
                    model_identity=self.model_identity,
                    input_cost_per_million_tokens=self.provider_input_cost_per_million_tokens,
                    output_cost_per_million_tokens=self.provider_output_cost_per_million_tokens,
                    currency=self.provider_pricing_currency,
                ),
            )
        )

    def budget_policy(self) -> GroundedProviderBudgetPolicy:
        return GroundedProviderBudgetPolicy(
            max_output_tokens=self.provider_max_output_tokens,
            max_total_tokens=self.provider_max_total_tokens,
            max_total_cost=self.provider_max_total_cost,
            currency=self.provider_budget_currency,
        )


def _required(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise ValueError(
            f"required environment variable is missing: {name}"
        )
    return value


def _csv_required(
    environment: Mapping[str, str],
    name: str,
) -> tuple[str, ...]:
    values = tuple(
        v.strip()
        for v in _required(environment, name).split(",")
        if v.strip()
    )
    if not values:
        raise ValueError(
            f"{name} must contain at least one value"
        )
    if len(set(values)) != len(values):
        raise ValueError(
            f"{name} values must be unique"
        )
    return values


def _currency_required(
    environment: Mapping[str, str],
    name: str,
) -> str:
    return _required(environment, name).upper()


def _positive_float(value: str, field_name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a positive number"
        ) from exc
    if parsed <= 0:
        raise ValueError(
            f"{field_name} must be a positive number"
        )
    return parsed


def _non_negative_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a non-negative integer"
        ) from exc
    if parsed < 0:
        raise ValueError(
            f"{field_name} must be a non-negative integer"
        )
    return parsed


def _positive_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be a positive integer"
        ) from exc
    if parsed <= 0:
        raise ValueError(
            f"{field_name} must be a positive integer"
        )
    return parsed


def _non_negative_decimal(
    value: str,
    field_name: str,
) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(
            f"{field_name} must be a non-negative decimal"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(
            f"{field_name} must be a non-negative decimal"
        )
    return parsed


def _positive_decimal(
    value: str,
    field_name: str,
) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(
            f"{field_name} must be a positive decimal"
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(
            f"{field_name} must be a positive decimal"
        )
    return parsed
