"""
Application composition root for live grounded AI.

This module owns infrastructure construction for the grounded AI application:
Knowledge SQLite query, provider generation composition, and concrete
application service assembly. CLI and HTTP adapters depend on this single
composition boundary.
"""

from decimal import Decimal
from pathlib import Path

from investment_terminal.ai.generation_recording import (
    GroundedGenerationRecordingService,
)
from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
    build_openai_grounded_generation_service,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.ai.providers.pricing import (
    GroundedProviderPricingPolicy,
)
from investment_terminal.application.live_grounded_ai import (
    LiveGroundedAIApplicationService,
)
from investment_terminal.knowledge.query_service import (
    KnowledgeQueryService,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


def build_live_grounded_ai_application(
    *,
    database: Path,
    model_identity: str,
    timeout_seconds: float,
    max_retries: int,
    governance_policy: GroundedProviderGovernancePolicy,
    requested_max_output_tokens: int | None = None,
    retry_initial_delay_seconds: Decimal | None = None,
    retry_delay_multiplier: Decimal | None = None,
    retry_maximum_delay_seconds: Decimal | None = None,
    api_key_environment_variable: str = DEFAULT_OPENAI_API_KEY_ENV,
    pricing_policy: GroundedProviderPricingPolicy | None = None,
    budget_policy: GroundedProviderBudgetPolicy | None = None,
    generation_recording_service: (
        GroundedGenerationRecordingService | None
    ) = None,
) -> LiveGroundedAIApplicationService:
    if not isinstance(
        database,
        Path,
    ):
        raise TypeError(
            "database must be a Path"
        )
    if not database.is_file():
        raise ValueError(
            f"Knowledge database does not exist: {database}"
        )

    query = KnowledgeQueryService(
        repository=SQLiteKnowledgeRecordRepository(
            KnowledgeSQLiteStore(
                database
            )
        )
    )

    generation_service = (
        build_openai_grounded_generation_service(
            model_identity=model_identity,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            governance_policy=governance_policy,
            max_output_tokens=requested_max_output_tokens,
            retry_initial_delay_seconds=retry_initial_delay_seconds,
            retry_delay_multiplier=retry_delay_multiplier,
            retry_maximum_delay_seconds=retry_maximum_delay_seconds,
            api_key_environment_variable=api_key_environment_variable,
        )
    )

    return LiveGroundedAIApplicationService(
        query=query,
        generation_service=generation_service,
        pricing_policy=pricing_policy,
        budget_policy=budget_policy,
        requested_max_output_tokens=requested_max_output_tokens,
        generation_recording_service=generation_recording_service,
    )
