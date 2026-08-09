"""
Grounding validation policy for Evidence-Grounded AI v1.

The policy validates exact Knowledge citation lineage and provenance
admissibility. It does not attempt semantic entailment, truth scoring,
prediction, or model-based claim verification.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Iterable

from investment_terminal.ai.models import (
    GroundedAIAnswer,
    GroundedAIClaim,
    GroundedKnowledgeCitation,
)
from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelope,
)


@dataclass(frozen=True, slots=True)
class GroundingValidationAssessment:
    """Immutable validation result for one claim or answer."""

    status: str
    claim_count: int
    citation_count: int
    resolved_citation_count: int
    inadmissible_citation_count: int
    warnings: tuple[str, ...]

    ADMISSIBLE: ClassVar[str] = "ADMISSIBLE"
    REJECTED: ClassVar[str] = "REJECTED"

    def __post_init__(self) -> None:
        if self.status not in (
            self.ADMISSIBLE,
            self.REJECTED,
        ):
            raise ValueError(
                "status must be ADMISSIBLE or REJECTED"
            )

        for field_name in (
            "claim_count",
            "citation_count",
            "resolved_citation_count",
            "inadmissible_citation_count",
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

        if self.resolved_citation_count > self.citation_count:
            raise ValueError(
                "resolved_citation_count must not exceed citation_count"
            )
        if self.inadmissible_citation_count > self.citation_count:
            raise ValueError(
                "inadmissible_citation_count must not exceed citation_count"
            )

        if not isinstance(self.warnings, tuple):
            raise TypeError(
                "warnings must be a tuple"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "claim_count": self.claim_count,
            "citation_count": self.citation_count,
            "resolved_citation_count": self.resolved_citation_count,
            "inadmissible_citation_count": self.inadmissible_citation_count,
            "warnings": list(self.warnings),
        }


class GroundingValidationService:
    """
    Validate exact citation lineage against supplied Knowledge envelopes.

    V1 admissibility rule:
    - citation must resolve to an exact Knowledge identity;
    - citation statement must exactly match the Knowledge record statement;
    - citation provenance_status must exactly match the envelope assessment;
    - envelope provenance must be COMPLETE.

    PARTIAL provenance remains traceable evidence, but is not sufficient as
    grounding for EVIDENCE_GROUNDED_ANSWER@1.
    """

    ADMISSIBLE_PROVENANCE = (
        "COMPLETE",
    )

    WARNING_PARTIAL = (
        "PARTIAL Knowledge provenance is traceable but is not admissible "
        "grounding for EVIDENCE_GROUNDED_ANSWER@1"
    )

    def validate_answer(
        self,
        answer: GroundedAIAnswer,
        *,
        knowledge: Iterable[KnowledgeRecordEnvelope],
    ) -> GroundingValidationAssessment:
        if not isinstance(
            answer,
            GroundedAIAnswer,
        ):
            raise TypeError(
                "answer must be a GroundedAIAnswer"
            )

        registry = self._registry(
            knowledge
        )

        citation_count = 0
        resolved_count = 0
        inadmissible_count = 0
        warnings: list[str] = []

        for claim in answer.claims:
            result = self._validate_claim(
                claim,
                registry=registry,
            )
            citation_count += result[
                "citation_count"
            ]
            resolved_count += result[
                "resolved_count"
            ]
            inadmissible_count += result[
                "inadmissible_count"
            ]
            warnings.extend(
                result["warnings"]
            )

        status = (
            GroundingValidationAssessment.ADMISSIBLE
            if (
                resolved_count == citation_count
                and inadmissible_count == 0
            )
            else GroundingValidationAssessment.REJECTED
        )

        return GroundingValidationAssessment(
            status=status,
            claim_count=len(answer.claims),
            citation_count=citation_count,
            resolved_citation_count=resolved_count,
            inadmissible_citation_count=inadmissible_count,
            warnings=tuple(
                dict.fromkeys(
                    warnings
                )
            ),
        )

    def require_admissible(
        self,
        answer: GroundedAIAnswer,
        *,
        knowledge: Iterable[KnowledgeRecordEnvelope],
    ) -> GroundedAIAnswer:
        assessment = self.validate_answer(
            answer,
            knowledge=knowledge,
        )
        if (
            assessment.status
            != GroundingValidationAssessment.ADMISSIBLE
        ):
            details = (
                "; ".join(
                    assessment.warnings
                )
                or "grounding validation failed"
            )
            raise ValueError(
                f"Grounded AI answer is not admissible: {details}"
            )
        return answer

    def _validate_claim(
        self,
        claim: GroundedAIClaim,
        *,
        registry: dict[str, KnowledgeRecordEnvelope],
    ) -> dict[str, Any]:
        if not isinstance(
            claim,
            GroundedAIClaim,
        ):
            raise TypeError(
                "claim must be a GroundedAIClaim"
            )

        resolved = 0
        inadmissible = 0
        warnings: list[str] = []

        for citation in claim.citations:
            envelope = registry.get(
                citation.knowledge_identity
            )
            if envelope is None:
                warnings.append(
                    "Citation does not resolve to supplied Knowledge: "
                    f"{citation.knowledge_identity}"
                )
                continue

            resolved += 1

            if (
                citation.statement
                != envelope.record.statement
            ):
                inadmissible += 1
                warnings.append(
                    "Citation statement does not match Knowledge record: "
                    f"{citation.knowledge_identity}"
                )

            if (
                citation.provenance_status
                != envelope.provenance.status
            ):
                inadmissible += 1
                warnings.append(
                    "Citation provenance_status does not match Knowledge "
                    f"envelope: {citation.knowledge_identity}"
                )

            if (
                envelope.provenance.status
                not in self.ADMISSIBLE_PROVENANCE
            ):
                inadmissible += 1
                warnings.append(
                    self.WARNING_PARTIAL
                )

        return {
            "citation_count": len(
                claim.citations
            ),
            "resolved_count": resolved,
            "inadmissible_count": inadmissible,
            "warnings": warnings,
        }

    @staticmethod
    def _registry(
        knowledge: Iterable[KnowledgeRecordEnvelope],
    ) -> dict[str, KnowledgeRecordEnvelope]:
        materialized = tuple(
            knowledge
        )

        if any(
            not isinstance(
                item,
                KnowledgeRecordEnvelope,
            )
            for item in materialized
        ):
            raise TypeError(
                "knowledge must contain only KnowledgeRecordEnvelope values"
            )

        registry: dict[
            str,
            KnowledgeRecordEnvelope,
        ] = {}
        for item in materialized:
            if item.identity_key in registry:
                raise ValueError(
                    "knowledge envelopes must have unique identities"
                )
            registry[
                item.identity_key
            ] = item

        return registry
