import os
from collections.abc import Mapping
from datetime import datetime, timezone

from fastapi import FastAPI

from investment_terminal.ai.generation_recording import (
    GroundedGenerationRecordingService,
)
from investment_terminal.ai.generation_sqlite_repository import (
    SQLiteGroundedGenerationRepository,
)
from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.ai.providers.usage_ledger_recording import GroundedProviderUsageCostLedgerRecordingService
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import SQLiteGroundedProviderUsageCostLedgerRepository
from investment_terminal.ai.providers.usage_ledger_sqlite_store import GroundedProviderUsageCostLedgerSQLiteStore
from investment_terminal.api.composition import build_live_grounded_ai_http_handler
from investment_terminal.server.authentication import GroundedAIServerAPIKeyAuthenticator
from investment_terminal.server.fastapi_app import create_grounded_ai_fastapi_app
from investment_terminal.server.rate_limit_admission import GroundedAIServerRateLimitAdmissionService
from investment_terminal.server.rate_limit_clock import GroundedAIServerMonotonicDecimalClock
from investment_terminal.server.rate_limit_identity import GroundedAIServerRateLimitIdentityDeriver
from investment_terminal.server.rate_limits import GroundedAIServerRateLimitPolicy
from investment_terminal.server.readiness import GroundedAIServerReadinessService
from investment_terminal.server.request_limits import GroundedAIServerRequestLimitPolicy
from investment_terminal.server.runtime_config import GroundedAIServerRuntimeConfig


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def create_app(environment: Mapping[str, str] | None = None) -> FastAPI:
    source = environment if environment is not None else os.environ
    config = GroundedAIServerRuntimeConfig.from_environment(source)

    ledger_store = GroundedProviderUsageCostLedgerSQLiteStore(
        config.usage_cost_ledger_database
    )
    ledger_store.initialize()
    ledger_repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        ledger_store
    )

    generation_store = GroundedGenerationSQLiteStore(
        config.grounded_generation_database
    )
    generation_store.initialize()
    generation_repository = SQLiteGroundedGenerationRepository(
        generation_store
    )

    handler = build_live_grounded_ai_http_handler(
        database=config.database, model_identity=config.model_identity, timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries, governance_policy=config.governance_policy(),
        requested_max_output_tokens=config.provider_max_output_tokens,
        api_key_environment_variable=config.api_key_environment_variable, pricing_policy=config.pricing_policy(),
        budget_policy=config.budget_policy(),
        usage_cost_recording_service=GroundedProviderUsageCostLedgerRecordingService(repository=ledger_repository),
        generation_recording_service=GroundedGenerationRecordingService(
            repository=generation_repository,
            clock=_utc_now,
        ),
    )

    readiness_service = GroundedAIServerReadinessService(config=config, environment=source)
    server_api_key = source.get(config.server_api_key_environment_variable, "")
    if not isinstance(server_api_key, str) or not server_api_key.strip():
        raise ValueError(
            "required server API key environment variable is missing: "
            f"{config.server_api_key_environment_variable}"
        )
    authenticator = GroundedAIServerAPIKeyAuthenticator(expected_api_key=server_api_key)
    request_limit_policy = GroundedAIServerRequestLimitPolicy(max_body_bytes=config.max_request_body_bytes)
    rate_limit_admission_service = GroundedAIServerRateLimitAdmissionService(
        policy=GroundedAIServerRateLimitPolicy(
            capacity=config.rate_limit_capacity, refill_tokens_per_second=config.rate_limit_refill_tokens_per_second,
        ),
        clock=GroundedAIServerMonotonicDecimalClock(),
    )
    return create_grounded_ai_fastapi_app(
        handler=handler, readiness_service=readiness_service, authenticator=authenticator,
        request_limit_policy=request_limit_policy, rate_limit_admission_service=rate_limit_admission_service,
        rate_limit_identity_deriver=GroundedAIServerRateLimitIdentityDeriver(),
    )
