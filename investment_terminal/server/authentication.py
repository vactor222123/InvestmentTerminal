"""
Inbound server authentication for grounded AI routes.

This module owns API-key verification only. It does not know about Knowledge,
providers, application services, or FastAPI request objects.
"""

from dataclasses import dataclass
from hmac import compare_digest


@dataclass(frozen=True, slots=True)
class GroundedAIServerAPIKeyAuthenticator:
    expected_api_key: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.expected_api_key, str)
            or not self.expected_api_key.strip()
        ):
            raise ValueError(
                "expected_api_key must be a non-empty string"
            )

    def authenticate(
        self,
        provided_api_key: str | None,
    ) -> bool:
        if not isinstance(
            provided_api_key,
            str,
        ):
            return False

        candidate = provided_api_key.strip()
        if not candidate:
            return False

        return compare_digest(
            candidate,
            self.expected_api_key,
        )
