"""
Canonical immutable contracts for evidence-grounded AI outputs.

This module defines result shape only. It performs no model invocation,
prompt construction, network I/O, or autonomous decision making.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelope,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedKnowledgeCitation:
    """Exact citation from an AI claim to one Knowledge envelope."""

    knowledge_identity: str
    statement: str
    provenance_status: str

    def __post_init__(self) -> None:
        for field_name in (
            "knowledge_identity",
            "statement",
            "provenance_status",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

    @classmethod
    def from_envelope(
        cls,
        envelope: KnowledgeRecordEnvelope,
    ) -> "GroundedKnowledgeCitation":
        if not isinstance(
            envelope,
            KnowledgeRecordEnvelope,
        ):
            raise TypeError(
                "envelope must be a KnowledgeRecordEnvelope"
            )

        return cls(
            knowledge_identity=envelope.identity_key,
            statement=envelope.record.statement,
            provenance_status=envelope.provenance.status,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "knowledge_identity": self.knowledge_identity,
            "statement": self.statement,
            "provenance_status": self.provenance_status,
        }


@dataclass(frozen=True, slots=True)
class GroundedAIClaim:
    """One descriptive AI-facing claim with explicit Knowledge citations."""

    text: str
    citations: tuple[GroundedKnowledgeCitation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            normalize_required_text(
                self.text,
                field_name="text",
            ),
        )

        if not isinstance(
            self.citations,
            tuple,
        ):
            raise TypeError(
                "citations must be a tuple"
            )
        if not self.citations:
            raise ValueError(
                "citations must contain at least one citation"
            )
        if any(
            not isinstance(
                item,
                GroundedKnowledgeCitation,
            )
            for item in self.citations
        ):
            raise TypeError(
                "citations must contain only GroundedKnowledgeCitation values"
            )

        identities = tuple(
            item.knowledge_identity
            for item in self.citations
        )
        if len(set(identities)) != len(identities):
            raise ValueError(
                "citations must have unique knowledge identities"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "citations": [
                item.to_dict()
                for item in self.citations
            ],
        }


@dataclass(frozen=True, slots=True)
class GroundedAIAnswer:
    """
    Canonical versioned answer contract for the Evidence-Grounded AI layer.

    V1 is descriptive only. It deliberately carries no confidence,
    prediction, recommendation-effectiveness, or causal semantics.
    """

    answer_id: str
    protocol_identity: str
    claims: tuple[GroundedAIClaim, ...]

    PROTOCOL_IDENTITY = "EVIDENCE_GROUNDED_ANSWER@1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "answer_id",
            normalize_required_text(
                self.answer_id,
                field_name="answer_id",
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

        if (
            self.protocol_identity
            != self.PROTOCOL_IDENTITY
        ):
            raise ValueError(
                "protocol_identity must be EVIDENCE_GROUNDED_ANSWER@1"
            )

        if not isinstance(
            self.claims,
            tuple,
        ):
            raise TypeError(
                "claims must be a tuple"
            )
        if not self.claims:
            raise ValueError(
                "claims must contain at least one claim"
            )
        if any(
            not isinstance(
                item,
                GroundedAIClaim,
            )
            for item in self.claims
        ):
            raise TypeError(
                "claims must contain only GroundedAIClaim values"
            )

    @property
    def cited_knowledge_identities(
        self,
    ) -> tuple[str, ...]:
        identities = {
            citation.knowledge_identity
            for claim in self.claims
            for citation in claim.citations
        }
        return tuple(
            sorted(
                identities
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "protocol_identity": self.protocol_identity,
            "claims": [
                item.to_dict()
                for item in self.claims
            ],
            "cited_knowledge_identities": list(
                self.cited_knowledge_identities
            ),
        }
