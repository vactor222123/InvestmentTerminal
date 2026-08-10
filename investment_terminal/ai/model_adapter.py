"""
Provider-independent model adapter contract for Evidence-Grounded AI.

This module defines the boundary between canonical prompt input and an external
text-generation provider. It imports no provider SDK and performs no network I/O.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from investment_terminal.ai.prompt_input import GroundedPromptInput
from investment_terminal.utils.validation import normalize_required_text


@dataclass(frozen=True, slots=True)
class GroundedProviderUsage:
    """Provider-neutral token usage totals for one completed model response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        for field_name in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError(
                "total_tokens must equal input_tokens + output_tokens"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderOperationalMetadata:
    """Safe provider execution metadata with no headers, bodies, or secrets."""

    attempt_count: int
    retry_count: int
    transport_status_code: int
    transport_outcome: str = "SUCCESS"

    def __post_init__(self) -> None:
        for field_name in ("attempt_count", "retry_count"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.attempt_count < 1:
            raise ValueError("attempt_count must be at least 1")
        if self.retry_count != self.attempt_count - 1:
            raise ValueError(
                "retry_count must equal attempt_count - 1"
            )

        if (
            isinstance(self.transport_status_code, bool)
            or not isinstance(self.transport_status_code, int)
            or not 100 <= self.transport_status_code <= 599
        ):
            raise ValueError(
                "transport_status_code must be an HTTP status code"
            )

        object.__setattr__(
            self,
            "transport_outcome",
            normalize_required_text(
                self.transport_outcome,
                field_name="transport_outcome",
                uppercase=True,
            ),
        )
        if self.transport_outcome != "SUCCESS":
            raise ValueError(
                "successful model response operational metadata "
                "requires transport_outcome SUCCESS"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_count": self.attempt_count,
            "retry_count": self.retry_count,
            "transport_status_code": self.transport_status_code,
            "transport_outcome": self.transport_outcome,
        }


@dataclass(frozen=True, slots=True)
class GroundedModelResponse:
    """Immutable raw generation result correlated to one grounded prompt."""

    request_id: str
    provider_identity: str
    model_identity: str
    raw_text: str
    operational_metadata: GroundedProviderOperationalMetadata | None = None
    usage: GroundedProviderUsage | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "provider_identity",
            "model_identity",
            "raw_text",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        if (
            self.operational_metadata is not None
            and not isinstance(
                self.operational_metadata,
                GroundedProviderOperationalMetadata,
            )
        ):
            raise TypeError(
                "operational_metadata must be a "
                "GroundedProviderOperationalMetadata or None"
            )

        if self.usage is not None and not isinstance(
            self.usage,
            GroundedProviderUsage,
        ):
            raise TypeError(
                "usage must be a GroundedProviderUsage or None"
            )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "request_id": self.request_id,
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "raw_text": self.raw_text,
        }
        if self.operational_metadata is not None:
            data["operational_metadata"] = (
                self.operational_metadata.to_dict()
            )
        if self.usage is not None:
            data["usage"] = self.usage.to_dict()
        return data


class GroundedModelAdapter(ABC):
    """Provider-neutral generation interface."""

    @abstractmethod
    def generate(
        self,
        prompt: GroundedPromptInput,
    ) -> GroundedModelResponse:
        """Generate one raw response for one grounded prompt input."""


class StaticGroundedModelAdapter(GroundedModelAdapter):
    """Deterministic in-memory reference adapter for contract tests."""

    def __init__(
        self,
        *,
        provider_identity: str,
        model_identity: str,
        raw_text: str,
    ) -> None:
        self._provider_identity = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
        )
        self._model_identity = normalize_required_text(
            model_identity,
            field_name="model_identity",
        )
        self._raw_text = normalize_required_text(
            raw_text,
            field_name="raw_text",
        )

    def generate(
        self,
        prompt: GroundedPromptInput,
    ) -> GroundedModelResponse:
        if not isinstance(prompt, GroundedPromptInput):
            raise TypeError(
                "prompt must be a GroundedPromptInput"
            )

        return GroundedModelResponse(
            request_id=prompt.request_id,
            provider_identity=self._provider_identity,
            model_identity=self._model_identity,
            raw_text=self._raw_text,
        )
