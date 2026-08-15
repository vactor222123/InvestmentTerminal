"""Authenticated read-only HTTP routes for persisted grounded generations."""

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse

from investment_terminal.application.grounded_generation_history import (
    GroundedGenerationHistoryService,
)
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)


def install_grounded_generation_routes(
    *,
    app: FastAPI,
    history_service: GroundedGenerationHistoryService,
    authenticator: GroundedAIServerAPIKeyAuthenticator,
) -> None:
    if not isinstance(
        history_service,
        GroundedGenerationHistoryService,
    ):
        raise TypeError(
            "history_service must be a GroundedGenerationHistoryService"
        )
    if not isinstance(
        authenticator,
        GroundedAIServerAPIKeyAuthenticator,
    ):
        raise TypeError(
            "authenticator must be a GroundedAIServerAPIKeyAuthenticator"
        )

    def authenticated(
        api_key: str | None,
    ) -> bool:
        return authenticator.authenticate(
            api_key
        )

    def authentication_error() -> JSONResponse:
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

    @app.get(
        "/v1/grounded-generations",
        response_class=JSONResponse,
        operation_id="grounded_generations_recent",
        summary="List recent persisted grounded generations",
    )
    def recent_grounded_generations(
        limit: int = Query(
            ...,
            ge=1,
            le=100,
            description="Maximum number of newest generations to return",
        ),
        api_key: str | None = Header(
            default=None,
            alias="X-API-Key",
            description="Inbound Investment Terminal API key",
        ),
    ) -> JSONResponse:
        if not authenticated(
            api_key
        ):
            return authentication_error()

        records = history_service.recent(
            limit
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "SUCCESS",
                "data": {
                    "count": len(records),
                    "records": [
                        record.to_dict()
                        for record in records
                    ],
                },
            },
        )

    @app.get(
        "/v1/grounded-generations/{request_id}",
        response_class=JSONResponse,
        operation_id="grounded_generation_show",
        summary="Read one persisted grounded generation",
    )
    def grounded_generation_by_request(
        request_id: str,
        api_key: str | None = Header(
            default=None,
            alias="X-API-Key",
            description="Inbound Investment Terminal API key",
        ),
    ) -> JSONResponse:
        if not authenticated(
            api_key
        ):
            return authentication_error()

        try:
            record = history_service.require(
                request_id
            )
        except KeyError:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "ERROR",
                    "error": {
                        "category": "NOT_FOUND",
                        "code": "GROUNDED_GENERATION_NOT_FOUND",
                        "message": "grounded generation not found",
                    },
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "SUCCESS",
                "data": {
                    "record": record.to_dict(),
                },
            },
        )
