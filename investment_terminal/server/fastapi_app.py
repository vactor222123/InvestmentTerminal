"""
FastAPI runtime adapter for grounded AI.
"""

import json
from decimal import ROUND_CEILING

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from investment_terminal.api.http_handler import GroundedAIHTTPHandler
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)
from investment_terminal.server.error_boundary import (
    GroundedAIServerInternalErrorResponse,
)
from investment_terminal.server.openapi_contract import (
    grounded_ai_openapi_extra,
)
from investment_terminal.server.rate_limit_admission import (
    GroundedAIServerRateLimitAdmissionService,
)
from investment_terminal.server.rate_limit_headers import (
    grounded_ai_rate_limit_headers,
)
from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentityDeriver,
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
    rate_limit_admission_service: (
        GroundedAIServerRateLimitAdmissionService | None
    ) = None,
    rate_limit_identity_deriver: (
        GroundedAIServerRateLimitIdentityDeriver | None
    ) = None,
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
    if rate_limit_admission_service is not None and not isinstance(
        rate_limit_admission_service,
        GroundedAIServerRateLimitAdmissionService,
    ):
        raise TypeError(
            "rate_limit_admission_service must be a "
            "GroundedAIServerRateLimitAdmissionService or None"
        )
    if rate_limit_identity_deriver is not None and not isinstance(
        rate_limit_identity_deriver,
        GroundedAIServerRateLimitIdentityDeriver,
    ):
        raise TypeError(
            "rate_limit_identity_deriver must be a "
            "GroundedAIServerRateLimitIdentityDeriver or None"
        )
    if (
        rate_limit_admission_service is None
    ) != (
        rate_limit_identity_deriver is None
    ):
        raise ValueError(
            "rate-limit admission service and identity deriver "
            "must be configured together"
        )

    active_limit_policy = (
        request_limit_policy
        if request_limit_policy is not None
        else GroundedAIServerRequestLimitPolicy()
    )

    app = FastAPI(
        title="Investment Terminal API",
        version="1",
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
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

    @app.get(
        "/health",
        response_class=JSONResponse,
        include_in_schema=False,
    )
    def health() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"status": "OK"},
        )

    @app.get(
        "/ready",
        response_class=JSONResponse,
        include_in_schema=False,
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
            status_code=200 if assessment.ready else 503,
            content=assessment.to_dict(),
        )

    @app.post(
        "/v1/grounded-ai",
        response_class=JSONResponse,
        operation_id="grounded_ai_generate",
        summary="Generate a grounded AI response",
        openapi_extra=grounded_ai_openapi_extra(),
    )
    async def grounded_ai(
        request: Request,
        api_key: str | None = Header(
            default=None,
            alias="X-API-Key",
            description="Inbound Investment Terminal API key",
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

        rate_limit_headers: dict[str, str] = {}
        if rate_limit_admission_service is not None:
            identity = rate_limit_identity_deriver.derive(
                api_key
            )
            decision = rate_limit_admission_service.decide(
                identity=identity
            )
            rate_limit_headers = grounded_ai_rate_limit_headers(
                policy=rate_limit_admission_service.policy,
                decision=decision,
            )
            if not decision.allowed:
                retry_after_seconds = int(
                    decision.retry_after_seconds.to_integral_value(
                        rounding=ROUND_CEILING,
                    )
                )
                return JSONResponse(
                    status_code=429,
                    headers={
                        **rate_limit_headers,
                        "Retry-After": str(
                            max(
                                1,
                                retry_after_seconds,
                            )
                        ),
                    },
                    content={
                        "status": "ERROR",
                        "error": {
                            "category": "RATE_LIMITED",
                            "code": "SERVER_RATE_LIMIT_EXCEEDED",
                            "message": "request rate limit exceeded",
                        },
                    },
                )

        try:
            raw_body = await active_limit_policy.read_body(request)
        except GroundedAIServerRequestTooLargeError:
            return JSONResponse(
                status_code=413,
                headers=rate_limit_headers,
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
                headers=rate_limit_headers,
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
            headers=rate_limit_headers,
            content=response.body,
        )

    return app
