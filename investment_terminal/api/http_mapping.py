"""
Deterministic HTTP status mapping for framework-neutral grounded AI API responses.

This module contains HTTP semantics only. It does not start a server, register
routes, depend on a web framework, or mutate the API/application contracts.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.api.grounded_ai import (
    GroundedAIAPIResponse,
)


@dataclass(frozen=True, slots=True)
class GroundedAIHTTPResponse:
    status_code: int
    body: dict[str, Any]

    def __post_init__(self) -> None:
        if (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ValueError(
                "status_code must be an HTTP status code"
            )
        if not isinstance(
            self.body,
            dict,
        ):
            raise TypeError(
                "body must be a dictionary"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "body": self.body,
        }


class GroundedAIHTTPStatusMapper:
    """Map stable API response semantics to deterministic HTTP status codes."""

    ERROR_CATEGORY_STATUS = {
        "INVALID_REQUEST": 400,
        "POLICY_DENIED": 403,
        "EXECUTION_FAILED": 503,
        "INTERNAL_ERROR": 500,
    }

    def map(
        self,
        response: GroundedAIAPIResponse,
    ) -> GroundedAIHTTPResponse:
        if not isinstance(
            response,
            GroundedAIAPIResponse,
        ):
            raise TypeError(
                "response must be a GroundedAIAPIResponse"
            )

        if response.status == "SUCCESS":
            status_code = 200
        else:
            assert response.error is not None
            category = response.error.get(
                "category"
            )
            status_code = self.ERROR_CATEGORY_STATUS.get(
                category,
                500,
            )

        return GroundedAIHTTPResponse(
            status_code=status_code,
            body=response.to_dict(),
        )
