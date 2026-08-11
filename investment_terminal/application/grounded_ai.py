"""
Provider-neutral application boundary for grounded AI requests.

This module defines stable application request/result contracts only.
It owns no CLI parsing, HTTP framework integration, database construction,
provider composition, credential lookup, network I/O, or persistence.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedAIApplicationRequest:
    """One application-level grounded AI request."""

    request_id: str
    user_query: str
    subject_keys: tuple[str, ...] = ()
    max_items: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            normalize_required_text(
                self.request_id,
                field_name="request_id",
            ),
        )
        object.__setattr__(
            self,
            "user_query",
            normalize_required_text(
                self.user_query,
                field_name="user_query",
            ),
        )

        if not isinstance(
            self.subject_keys,
            tuple,
        ):
            raise TypeError(
                "subject_keys must be a tuple"
            )

        normalized_subjects = tuple(
            normalize_required_text(
                subject,
                field_name="subject_key",
            )
            for subject in self.subject_keys
        )
        if len(set(normalized_subjects)) != len(
            normalized_subjects
        ):
            raise ValueError(
                "subject_keys must be unique"
            )
        object.__setattr__(
            self,
            "subject_keys",
            normalized_subjects,
        )

        if self.max_items is not None and (
            isinstance(self.max_items, bool)
            or not isinstance(self.max_items, int)
            or self.max_items <= 0
        ):
            raise ValueError(
                "max_items must be a positive integer or None"
            )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "request_id": self.request_id,
            "user_query": self.user_query,
            "subject_keys": list(
                self.subject_keys
            ),
        }
        if self.max_items is not None:
            data["max_items"] = self.max_items
        return data


@dataclass(frozen=True, slots=True)
class GroundedAIApplicationResult:
    """
    Safe application result.

    generation and trace are already-projected dictionaries produced by lower
    layers. The application boundary never exposes credentials, transport
    requests, raw provider headers, or provider-specific client objects.
    """

    generation: dict[str, Any]
    trace: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(
            self.generation,
            dict,
        ):
            raise TypeError(
                "generation must be a dictionary"
            )
        if not isinstance(
            self.trace,
            dict,
        ):
            raise TypeError(
                "trace must be a dictionary"
            )

        generation_request_id = self._generation_request_id()
        trace_request_id = self.trace.get(
            "request_id"
        )

        if (
            not isinstance(trace_request_id, str)
            or not trace_request_id.strip()
        ):
            raise ValueError(
                "trace must contain a non-empty request_id"
            )

        if generation_request_id != trace_request_id:
            raise ValueError(
                "generation and trace request_id must match"
            )

    def _generation_request_id(self) -> str:
        prompt = self.generation.get(
            "prompt"
        )
        if not isinstance(prompt, dict):
            raise ValueError(
                "generation must contain prompt"
            )

        request_id = prompt.get(
            "request_id"
        )
        if (
            not isinstance(request_id, str)
            or not request_id.strip()
        ):
            raise ValueError(
                "generation prompt must contain a non-empty request_id"
            )
        return request_id

    @property
    def request_id(self) -> str:
        return self._generation_request_id()

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "trace": self.trace,
        }


class GroundedAIApplicationService(ABC):
    """
    Stable application use-case boundary.

    Concrete implementations may compose Knowledge, grounded generation,
    governance, pricing, budgets, and provider execution, but callers depend
    only on this request/result contract.
    """

    @abstractmethod
    def execute(
        self,
        request: GroundedAIApplicationRequest,
    ) -> GroundedAIApplicationResult:
        """Execute one grounded AI application request."""
