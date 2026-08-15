"""Immutable persistence model for admissible grounded generations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class PersistedGroundedGeneration:
    """
    Durable projection of one ADMISSIBLE grounded generation.

    This is generated evidence, not canonical History or Knowledge.
    """

    request_id: str
    generated_at: datetime
    prompt_protocol_identity: str
    answer_protocol_identity: str
    provider_identity: str
    model_identity: str
    selected_knowledge_identities: tuple[str, ...]
    cited_knowledge_identities: tuple[str, ...]
    generation: dict[str, Any]
    trace: dict[str, Any]

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "prompt_protocol_identity",
            "answer_protocol_identity",
            "provider_identity",
            "model_identity",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        validate_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )

        for field_name in (
            "selected_knowledge_identities",
            "cited_knowledge_identities",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )
            normalized = tuple(
                normalize_required_text(
                    identity,
                    field_name=field_name,
                )
                for identity in value
            )
            if len(set(normalized)) != len(normalized):
                raise ValueError(
                    f"{field_name} must contain unique identities"
                )
            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        if not set(
            self.cited_knowledge_identities
        ).issubset(
            set(self.selected_knowledge_identities)
        ):
            raise ValueError(
                "cited Knowledge identities must be a subset "
                "of selected Knowledge identities"
            )

        if not isinstance(self.generation, dict):
            raise TypeError(
                "generation must be a dictionary"
            )
        if not isinstance(self.trace, dict):
            raise TypeError(
                "trace must be a dictionary"
            )

        prompt = self.generation.get("prompt")
        if not isinstance(prompt, dict):
            raise ValueError(
                "generation must contain prompt"
            )
        if prompt.get("request_id") != self.request_id:
            raise ValueError(
                "generation request_id must match persisted request_id"
            )

        if self.trace.get("request_id") != self.request_id:
            raise ValueError(
                "trace request_id must match persisted request_id"
            )
        if self.trace.get("validation_status") != "ADMISSIBLE":
            raise ValueError(
                "only ADMISSIBLE grounded generations may be persisted"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "generated_at": self.generated_at.isoformat(),
            "prompt_protocol_identity": self.prompt_protocol_identity,
            "answer_protocol_identity": self.answer_protocol_identity,
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "selected_knowledge_identities": list(
                self.selected_knowledge_identities
            ),
            "cited_knowledge_identities": list(
                self.cited_knowledge_identities
            ),
            "generation": self.generation,
            "trace": self.trace,
        }
