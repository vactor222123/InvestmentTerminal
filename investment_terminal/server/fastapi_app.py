"""
FastAPI runtime adapter for grounded AI.

The server layer owns HTTP framework integration only. It delegates decoded
request payloads to the existing framework-neutral GroundedAIHTTPHandler and
returns its status/body unchanged.
"""

from typing import Any

from fastapi import Body, FastAPI, Header
from fastapi.responses import JSONResponse

from investment_terminal.api.http_handler import (
    GroundedAIHTTPHandler,
)
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)


def create_grounded_ai_fastapi_app(
    *,
    handler: GroundedAIHTTPHandler,
    readiness_service: GroundedAIServerReadinessService | None = None,
    authenticator: GroundedAIServerAPIKeyAuthenticator | None = None,
) -> FastAPI:
    if not isinstance(
        handler,
        GroundedAIHTTPHandler,
    ):
        raise TypeError(
            "handler must be a GroundedAIHTTPHandler"
        )
    if (
        readiness_service is not None
        and not isinstance(
            readiness_service,
            GroundedAIServerReadinessService,
        )
    ):
        raise TypeError(
            "readiness_service must be a "
            "GroundedAIServerReadinessService or None"
        )
    if (
        authenticator is not None
        and not isinstance(
            authenticator,
            GroundedAIServerAPIKeyAuthenticator,
        )
    ):
        raise TypeError(
            "authenticator must be a "
            "GroundedAIServerAPIKeyAuthenticator or None"
        )

    app = FastAPI(
        title="Investment Terminal API",
        version="1",
    )

    @app.get(
        "/health",
        response_class=JSONResponse,
    )
    def health() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={
                "status": "OK",
            },
        )

    @app.get(
        "/ready",
        response_class=JSONResponse,
    )
    def ready() -> JSONResponse:
        if readiness_service is None:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "NOT_READY",
                    "checks": {},
                },
            )

        assessment = readiness_service.check()
        return JSONResponse(
            status_code=(
                200
                if assessment.ready
                else 503
            ),
            content=assessment.to_dict(),
        )

    @app.post(
        "/v1/grounded-ai",
        response_class=JSONResponse,
    )
    def grounded_ai(
        payload: Any = Body(...),
        api_key: str | None = Header(
            default=None,
            alias="X-API-Key",
        ),
    ) -> JSONResponse:
        if (
            authenticator is None
            or not authenticator.authenticate(
                api_key
            )
        ):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "ERROR",
                    "error": {
                        "category": "UNAUTHENTICATED",
                        "code": "SERVER_AUTHENTICATION_REQUIRED",
                        "message": "authentication required",
                    },
                },
            )

        response = handler.handle(
            payload
        )
        return JSONResponse(
            status_code=response.status_code,
            content=response.body,
        )

    return app
