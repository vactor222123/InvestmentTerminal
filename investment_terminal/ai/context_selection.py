"""
Deterministic Knowledge context selection for Evidence-Grounded AI.

Selection consumes already-built KnowledgeRecordEnvelope values. It does not
query persistence, construct prompts, call models, or infer relevance.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelope,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedContextSelectionPolicy:
    """
    Explicit v1 context policy.

    subject_keys is an optional allowlist. max_items bounds the selected
    context after deterministic ordering. COMPLETE provenance is required.
    """

    subject_keys: tuple[str, ...] = ()
    max_items: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.subject_keys,
            tuple,
        ):
            raise TypeError(
                "subject_keys must be a tuple"
            )

        normalized = tuple(
            normalize_required_text(
                item,
                field_name="subject_key",
            )
            for item in self.subject_keys
        )
        if len(
            set(
                normalized
            )
        ) != len(normalized):
            raise ValueError(
                "subject_keys must be unique"
            )
        object.__setattr__(
            self,
            "subject_keys",
            normalized,
        )

        if self.max_items is not None:
            if (
                isinstance(self.max_items, bool)
                or not isinstance(
                    self.max_items,
                    int,
                )
                or self.max_items <= 0
            ):
                raise ValueError(
                    "max_items must be a positive integer"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_keys": list(
                self.subject_keys
            ),
            "max_items": self.max_items,
            "required_provenance_status": "COMPLETE",
        }


@dataclass(frozen=True, slots=True)
class GroundedContextSelection:
    """Immutable selected context and accounting."""

    policy: GroundedContextSelectionPolicy
    source_count: int
    selected: tuple[KnowledgeRecordEnvelope, ...]
    excluded_partial_count: int
    excluded_subject_count: int

    def __post_init__(self) -> None:
        if not isinstance(
            self.policy,
            GroundedContextSelectionPolicy,
        ):
            raise TypeError(
                "policy must be a GroundedContextSelectionPolicy"
            )
        if not isinstance(
            self.selected,
            tuple,
        ):
            raise TypeError(
                "selected must be a tuple"
            )
        if any(
            not isinstance(
                item,
                KnowledgeRecordEnvelope,
            )
            for item in self.selected
        ):
            raise TypeError(
                "selected must contain only KnowledgeRecordEnvelope values"
            )

        for field_name in (
            "source_count",
            "excluded_partial_count",
            "excluded_subject_count",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

    @property
    def selected_count(self) -> int:
        return len(
            self.selected
        )

    @property
    def selected_identities(self) -> tuple[str, ...]:
        return tuple(
            item.identity_key
            for item in self.selected
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy.to_dict(),
            "source_count": self.source_count,
            "selected_count": self.selected_count,
            "selected_identities": list(
                self.selected_identities
            ),
            "excluded_partial_count": self.excluded_partial_count,
            "excluded_subject_count": self.excluded_subject_count,
        }


class GroundedContextSelectionService:
    """Apply explicit v1 admissibility and deterministic context ordering."""

    REQUIRED_PROVENANCE_STATUS = "COMPLETE"

    def select(
        self,
        knowledge: Iterable[KnowledgeRecordEnvelope],
        *,
        policy: GroundedContextSelectionPolicy | None = None,
    ) -> GroundedContextSelection:
        active_policy = (
            policy
            if policy is not None
            else GroundedContextSelectionPolicy()
        )
        if not isinstance(
            active_policy,
            GroundedContextSelectionPolicy,
        ):
            raise TypeError(
                "policy must be a GroundedContextSelectionPolicy"
            )

        source = tuple(
            knowledge
        )
        if any(
            not isinstance(
                item,
                KnowledgeRecordEnvelope,
            )
            for item in source
        ):
            raise TypeError(
                "knowledge must contain only KnowledgeRecordEnvelope values"
            )

        identities = tuple(
            item.identity_key
            for item in source
        )
        if len(
            set(
                identities
            )
        ) != len(identities):
            raise ValueError(
                "knowledge envelopes must have unique identities"
            )

        excluded_partial = 0
        excluded_subject = 0
        candidates: list[
            KnowledgeRecordEnvelope
        ] = []

        allowed_subjects = set(
            active_policy.subject_keys
        )

        for item in source:
            if (
                item.provenance.status
                != self.REQUIRED_PROVENANCE_STATUS
            ):
                excluded_partial += 1
                continue

            if (
                allowed_subjects
                and item.record.subject_key
                not in allowed_subjects
            ):
                excluded_subject += 1
                continue

            candidates.append(
                item
            )

        ordered = tuple(
            sorted(
                candidates,
                key=lambda item: (
                    item.record.subject_key,
                    item.record.valid_from,
                    item.record.generated_at,
                    item.record.knowledge_id,
                    item.record.version,
                ),
            )
        )

        if active_policy.max_items is not None:
            ordered = ordered[
                : active_policy.max_items
            ]

        return GroundedContextSelection(
            policy=active_policy,
            source_count=len(source),
            selected=ordered,
            excluded_partial_count=excluded_partial,
            excluded_subject_count=excluded_subject,
        )
