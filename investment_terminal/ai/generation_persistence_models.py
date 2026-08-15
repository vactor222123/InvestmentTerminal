"""Immutable persistence model for admissible grounded generations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class FrozenJSONDict(dict[str, Any]):
    """JSON-compatible dictionary that rejects every mutation operation."""

    @staticmethod
    def _immutable(*args, **kwargs):
        raise TypeError("frozen JSON object is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def _freeze_json(
    value: Any,
    *,
    field_name: str,
) -> Any:
    if isinstance(value, dict):
        return FrozenJSONDict(
            {
                key: _freeze_json(
                    item,
                    field_name=field_name,
                )
                for key, item in value.items()
            }
        )
    if isinstance(value, list):
        return tuple(
            _freeze_json(
                item,
                field_name=field_name,
            )
            for item in value
        )
    if isinstance(value, tuple):
        return tuple(
            _freeze_json(
                item,
                field_name=field_name,
            )
            for item in value
        )
    if value is None or isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value
    raise TypeError(
        f"{field_name} must contain JSON-compatible values"
    )


def _thaw_json(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _thaw_json(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return [
            _thaw_json(item)
            for item in value
        ]
    return value


@dataclass(frozen=True, slots=True)
class PersistedGroundedGeneration:
    """
    Durable projection of one ADMISSIBLE grounded generation.

    This is generated evidence, not canonical History or Knowledge.
    Nested generation/trace JSON is defensively deep-frozen.
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

        frozen_generation = _freeze_json(
            self.generation,
            field_name="generation",
        )
        frozen_trace = _freeze_json(
            self.trace,
            field_name="trace",
        )

        object.__setattr__(
            self,
            "generation",
            frozen_generation,
        )
        object.__setattr__(
            self,
            "trace",
            frozen_trace,
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
            "generation": _thaw_json(
                self.generation
            ),
            "trace": _thaw_json(
                self.trace
            ),
        }
