"""
Production composition root for the OpenAI grounded generation path.

The composition owns concrete infrastructure wiring only. Domain grounding,
parsing, and orchestration semantics remain in their existing services.
"""

from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
)
from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
)
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
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


DEFAULT_OPENAI_API_KEY_ENV = (
    "INVESTMENT_TERMINAL_OPENAI_API_KEY"
)


def build_openai_grounded_generation_service(
    *,
    model_identity: str,
    timeout_seconds: float,
    max_retries: int,
    governance_policy: GroundedProviderGovernancePolicy,
    api_key_environment_variable: str = DEFAULT_OPENAI_API_KEY_ENV,
    transport: GroundedProviderTransport | None = None,
) -> GroundedGenerationService:
    """
    Build the live-ready OpenAI grounded generation service.

    Governance is enforced before credential-source and transport construction.
    transport is injectable for offline tests. Production defaults to the real
    urllib-backed HTTP transport.
    """

    model = normalize_required_text(
        model_identity,
        field_name="model_identity",
    )

    if not isinstance(
        governance_policy,
        GroundedProviderGovernancePolicy,
    ):
        raise TypeError(
            "governance_policy must be a "
            "GroundedProviderGovernancePolicy"
        )

    governance_policy.require_allowed(
        provider_identity="OPENAI",
        model_identity=model,
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
    )

    credentials = EnvironmentGroundedProviderCredentialSource(
        variable_by_provider={
            "OPENAI": variable,
        }
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

    execution = GroundedProviderExecutionService(
        transport=active_transport
    )

    adapter = OpenAIGroundedModelAdapter(
        config=config,
        credentials=credentials,
        execution=execution,
    )

    return GroundedGenerationService(
        adapter=adapter
    )
