"""Deterministic projection of admissible grounded results for persistence."""

from datetime import datetime
from typing import Any

from investment_terminal.ai.audit import (
    GroundedGenerationTrace,
)
from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.orchestration import (
    GroundedGenerationResult,
)
from investment_terminal.utils.validation import validate_aware_datetime


class GroundedGenerationPersistenceProjectionService:
    """
    Project an already-admissible generation and its exact trace.

    This service performs no provider execution, grounding, persistence,
    clock lookup, or authority promotion.
    """

    def project(
        self,
        *,
        result: GroundedGenerationResult,
        trace: GroundedGenerationTrace,
        generated_at: datetime,
        trace_data: dict[str, Any] | None = None,
    ) -> PersistedGroundedGeneration:
        if not isinstance(
            result,
            GroundedGenerationResult,
        ):
            raise TypeError(
                "result must be a GroundedGenerationResult"
            )
        if not isinstance(
            trace,
            GroundedGenerationTrace,
        ):
            raise TypeError(
                "trace must be a GroundedGenerationTrace"
            )
        validate_aware_datetime(
            generated_at,
            field_name="generated_at",
        )

        if result.prompt.request_id != trace.request_id:
            raise ValueError(
                "generation and trace request_id must match"
            )
        if (
            result.prompt.protocol_identity
            != trace.prompt_protocol_identity
        ):
            raise ValueError(
                "generation and trace prompt protocol must match"
            )
        if (
            result.answer.protocol_identity
            != trace.answer_protocol_identity
        ):
            raise ValueError(
                "generation and trace answer protocol must match"
            )
        if (
            result.response.provider_identity
            != trace.provider_identity
        ):
            raise ValueError(
                "generation and trace provider identity must match"
            )
        if (
            result.response.model_identity
            != trace.model_identity
        ):
            raise ValueError(
                "generation and trace model identity must match"
            )
        if (
            result.selection.selected_identities
            != trace.selected_knowledge_identities
        ):
            raise ValueError(
                "generation and trace selected Knowledge must match"
            )
        if (
            result.answer.cited_knowledge_identities
            != trace.cited_knowledge_identities
        ):
            raise ValueError(
                "generation and trace cited Knowledge must match"
            )

        if trace_data is None:
            projected_trace = trace.to_dict()
        else:
            if not isinstance(trace_data, dict):
                raise TypeError(
                    "trace_data must be a dictionary or None"
                )
            projected_trace = dict(trace_data)
            if projected_trace.get("request_id") != trace.request_id:
                raise ValueError(
                    "trace_data request_id must match trace"
                )
            if (
                projected_trace.get("validation_status")
                != "ADMISSIBLE"
            ):
                raise ValueError(
                    "trace_data must describe ADMISSIBLE grounding"
                )

        return PersistedGroundedGeneration(
            request_id=result.prompt.request_id,
            generated_at=generated_at,
            prompt_protocol_identity=(
                result.prompt.protocol_identity
            ),
            answer_protocol_identity=(
                result.answer.protocol_identity
            ),
            provider_identity=(
                result.response.provider_identity
            ),
            model_identity=result.response.model_identity,
            selected_knowledge_identities=(
                result.selection.selected_identities
            ),
            cited_knowledge_identities=(
                result.answer.cited_knowledge_identities
            ),
            generation=result.to_dict(),
            trace=projected_trace,
        )
