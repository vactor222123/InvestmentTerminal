from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from investment_terminal.ai.providers.composition import DEFAULT_OPENAI_API_KEY_ENV
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)

DATABASE_ENV = "INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE"
MODEL_ENV = "INVESTMENT_TERMINAL_OPENAI_MODEL"
ALLOWED_MODELS_ENV = "INVESTMENT_TERMINAL_ALLOWED_OPENAI_MODELS"
TIMEOUT_ENV = "INVESTMENT_TERMINAL_PROVIDER_TIMEOUT_SECONDS"
MAX_RETRIES_ENV = "INVESTMENT_TERMINAL_PROVIDER_MAX_RETRIES"
API_KEY_ENV_NAME_ENV = "INVESTMENT_TERMINAL_OPENAI_API_KEY_ENV"
SERVER_API_KEY_ENV_NAME_ENV = "INVESTMENT_TERMINAL_SERVER_API_KEY_ENV"
DEFAULT_SERVER_API_KEY_ENV = "INVESTMENT_TERMINAL_SERVER_API_KEY"


@dataclass(frozen=True, slots=True)
class GroundedAIServerRuntimeConfig:
    database: Path
    model_identity: str
    allowed_models: tuple[str, ...]
    timeout_seconds: float
    max_retries: int
    api_key_environment_variable: str
    server_api_key_environment_variable: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]):
        database = Path(_required(environment, DATABASE_ENV))
        model_identity = _required(environment, MODEL_ENV)
        allowed_models = _csv_required(environment, ALLOWED_MODELS_ENV)
        timeout_seconds = _positive_float(environment.get(TIMEOUT_ENV, "30"), TIMEOUT_ENV)
        max_retries = _non_negative_int(environment.get(MAX_RETRIES_ENV, "2"), MAX_RETRIES_ENV)
        api_key_environment_variable = environment.get(
            API_KEY_ENV_NAME_ENV, DEFAULT_OPENAI_API_KEY_ENV
        ).strip()
        if not api_key_environment_variable:
            raise ValueError(f"{API_KEY_ENV_NAME_ENV} must not be empty")

        server_api_key_environment_variable = environment.get(
            SERVER_API_KEY_ENV_NAME_ENV,
            DEFAULT_SERVER_API_KEY_ENV,
        ).strip()
        if not server_api_key_environment_variable:
            raise ValueError(
                f"{SERVER_API_KEY_ENV_NAME_ENV} must not be empty"
            )

        if model_identity not in allowed_models:
            raise ValueError(
                f"{MODEL_ENV} must be explicitly present in {ALLOWED_MODELS_ENV}"
            )

        return cls(
            database=database,
            model_identity=model_identity,
            allowed_models=allowed_models,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            api_key_environment_variable=api_key_environment_variable,
            server_api_key_environment_variable=(
                server_api_key_environment_variable
            ),
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


def _required(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise ValueError(f"required environment variable is missing: {name}")
    return value


def _csv_required(environment: Mapping[str, str], name: str) -> tuple[str, ...]:
    values = tuple(v.strip() for v in _required(environment, name).split(",") if v.strip())
    if not values:
        raise ValueError(f"{name} must contain at least one value")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} values must be unique")
    return values


def _positive_float(value: str, field_name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a positive number") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return parsed


def _non_negative_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return parsed
