from dataclasses import dataclass
from typing import Any

from investment_terminal.knowledge.models import KnowledgeRecord


@dataclass(frozen=True, slots=True)
class KnowledgeTemporalComparison:
    earlier_identity: str
    later_identity: str
    statement_changed: bool
    status_changed: bool
    validity_changed: bool
    evidence_added: tuple[str, ...]
    evidence_removed: tuple[str, ...]

    @property
    def evidence_changed(self) -> bool:
        return bool(
            self.evidence_added
            or self.evidence_removed
        )

    @property
    def any_change(self) -> bool:
        return any(
            (
                self.statement_changed,
                self.status_changed,
                self.validity_changed,
                self.evidence_changed,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "earlier_identity": self.earlier_identity,
            "later_identity": self.later_identity,
            "statement_changed": self.statement_changed,
            "status_changed": self.status_changed,
            "validity_changed": self.validity_changed,
            "evidence_added": list(self.evidence_added),
            "evidence_removed": list(self.evidence_removed),
            "evidence_changed": self.evidence_changed,
            "any_change": self.any_change,
        }


class KnowledgeTemporalComparisonService:
    """Compare two versions of the same knowledge identity deterministically."""

    def compare(
        self,
        first: KnowledgeRecord,
        second: KnowledgeRecord,
    ) -> KnowledgeTemporalComparison:
        if not isinstance(first, KnowledgeRecord):
            raise TypeError("first must be a KnowledgeRecord")
        if not isinstance(second, KnowledgeRecord):
            raise TypeError("second must be a KnowledgeRecord")

        if first.knowledge_id != second.knowledge_id:
            raise ValueError(
                "Knowledge records must share the same knowledge_id"
            )

        if first.identity_key == second.identity_key:
            raise ValueError(
                "Knowledge records must have different identities"
            )

        earlier, later = sorted(
            (first, second),
            key=lambda item: (
                item.generated_at,
                item.version,
            ),
        )

        earlier_evidence = {
            item.identity_key
            for item in earlier.evidence
        }
        later_evidence = {
            item.identity_key
            for item in later.evidence
        }

        return KnowledgeTemporalComparison(
            earlier_identity=earlier.identity_key,
            later_identity=later.identity_key,
            statement_changed=(
                earlier.statement
                != later.statement
            ),
            status_changed=(
                earlier.status
                != later.status
            ),
            validity_changed=(
                earlier.valid_from
                != later.valid_from
                or earlier.valid_to
                != later.valid_to
            ),
            evidence_added=tuple(
                sorted(
                    later_evidence
                    - earlier_evidence
                )
            ),
            evidence_removed=tuple(
                sorted(
                    earlier_evidence
                    - later_evidence
                )
            ),
        )
