"""
Provider-independent model adapter contract for Evidence-Grounded AI.

This module defines the boundary between canonical prompt input and an external
text-generation provider. It imports no provider SDK and performs no network I/O.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from investment_terminal.ai.prompt_input import (
    GroundedPromptInput,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedModelResponse:
    """Immutable raw generation result correlated to one grounded prompt."""

    request_id: str
    provider_identity: str
    model_identity: str
    raw_text: str

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "raw_text": self.raw_text,
        }


class GroundedModelAdapter(ABC):
    """Provider-neutral generation interface."""

    @abstractmethod
    def generate(
        self,
        prompt: GroundedPromptInput,
    ) -> GroundedModelResponse:
        """Generate one raw response for one grounded prompt input."""


class StaticGroundedModelAdapter(
    GroundedModelAdapter
):
    """
    Deterministic in-memory reference adapter for contract tests.

    This is not a real model integration.
    """

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
        if not isinstance(
            prompt,
            GroundedPromptInput,
        ):
            raise TypeError(
                "prompt must be a GroundedPromptInput"
            )

        return GroundedModelResponse(
            request_id=prompt.request_id,
            provider_identity=self._provider_identity,
            model_identity=self._model_identity,
            raw_text=self._raw_text,
        )
