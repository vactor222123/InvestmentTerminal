"""
Deterministic orchestration for Evidence-Grounded AI.

This service composes existing selection, prompt, adapter, parser, and
grounding validation boundaries. It introduces no new ranking, parsing,
grounding, or provider semantics.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from investment_terminal.ai.context_selection import (
    GroundedContextSelection,
    GroundedContextSelectionPolicy,
    GroundedContextSelectionService,
)
from investment_terminal.ai.model_adapter import (
    GroundedModelAdapter,
    GroundedModelResponse,
)
from investment_terminal.ai.models import (
    GroundedAIAnswer,
)
from investment_terminal.ai.prompt_input import (
    GroundedPromptInput,
    GroundedPromptInputService,
)
from investment_terminal.ai.response_parser import (
    GroundedModelParseResult,
    GroundedModelResponseParser,
)
from investment_terminal.ai.validation import (
    GroundingValidationAssessment,
    GroundingValidationService,
)
from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelope,
)


@dataclass(frozen=True, slots=True)
class GroundedGenerationResult:
    """Immutable end-to-end result for one grounded generation request."""

    selection: GroundedContextSelection
    prompt: GroundedPromptInput
    response: GroundedModelResponse
    parsed: GroundedModelParseResult
    validation: GroundingValidationAssessment
    answer: GroundedAIAnswer

    def __post_init__(self) -> None:
        if self.prompt.request_id != self.response.request_id:
            raise ValueError(
                "prompt and response request_id must match"
            )
        if self.response.request_id != self.parsed.request_id:
            raise ValueError(
                "response and parsed request_id must match"
            )
        if self.parsed.answer is not self.answer:
            raise ValueError(
                "answer must be the parsed candidate answer"
            )
        if self.validation.status != "ADMISSIBLE":
            raise ValueError(
                "final generation result requires ADMISSIBLE grounding"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection": self.selection.to_dict(),
            "prompt": self.prompt.to_dict(),
            "response": self.response.to_dict(),
            "parsed": self.parsed.to_dict(),
            "validation": self.validation.to_dict(),
            "answer": self.answer.to_dict(),
        }


class GroundedGenerationService:
    """Compose grounded AI boundaries into one fail-closed workflow."""

    def __init__(
        self,
        *,
        adapter: GroundedModelAdapter,
        selection_service: GroundedContextSelectionService | None = None,
        prompt_service: GroundedPromptInputService | None = None,
        parser: GroundedModelResponseParser | None = None,
        validation_service: GroundingValidationService | None = None,
    ) -> None:
        if not isinstance(
            adapter,
            GroundedModelAdapter,
        ):
            raise TypeError(
                "adapter must be a GroundedModelAdapter"
            )

        self._adapter = adapter
        self._selection_service = (
            selection_service
            if selection_service is not None
            else GroundedContextSelectionService()
        )
        self._prompt_service = (
            prompt_service
            if prompt_service is not None
            else GroundedPromptInputService()
        )
        self._parser = (
            parser
            if parser is not None
            else GroundedModelResponseParser()
        )
        self._validation_service = (
            validation_service
            if validation_service is not None
            else GroundingValidationService()
        )

    def generate(
        self,
        *,
        request_id: str,
        user_query: str,
        knowledge: Iterable[KnowledgeRecordEnvelope],
        policy: GroundedContextSelectionPolicy | None = None,
    ) -> GroundedGenerationResult:
        source = tuple(
            knowledge
        )

        selection = self._selection_service.select(
            source,
            policy=policy,
        )

        prompt = self._prompt_service.build(
            request_id=request_id,
            user_query=user_query,
            selection=selection,
        )

        response = self._adapter.generate(
            prompt
        )

        if response.request_id != prompt.request_id:
            raise ValueError(
                "model response request_id does not match prompt request_id"
            )

        parsed = self._parser.parse(
            response
        )

        validation = self._validation_service.validate_answer(
            parsed.answer,
            knowledge=selection.selected,
        )

        answer = self._validation_service.require_admissible(
            parsed.answer,
            knowledge=selection.selected,
        )

        return GroundedGenerationResult(
            selection=selection,
            prompt=prompt,
            response=response,
            parsed=parsed,
            validation=validation,
            answer=answer,
        )
