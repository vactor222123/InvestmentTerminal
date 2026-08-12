"""
Server-level unhandled exception sanitization.

This boundary is intentionally transport-only. It prevents unexpected runtime
exceptions from leaking raw messages or stack-derived details to clients.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GroundedAIServerInternalErrorResponse:
    status: str = "ERROR"
    category: str = "INTERNAL_ERROR"
    code: str = "SERVER_INTERNAL_ERROR"
    message: str = "internal server error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "error": {
                "category": self.category,
                "code": self.code,
                "message": self.message,
            },
        }
