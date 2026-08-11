"""
Provider operational contracts for real model integration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from investment_terminal.utils.validation import normalize_required_text


@dataclass(frozen=True, slots=True)
class GroundedProviderConfig:
    """Immutable non-secret operational configuration for one provider model."""

    provider_identity: str
    model_identity: str
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        for field_name in ("provider_identity", "model_identity"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be a positive number"
            )
        object.__setattr__(
            self,
            "timeout_seconds",
            float(self.timeout_seconds),
        )

        if (
            isinstance(self.max_retries, bool)
            or not isinstance(self.max_retries, int)
            or self.max_retries < 0
        ):
            raise ValueError(
                "max_retries must be a non-negative integer"
            )

        if self.max_output_tokens is not None and (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens <= 0
        ):
            raise ValueError(
                "max_output_tokens must be a positive integer or None"
            )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }
        if self.max_output_tokens is not None:
            data["max_output_tokens"] = self.max_output_tokens
        return data


class GroundedProviderCredentialSource(ABC):
    @abstractmethod
    def get_api_key(
        self,
        *,
        provider_identity: str,
    ) -> str:
        """Return the API key for the requested provider identity."""


class StaticGroundedProviderCredentialSource(
    GroundedProviderCredentialSource
):
    def __init__(
        self,
        *,
        provider_identity: str,
        api_key: str,
    ) -> None:
        self._provider_identity = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
        )
        self._api_key = normalize_required_text(
            api_key,
            field_name="api_key",
        )

    def get_api_key(
        self,
        *,
        provider_identity: str,
    ) -> str:
        normalized = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
        )
        if normalized != self._provider_identity:
            raise KeyError(
                f"No credential configured for provider: {normalized}"
            )
        return self._api_key
