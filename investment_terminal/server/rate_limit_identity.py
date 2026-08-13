"""
Opaque authenticated identity derivation for inbound rate limiting.

Raw API keys are never exposed as rate-limit identities.
"""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class GroundedAIServerRateLimitIdentity:
    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or len(self.value) != 64
        ):
            raise ValueError(
                "rate-limit identity must be a 64-character SHA-256 hex digest"
            )
        try:
            bytes.fromhex(
                self.value
            )
        except ValueError as exc:
            raise ValueError(
                "rate-limit identity must be valid hexadecimal"
            ) from exc

    def __str__(self) -> str:
        return self.value


class GroundedAIServerRateLimitIdentityDeriver:
    """Derive a deterministic opaque identity from an authenticated API key."""

    def derive(
        self,
        authenticated_api_key: str,
    ) -> GroundedAIServerRateLimitIdentity:
        if (
            not isinstance(authenticated_api_key, str)
            or not authenticated_api_key.strip()
        ):
            raise ValueError(
                "authenticated_api_key must be a non-empty string"
            )

        normalized = authenticated_api_key.strip()
        digest = sha256(
            normalized.encode("utf-8")
        ).hexdigest()

        return GroundedAIServerRateLimitIdentity(
            value=digest,
        )
