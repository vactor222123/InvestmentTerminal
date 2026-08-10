"""
OpenAI Responses API adapter for Evidence-Grounded AI.
"""

import json
from typing import Any

from investment_terminal.ai.model_adapter import (
    GroundedModelAdapter,
    GroundedModelResponse,
    GroundedProviderOperationalMetadata,
    GroundedProviderUsage,
)
from investment_terminal.ai.prompt_input import GroundedPromptInput
from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
    GroundedProviderCredentialSource,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransportRequest,
)


class OpenAIGroundedModelAdapter(GroundedModelAdapter):
    PROVIDER_IDENTITY = "OPENAI"
    RESPONSES_URL = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        *,
        config: GroundedProviderConfig,
        credentials: GroundedProviderCredentialSource,
        execution: GroundedProviderExecutionService,
    ) -> None:
        if not isinstance(config, GroundedProviderConfig):
            raise TypeError(
                "config must be a GroundedProviderConfig"
            )
        if config.provider_identity != self.PROVIDER_IDENTITY:
            raise ValueError(
                "OpenAI adapter requires provider_identity OPENAI"
            )
        if not isinstance(
            credentials,
            GroundedProviderCredentialSource,
        ):
            raise TypeError(
                "credentials must be a GroundedProviderCredentialSource"
            )
        if not isinstance(
            execution,
            GroundedProviderExecutionService,
        ):
            raise TypeError(
                "execution must be a GroundedProviderExecutionService"
            )
        self._config = config
        self._credentials = credentials
        self._execution = execution

    def generate(
        self,
        prompt: GroundedPromptInput,
    ) -> GroundedModelResponse:
        if not isinstance(prompt, GroundedPromptInput):
            raise TypeError(
                "prompt must be a GroundedPromptInput"
            )

        api_key = self._credentials.get_api_key(
            provider_identity=self.PROVIDER_IDENTITY,
        )
        transport_request = GroundedProviderTransportRequest(
            request_id=prompt.request_id,
            method="POST",
            url=self.RESPONSES_URL,
            headers=(
                ("Authorization", f"Bearer {api_key}"),
                ("Content-Type", "application/json"),
                ("X-Client-Request-Id", prompt.request_id),
            ),
            body=json.dumps(
                self._request_payload(prompt),
                separators=(",", ":"),
                sort_keys=True,
            ),
            timeout_seconds=self._config.timeout_seconds,
        )
        execution_result = self._execution.execute(
            request=transport_request,
            config=self._config,
        )

        payload = self._parse_completed_response(
            execution_result.response.body
        )
        raw_text = self._extract_output_text_from_payload(
            payload
        )
        usage = self._extract_usage_from_payload(
            payload
        )

        return GroundedModelResponse(
            request_id=prompt.request_id,
            provider_identity=self.PROVIDER_IDENTITY,
            model_identity=self._config.model_identity,
            raw_text=raw_text,
            operational_metadata=GroundedProviderOperationalMetadata(
                attempt_count=execution_result.attempt_count,
                retry_count=execution_result.retry_count,
                transport_status_code=(
                    execution_result.response.status_code
                ),
                transport_outcome="SUCCESS",
            ),
            usage=usage,
        )

    def _request_payload(
        self,
        prompt: GroundedPromptInput,
    ) -> dict[str, Any]:
        return {
            "model": self._config.model_identity,
            "instructions": (
                "Answer only from the supplied Evidence-Grounded AI context. "
                "Every claim must cite one or more supplied Knowledge identities. "
                "Copy each cited Knowledge statement and provenance status exactly. "
                "Do not add confidence, prediction, effectiveness, or causal claims."
            ),
            "input": json.dumps(
                prompt.to_dict(),
                separators=(",", ":"),
                sort_keys=True,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "evidence_grounded_answer_v1",
                    "strict": True,
                    "schema": self._answer_schema(),
                }
            },
        }

    @staticmethod
    def _answer_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "answer_id": {"type": "string"},
                "protocol_identity": {
                    "type": "string",
                    "enum": ["EVIDENCE_GROUNDED_ANSWER@1"],
                },
                "claims": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "text": {"type": "string"},
                            "citations": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "knowledge_identity": {
                                            "type": "string"
                                        },
                                        "statement": {
                                            "type": "string"
                                        },
                                        "provenance_status": {
                                            "type": "string"
                                        },
                                    },
                                    "required": [
                                        "knowledge_identity",
                                        "statement",
                                        "provenance_status",
                                    ],
                                },
                            },
                        },
                        "required": ["text", "citations"],
                    },
                },
            },
            "required": [
                "answer_id",
                "protocol_identity",
                "claims",
            ],
        }

    @staticmethod
    def _parse_completed_response(
        response_body: str,
    ) -> dict[str, Any]:
        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "OpenAI response body must be valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError(
                "OpenAI response body must be a JSON object"
            )
        if payload.get("status") != "completed":
            raise ValueError(
                "OpenAI response status must be completed"
            )
        return payload

    @staticmethod
    def _extract_output_text_from_payload(
        payload: dict[str, Any],
    ) -> str:
        output = payload.get("output")
        if not isinstance(output, list):
            raise ValueError(
                "OpenAI response output must be an array"
            )

        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "output_text":
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)

        if not parts:
            raise ValueError(
                "OpenAI response contains no output_text"
            )
        return "".join(parts)

    @staticmethod
    def _extract_usage_from_payload(
        payload: dict[str, Any],
    ) -> GroundedProviderUsage | None:
        raw_usage = payload.get("usage")
        if raw_usage is None:
            return None
        if not isinstance(raw_usage, dict):
            raise ValueError(
                "OpenAI response usage must be an object or null"
            )

        fields = {}
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            value = raw_usage.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"OpenAI response usage.{key} must be "
                    "a non-negative integer"
                )
            fields[key] = value

        return GroundedProviderUsage(**fields)

    @staticmethod
    def _extract_output_text(
        response_body: str,
    ) -> str:
        payload = OpenAIGroundedModelAdapter._parse_completed_response(
            response_body
        )
        return OpenAIGroundedModelAdapter._extract_output_text_from_payload(
            payload
        )
