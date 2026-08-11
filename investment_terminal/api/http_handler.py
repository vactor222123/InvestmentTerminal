"""
Framework-neutral HTTP handler for grounded AI.

Transforms an already-decoded transport payload into the stable API request,
executes the API adapter, and maps the API response to deterministic HTTP
semantics. It owns no web framework, route registration, socket, or JSON parser.
"""

from typing import Any

from investment_terminal.api.grounded_ai import (
    GroundedAIAPIAdapter,
    GroundedAIAPIRequest,
    GroundedAIAPIResponse,
)
from investment_terminal.api.http_mapping import (
    GroundedAIHTTPResponse,
    GroundedAIHTTPStatusMapper,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationService,
)


class GroundedAIHTTPHandler:
    """Synchronous framework-neutral HTTP request handler."""

    def __init__(
        self,
        *,
        application_service: GroundedAIApplicationService,
        status_mapper: GroundedAIHTTPStatusMapper | None = None,
    ) -> None:
        self._api_adapter = GroundedAIAPIAdapter(
            application_service=application_service,
        )
        self._status_mapper = (
            status_mapper
            if status_mapper is not None
            else GroundedAIHTTPStatusMapper()
        )
        if not isinstance(
            self._status_mapper,
            GroundedAIHTTPStatusMapper,
        ):
            raise TypeError(
                "status_mapper must be a "
                "GroundedAIHTTPStatusMapper"
            )

    def handle(
        self,
        payload: dict[str, Any],
    ) -> GroundedAIHTTPResponse:
        request_id = self._request_id_for_error(
            payload
        )

        try:
            request = GroundedAIAPIRequest.from_dict(
                payload
            )
        except (TypeError, ValueError) as exc:
            return self._status_mapper.map(
                GroundedAIAPIResponse(
                    status="ERROR",
                    request_id=request_id,
                    error={
                        "category": "INVALID_REQUEST",
                        "code": "API_INVALID_REQUEST",
                        "message": str(exc),
                    },
                )
            )

        return self._status_mapper.map(
            self._api_adapter.handle(
                request
            )
        )

    @staticmethod
    def _request_id_for_error(
        payload: Any,
    ) -> str:
        if isinstance(
            payload,
            dict,
        ):
            request_id = payload.get(
                "request_id"
            )
            if isinstance(
                request_id,
                str,
            ) and request_id.strip():
                return request_id.strip()

        # A malformed request may not contain a valid client request id.
        # Keep the response schema stable without inventing identity.
        return "UNKNOWN"
