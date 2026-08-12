import os
from collections.abc import Mapping

from fastapi import FastAPI

from investment_terminal.api.composition import (
    build_live_grounded_ai_http_handler,
)
from investment_terminal.server.fastapi_app import (
    create_grounded_ai_fastapi_app,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)
from investment_terminal.server.runtime_config import (
    GroundedAIServerRuntimeConfig,
)


def create_app(
    environment: Mapping[str, str] | None = None,
) -> FastAPI:
    source = (
        environment
        if environment is not None
        else os.environ
    )
    config = (
        GroundedAIServerRuntimeConfig.from_environment(
            source
        )
    )

    handler = build_live_grounded_ai_http_handler(
        database=config.database,
        model_identity=config.model_identity,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        governance_policy=config.governance_policy(),
        api_key_environment_variable=(
            config.api_key_environment_variable
        ),
    )

    readiness_service = (
        GroundedAIServerReadinessService(
            config=config,
            environment=source,
        )
    )

    return create_grounded_ai_fastapi_app(
        handler=handler,
        readiness_service=readiness_service,
    )
