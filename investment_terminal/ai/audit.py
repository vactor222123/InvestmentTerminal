"""
Deterministic audit/trace representation for grounded generation.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from investment_terminal.ai.orchestration import GroundedGenerationResult


@dataclass(frozen=True, slots=True)
class GroundedGenerationTrace:
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
    provider_retry_delay_seconds: tuple[Decimal, ...] = ()
    provider_input_tokens: int | None = None
    provider_output_tokens: int | None = None
    provider_total_tokens: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "prompt_protocol_identity",
            "answer_protocol_identity",
            "provider_identity",
            "model_identity",
            "validation_status",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        for field_name in (
            "selected_knowledge_identities",
            "cited_knowledge_identities",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise TypeError(f"{field_name} must be a tuple")

        for field_name in ("claim_count", "citation_count"):
            value = getattr(self, field_name)
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

        if not set(self.cited_knowledge_identities).issubset(
            set(self.selected_knowledge_identities)
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
        if any(v is not None for v in operational_values) and not all(
            v is not None for v in operational_values
        ):
            raise ValueError(
                "provider operational trace fields must be all present or all absent"
            )

        if not isinstance(
            self.provider_retry_delay_seconds,
            tuple,
        ):
            raise TypeError(
                "provider_retry_delay_seconds must be a tuple"
            )
        if (
            self.provider_retry_delay_seconds
            and self.provider_retry_count is None
        ):
            raise ValueError(
                "provider retry delays require provider operational metadata"
            )
        if (
            self.provider_retry_count is not None
            and len(self.provider_retry_delay_seconds)
            > self.provider_retry_count
        ):
            raise ValueError(
                "provider retry delay count cannot exceed retry count"
            )
        normalized_delays = []
        for value in self.provider_retry_delay_seconds:
            if isinstance(value, bool):
                raise TypeError(
                    "provider retry delays must be Decimal-compatible"
                )
            try:
                parsed = Decimal(str(value))
            except Exception as exc:
                raise TypeError(
                    "provider retry delays must be Decimal-compatible"
                ) from exc
            if not parsed.is_finite() or parsed < 0:
                raise ValueError(
                    "provider retry delays must be finite and non-negative"
                )
            normalized_delays.append(parsed)
        object.__setattr__(
            self,
            "provider_retry_delay_seconds",
            tuple(normalized_delays),
        )

        usage_values = (
            self.provider_input_tokens,
            self.provider_output_tokens,
            self.provider_total_tokens,
        )
        if any(v is not None for v in usage_values) and not all(
            v is not None for v in usage_values
        ):
            raise ValueError(
                "provider usage trace fields must be all present or all absent"
            )

        if self.provider_input_tokens is not None:
            assert self.provider_output_tokens is not None
            assert self.provider_total_tokens is not None
            for field_name in (
                "provider_input_tokens",
                "provider_output_tokens",
                "provider_total_tokens",
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
            if (
                self.provider_total_tokens
                != self.provider_input_tokens + self.provider_output_tokens
            ):
                raise ValueError(
                    "provider_total_tokens must equal input + output"
                )

    def to_dict(self) -> dict[str, Any]:
        data = {
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
            provider_operation = {
                "attempt_count": self.provider_attempt_count,
                "retry_count": self.provider_retry_count,
                "transport_status_code": self.provider_transport_status_code,
                "transport_outcome": self.provider_transport_outcome,
            }
            if self.provider_retry_delay_seconds:
                provider_operation["retry_delay_seconds"] = [
                    str(value)
                    for value in self.provider_retry_delay_seconds
                ]
            data["provider_operation"] = provider_operation
        if self.provider_input_tokens is not None:
            data["provider_usage"] = {
                "input_tokens": self.provider_input_tokens,
                "output_tokens": self.provider_output_tokens,
                "total_tokens": self.provider_total_tokens,
            }
        return data


class GroundedGenerationTraceService:
    def build(
        self,
        result: GroundedGenerationResult,
    ) -> GroundedGenerationTrace:
        if not isinstance(result, GroundedGenerationResult):
            raise TypeError(
                "result must be a GroundedGenerationResult"
            )

        citation_count = sum(
            len(claim.citations)
            for claim in result.answer.claims
        )
        operational = result.response.operational_metadata
        usage = result.response.usage

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
            claim_count=len(result.answer.claims),
            citation_count=citation_count,
            validation_status=result.validation.status,
            provider_attempt_count=(
                None if operational is None else operational.attempt_count
            ),
            provider_retry_count=(
                None if operational is None else operational.retry_count
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
            provider_retry_delay_seconds=(
                ()
                if operational is None
                else operational.retry_delay_seconds
            ),
            provider_input_tokens=(
                None if usage is None else usage.input_tokens
            ),
            provider_output_tokens=(
                None if usage is None else usage.output_tokens
            ),
            provider_total_tokens=(
                None if usage is None else usage.total_tokens
            ),
        )
