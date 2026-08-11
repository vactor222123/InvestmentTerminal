"""
Production composition root for the OpenAI grounded generation path.
"""

from decimal import Decimal

from investment_terminal.ai.orchestration import GroundedGenerationService
from investment_terminal.ai.providers.contracts import GroundedProviderConfig
from investment_terminal.ai.providers.environment import (
    EnvironmentGroundedProviderCredentialSource,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
)
from investment_terminal.ai.providers.http_transport import (
    UrllibGroundedProviderTransport,
)
from investment_terminal.ai.providers.openai_adapter import (
    OpenAIGroundedModelAdapter,
)
from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
)
from investment_terminal.ai.providers.sleeper import (
    TimeGroundedProviderSleeper,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
)
from investment_terminal.utils.validation import normalize_required_text


DEFAULT_OPENAI_API_KEY_ENV = "INVESTMENT_TERMINAL_OPENAI_API_KEY"


def _retry_delay_policy(
    *,
    initial_delay_seconds: Decimal | None,
    multiplier: Decimal | None,
    maximum_delay_seconds: Decimal | None,
) -> GroundedProviderRetryDelayPolicy | None:
    supplied = (
        initial_delay_seconds is not None,
        multiplier is not None,
        maximum_delay_seconds is not None,
    )
    if not any(supplied):
        return None
    if not all(supplied):
        raise ValueError(
            "retry delay configuration requires initial delay, "
            "multiplier, and maximum delay together"
        )

    assert initial_delay_seconds is not None
    assert multiplier is not None
    assert maximum_delay_seconds is not None

    return GroundedProviderRetryDelayPolicy(
        initial_delay_seconds=initial_delay_seconds,
        multiplier=multiplier,
        maximum_delay_seconds=maximum_delay_seconds,
    )


def build_openai_grounded_generation_service(
    *,
    model_identity: str,
    timeout_seconds: float,
    max_retries: int,
    governance_policy: GroundedProviderGovernancePolicy,
    max_output_tokens: int | None = None,
    retry_initial_delay_seconds: Decimal | None = None,
    retry_delay_multiplier: Decimal | None = None,
    retry_maximum_delay_seconds: Decimal | None = None,
    api_key_environment_variable: str = DEFAULT_OPENAI_API_KEY_ENV,
    transport: GroundedProviderTransport | None = None,
) -> GroundedGenerationService:
    model = normalize_required_text(
        model_identity,
        field_name="model_identity",
    )

    if not isinstance(
        governance_policy,
        GroundedProviderGovernancePolicy,
    ):
        raise TypeError(
            "governance_policy must be a GroundedProviderGovernancePolicy"
        )

    governance_policy.require_allowed(
        provider_identity="OPENAI",
        model_identity=model,
    )

    delay_policy = _retry_delay_policy(
        initial_delay_seconds=retry_initial_delay_seconds,
        multiplier=retry_delay_multiplier,
        maximum_delay_seconds=retry_maximum_delay_seconds,
    )

    variable = normalize_required_text(
        api_key_environment_variable,
        field_name="api_key_environment_variable",
    )

    config = GroundedProviderConfig(
        provider_identity="OPENAI",
        model_identity=model,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
    )

    credentials = EnvironmentGroundedProviderCredentialSource(
        variable_by_provider={"OPENAI": variable}
    )

    active_transport = (
        transport
        if transport is not None
        else UrllibGroundedProviderTransport()
    )
    if not isinstance(
        active_transport,
        GroundedProviderTransport,
    ):
        raise TypeError(
            "transport must be a GroundedProviderTransport"
        )

    if delay_policy is None:
        execution = GroundedProviderExecutionService(
            transport=active_transport
        )
    else:
        execution = GroundedProviderExecutionService(
            transport=active_transport,
            retry_delay_policy=delay_policy,
            sleeper=TimeGroundedProviderSleeper(),
        )

    adapter = OpenAIGroundedModelAdapter(
        config=config,
        credentials=credentials,
        execution=execution,
    )
    return GroundedGenerationService(adapter=adapter)
