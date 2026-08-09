"""
Deterministic parser for raw model responses.

Parsing converts provider raw JSON text into a structured GroundedAIAnswer.
It does not validate Knowledge resolution or grounding admissibility.
"""

import json
from dataclasses import dataclass
from typing import Any

from investment_terminal.ai.model_adapter import (
    GroundedModelResponse,
)
from investment_terminal.ai.models import (
    GroundedAIAnswer,
    GroundedAIClaim,
    GroundedKnowledgeCitation,
)


@dataclass(frozen=True, slots=True)
class GroundedModelParseResult:
    """Parsed answer correlated to the original model response."""

    request_id: str
    provider_identity: str
    model_identity: str
    answer: GroundedAIAnswer

    def __post_init__(self) -> None:
        if not isinstance(
            self.answer,
            GroundedAIAnswer,
        ):
            raise TypeError(
                "answer must be a GroundedAIAnswer"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "answer": self.answer.to_dict(),
        }


class GroundedModelResponseParser:
    """Parse canonical JSON response text into a candidate grounded answer."""

    TOP_LEVEL_FIELDS = {
        "answer_id",
        "protocol_identity",
        "claims",
    }
    CLAIM_FIELDS = {
        "text",
        "citations",
    }
    CITATION_FIELDS = {
        "knowledge_identity",
        "statement",
        "provenance_status",
    }

    def parse(
        self,
        response: GroundedModelResponse,
    ) -> GroundedModelParseResult:
        if not isinstance(
            response,
            GroundedModelResponse,
        ):
            raise TypeError(
                "response must be a GroundedModelResponse"
            )

        try:
            payload = json.loads(
                response.raw_text
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "model raw_text must be valid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "model JSON must be an object"
            )

        self._require_exact_fields(
            payload,
            expected=self.TOP_LEVEL_FIELDS,
            context="answer",
        )

        claims_payload = payload[
            "claims"
        ]
        if not isinstance(
            claims_payload,
            list,
        ):
            raise ValueError(
                "claims must be a JSON array"
            )

        claims = tuple(
            self._parse_claim(
                item,
                index=index,
            )
            for index, item in enumerate(
                claims_payload
            )
        )

        answer = GroundedAIAnswer(
            answer_id=payload[
                "answer_id"
            ],
            protocol_identity=payload[
                "protocol_identity"
            ],
            claims=claims,
        )

        return GroundedModelParseResult(
            request_id=response.request_id,
            provider_identity=response.provider_identity,
            model_identity=response.model_identity,
            answer=answer,
        )

    def _parse_claim(
        self,
        payload: object,
        *,
        index: int,
    ) -> GroundedAIClaim:
        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                f"claims[{index}] must be a JSON object"
            )

        self._require_exact_fields(
            payload,
            expected=self.CLAIM_FIELDS,
            context=f"claims[{index}]",
        )

        citations_payload = payload[
            "citations"
        ]
        if not isinstance(
            citations_payload,
            list,
        ):
            raise ValueError(
                f"claims[{index}].citations must be a JSON array"
            )

        citations = tuple(
            self._parse_citation(
                item,
                claim_index=index,
                citation_index=citation_index,
            )
            for citation_index, item in enumerate(
                citations_payload
            )
        )

        return GroundedAIClaim(
            text=payload[
                "text"
            ],
            citations=citations,
        )

    def _parse_citation(
        self,
        payload: object,
        *,
        claim_index: int,
        citation_index: int,
    ) -> GroundedKnowledgeCitation:
        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "claims["
                f"{claim_index}"
                "].citations["
                f"{citation_index}"
                "] must be a JSON object"
            )

        context = (
            f"claims[{claim_index}]"
            f".citations[{citation_index}]"
        )
        self._require_exact_fields(
            payload,
            expected=self.CITATION_FIELDS,
            context=context,
        )

        return GroundedKnowledgeCitation(
            knowledge_identity=payload[
                "knowledge_identity"
            ],
            statement=payload[
                "statement"
            ],
            provenance_status=payload[
                "provenance_status"
            ],
        )

    @staticmethod
    def _require_exact_fields(
        payload: dict[str, Any],
        *,
        expected: set[str],
        context: str,
    ) -> None:
        actual = set(
            payload
        )

        missing = sorted(
            expected - actual
        )
        extra = sorted(
            actual - expected
        )

        if missing:
            raise ValueError(
                f"{context} is missing required fields: "
                + ", ".join(
                    missing
                )
            )

        if extra:
            raise ValueError(
                f"{context} contains unsupported fields: "
                + ", ".join(
                    extra
                )
            )
