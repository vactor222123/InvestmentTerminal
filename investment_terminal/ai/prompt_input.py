"""
Provider-neutral prompt input contract for Evidence-Grounded AI.

This module serializes an already-selected Knowledge context. It performs no
retrieval, re-ranking, prompt heuristics, model invocation, or network I/O.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.ai.context_selection import (
    GroundedContextSelection,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedPromptContextItem:
    """Immutable prompt-facing projection of one selected Knowledge envelope."""

    knowledge_identity: str
    subject_key: str
    statement: str
    provenance_status: str
    valid_from: str
    valid_to: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "knowledge_identity",
            "subject_key",
            "statement",
            "provenance_status",
            "valid_from",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        if self.valid_to is not None:
            object.__setattr__(
                self,
                "valid_to",
                normalize_required_text(
                    self.valid_to,
                    field_name="valid_to",
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_identity": self.knowledge_identity,
            "subject_key": self.subject_key,
            "statement": self.statement,
            "provenance_status": self.provenance_status,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }


@dataclass(frozen=True, slots=True)
class GroundedPromptInput:
    """Canonical provider-neutral model-input payload."""

    request_id: str
    protocol_identity: str
    user_query: str
    context: tuple[GroundedPromptContextItem, ...]

    PROTOCOL_IDENTITY: ClassVar[str] = "EVIDENCE_GROUNDED_PROMPT@1"

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
            "protocol_identity",
            normalize_required_text(
                self.protocol_identity,
                field_name="protocol_identity",
                uppercase=True,
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

        if (
            self.protocol_identity
            != self.PROTOCOL_IDENTITY
        ):
            raise ValueError(
                "protocol_identity must be EVIDENCE_GROUNDED_PROMPT@1"
            )

        if not isinstance(
            self.context,
            tuple,
        ):
            raise TypeError(
                "context must be a tuple"
            )
        if any(
            not isinstance(
                item,
                GroundedPromptContextItem,
            )
            for item in self.context
        ):
            raise TypeError(
                "context must contain only GroundedPromptContextItem values"
            )

        identities = tuple(
            item.knowledge_identity
            for item in self.context
        )
        if len(
            set(
                identities
            )
        ) != len(identities):
            raise ValueError(
                "context items must have unique knowledge identities"
            )

    @property
    def context_identities(self) -> tuple[str, ...]:
        return tuple(
            item.knowledge_identity
            for item in self.context
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "protocol_identity": self.protocol_identity,
            "user_query": self.user_query,
            "context": [
                item.to_dict()
                for item in self.context
            ],
            "context_identities": list(
                self.context_identities
            ),
        }


class GroundedPromptInputService:
    """Build prompt input from an already-deterministic context selection."""

    def build(
        self,
        *,
        request_id: str,
        user_query: str,
        selection: GroundedContextSelection,
    ) -> GroundedPromptInput:
        if not isinstance(
            selection,
            GroundedContextSelection,
        ):
            raise TypeError(
                "selection must be a GroundedContextSelection"
            )

        context = tuple(
            GroundedPromptContextItem(
                knowledge_identity=item.identity_key,
                subject_key=item.record.subject_key,
                statement=item.record.statement,
                provenance_status=item.provenance.status,
                valid_from=item.record.valid_from.isoformat(),
                valid_to=(
                    None
                    if item.record.valid_to is None
                    else item.record.valid_to.isoformat()
                ),
            )
            for item in selection.selected
        )

        return GroundedPromptInput(
            request_id=request_id,
            protocol_identity=GroundedPromptInput.PROTOCOL_IDENTITY,
            user_query=user_query,
            context=context,
        )
