"""
FastAPI runtime adapter for grounded AI.

The server layer owns HTTP framework integration only. It delegates decoded
request payloads to the existing framework-neutral GroundedAIHTTPHandler and
returns its status/body unchanged.
"""

from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse

from investment_terminal.api.http_handler import GroundedAIHTTPHandler


def create_grounded_ai_fastapi_app(
    *,
    handler: GroundedAIHTTPHandler,
) -> FastAPI:
    if not isinstance(handler, GroundedAIHTTPHandler):
        raise TypeError("handler must be a GroundedAIHTTPHandler")

    app = FastAPI(
        title="Investment Terminal API",
        version="1",
    )

    @app.post("/v1/grounded-ai", response_class=JSONResponse)
    def grounded_ai(payload: Any = Body(...)) -> JSONResponse:
        response = handler.handle(payload)
        return JSONResponse(
            status_code=response.status_code,
            content=response.body,
        )

    return app
