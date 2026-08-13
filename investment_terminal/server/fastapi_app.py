"""
FastAPI runtime adapter for grounded AI.
"""

import json

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from investment_terminal.api.http_handler import GroundedAIHTTPHandler
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)
from investment_terminal.server.error_boundary import (
    GroundedAIServerInternalErrorResponse,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)
from investment_terminal.server.request_limits import (
    GroundedAIServerRequestLimitPolicy,
    GroundedAIServerRequestTooLargeError,
)
from investment_terminal.server.security_headers import (
    GroundedAIServerSecurityHeadersMiddleware,
)


def create_grounded_ai_fastapi_app(
    *,
    handler: GroundedAIHTTPHandler,
    readiness_service: GroundedAIServerReadinessService | None = None,
    authenticator: GroundedAIServerAPIKeyAuthenticator | None = None,
    request_limit_policy: GroundedAIServerRequestLimitPolicy | None = None,
) -> FastAPI:
    if not isinstance(handler, GroundedAIHTTPHandler):
        raise TypeError("handler must be a GroundedAIHTTPHandler")
    if readiness_service is not None and not isinstance(
        readiness_service, GroundedAIServerReadinessService
    ):
        raise TypeError(
            "readiness_service must be a GroundedAIServerReadinessService or None"
        )
    if authenticator is not None and not isinstance(
        authenticator, GroundedAIServerAPIKeyAuthenticator
    ):
        raise TypeError(
            "authenticator must be a GroundedAIServerAPIKeyAuthenticator or None"
        )
    if request_limit_policy is not None and not isinstance(
        request_limit_policy, GroundedAIServerRequestLimitPolicy
    ):
        raise TypeError(
            "request_limit_policy must be a GroundedAIServerRequestLimitPolicy or None"
        )

    active_limit_policy = (
        request_limit_policy
        if request_limit_policy is not None
        else GroundedAIServerRequestLimitPolicy()
    )

    app = FastAPI(
        title="Investment Terminal API",
        version="1",
    )
    app.add_middleware(
        GroundedAIServerSecurityHeadersMiddleware,
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        body = GroundedAIServerInternalErrorResponse().to_dict()
        return JSONResponse(
            status_code=500,
            content=body,
        )

    @app.get("/health", response_class=JSONResponse)
    def health() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"status": "OK"},
        )

    @app.get("/ready", response_class=JSONResponse)
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
            status_code=200 if assessment.ready else 503,
            content=assessment.to_dict(),
        )

    @app.post("/v1/grounded-ai", response_class=JSONResponse)
    async def grounded_ai(
        request: Request,
        api_key: str | None = Header(
            default=None,
            alias="X-API-Key",
        ),
    ) -> JSONResponse:
        if authenticator is None or not authenticator.authenticate(api_key):
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

        try:
            raw_body = await active_limit_policy.read_body(request)
        except GroundedAIServerRequestTooLargeError:
            return JSONResponse(
                status_code=413,
                content={
                    "status": "ERROR",
                    "error": {
                        "category": "REQUEST_TOO_LARGE",
                        "code": "SERVER_REQUEST_BODY_TOO_LARGE",
                        "message": "request body exceeds configured maximum",
                    },
                },
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "ERROR",
                    "error": {
                        "category": "INVALID_REQUEST",
                        "code": "SERVER_INVALID_JSON",
                        "message": "request body must contain valid UTF-8 JSON",
                    },
                },
            )

        response = handler.handle(payload)
        return JSONResponse(
            status_code=response.status_code,
            content=response.body,
        )

    return app
