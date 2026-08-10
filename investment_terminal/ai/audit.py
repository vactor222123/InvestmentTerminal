"""
Deterministic audit/trace representation for grounded generation.

The trace is derived from a completed GroundedGenerationResult. It performs no
persistence, model calls, parsing, or re-validation.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.ai.orchestration import (
    GroundedGenerationResult,
)


@dataclass(frozen=True, slots=True)
class GroundedGenerationTrace:
    """Compact immutable lifecycle trace for one successful generation."""

    request_id: str
    prompt_protocol_identity: str
    answer_protocol_identity: str
    provider_identity: str
    model_identity: str
    selected_knowledge_identities: tuple[str, ...]
    cited_knowledge_identities: tuple[str, ...]
    claim_count: int
    citation_count: int
    validation_status: str
    provider_attempt_count: int | None = None
    provider_retry_count: int | None = None
    provider_transport_status_code: int | None = None
    provider_transport_outcome: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "prompt_protocol_identity",
            "answer_protocol_identity",
            "provider_identity",
            "model_identity",
            "validation_status",
        ):
            value = getattr(
                self,
                field_name,
            )
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        for field_name in (
            "selected_knowledge_identities",
            "cited_knowledge_identities",
        ):
            value = getattr(
                self,
                field_name,
            )
            if not isinstance(value, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )
            if any(
                not isinstance(item, str)
                or not item.strip()
                for item in value
            ):
                raise ValueError(
                    f"{field_name} must contain non-empty strings"
                )

        for field_name in (
            "claim_count",
            "citation_count",
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

        if self.validation_status != "ADMISSIBLE":
            raise ValueError(
                "successful generation trace requires ADMISSIBLE validation"
            )

        selected = set(
            self.selected_knowledge_identities
        )
        cited = set(
            self.cited_knowledge_identities
        )
        if not cited.issubset(
            selected
        ):
            raise ValueError(
                "cited Knowledge identities must be a subset of selected context"
            )

        operational_values = (
            self.provider_attempt_count,
            self.provider_retry_count,
            self.provider_transport_status_code,
            self.provider_transport_outcome,
        )
        if any(
            value is not None
            for value in operational_values
        ) and not all(
            value is not None
            for value in operational_values
        ):
            raise ValueError(
                "provider operational trace fields must be all present or all absent"
            )

        if self.provider_attempt_count is not None:
            assert self.provider_retry_count is not None
            assert self.provider_transport_status_code is not None
            assert self.provider_transport_outcome is not None

            if self.provider_attempt_count < 1:
                raise ValueError(
                    "provider_attempt_count must be at least 1"
                )
            if (
                self.provider_retry_count
                != self.provider_attempt_count - 1
            ):
                raise ValueError(
                    "provider_retry_count must equal provider_attempt_count - 1"
                )
            if not 100 <= self.provider_transport_status_code <= 599:
                raise ValueError(
                    "provider_transport_status_code must be an HTTP status code"
                )
            if self.provider_transport_outcome != "SUCCESS":
                raise ValueError(
                    "successful generation trace requires provider transport SUCCESS"
                )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "request_id": self.request_id,
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
            "claim_count": self.claim_count,
            "citation_count": self.citation_count,
            "validation_status": self.validation_status,
        }
        if self.provider_attempt_count is not None:
            data["provider_operation"] = {
                "attempt_count": self.provider_attempt_count,
                "retry_count": self.provider_retry_count,
                "transport_status_code": self.provider_transport_status_code,
                "transport_outcome": self.provider_transport_outcome,
            }
        return data


class GroundedGenerationTraceService:
    """Build a deterministic compact trace from a completed generation."""

    def build(
        self,
        result: GroundedGenerationResult,
    ) -> GroundedGenerationTrace:
        if not isinstance(
            result,
            GroundedGenerationResult,
        ):
            raise TypeError(
                "result must be a GroundedGenerationResult"
            )

        citation_count = sum(
            len(claim.citations)
            for claim in result.answer.claims
        )

        operational = result.response.operational_metadata

        return GroundedGenerationTrace(
            request_id=result.prompt.request_id,
            prompt_protocol_identity=result.prompt.protocol_identity,
            answer_protocol_identity=result.answer.protocol_identity,
            provider_identity=result.response.provider_identity,
            model_identity=result.response.model_identity,
            selected_knowledge_identities=(
                result.selection.selected_identities
            ),
            cited_knowledge_identities=(
                result.answer.cited_knowledge_identities
            ),
            claim_count=len(
                result.answer.claims
            ),
            citation_count=citation_count,
            validation_status=result.validation.status,
            provider_attempt_count=(
                None
                if operational is None
                else operational.attempt_count
            ),
            provider_retry_count=(
                None
                if operational is None
                else operational.retry_count
            ),
            provider_transport_status_code=(
                None
                if operational is None
                else operational.transport_status_code
            ),
            provider_transport_outcome=(
                None
                if operational is None
                else operational.transport_outcome
            ),
        )
