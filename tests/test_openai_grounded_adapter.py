import json

import pytest

from investment_terminal.ai.prompt_input import (
    GroundedPromptInput,
)
from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
    StaticGroundedProviderCredentialSource,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.openai_adapter import (
    OpenAIGroundedModelAdapter,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportResponse,
)


def prompt() -> GroundedPromptInput:
    return GroundedPromptInput(
        request_id="request-1",
        protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        user_query="What historical context is available?",
        context=(),
    )


def config() -> GroundedProviderConfig:
    return GroundedProviderConfig(
        provider_identity="OPENAI",
        model_identity="gpt-5.6",
        timeout_seconds=30,
        max_retries=2,
    )


def answer_json() -> str:
    return json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
            "claims": [
                {
                    "text": "Historical context is available.",
                    "citations": [
                        {
                            "knowledge_identity": "WORLD_CONTEXT@1",
                            "statement": "WORLD was present historically.",
                            "provenance_status": "COMPLETE",
                        }
                    ],
                }
            ],
        }
    )


def openai_response_body() -> str:
    return json.dumps(
        {
            "id": "resp_123",
            "object": "response",
            "status": "completed",
            "model": "gpt-5.6",
            "output": [
                {
                    "type": "message",
                    "id": "msg_123",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": answer_json(),
                        }
                    ],
                }
            ],
        }
    )


class CaptureTransport(
    GroundedProviderTransport
):
    def __init__(self) -> None:
        self.requests = []

    def send(self, request):
        self.requests.append(
            request
        )
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body=openai_response_body(),
        )


def adapter_with_capture():
    transport = CaptureTransport()
    adapter = OpenAIGroundedModelAdapter(
        config=config(),
        credentials=StaticGroundedProviderCredentialSource(
            provider_identity="OPENAI",
            api_key="secret-value",
        ),
        execution=GroundedProviderExecutionService(
            transport=transport
        ),
    )
    return adapter, transport


def test_openai_adapter_builds_responses_api_request() -> None:
    adapter, transport = adapter_with_capture()

    result = adapter.generate(
        prompt()
    )

    assert result.request_id == "request-1"
    assert result.provider_identity == "OPENAI"
    assert result.model_identity == "gpt-5.6"
    assert json.loads(result.raw_text)[
        "protocol_identity"
    ] == "EVIDENCE_GROUNDED_ANSWER@1"

    sent = transport.requests[0]
    assert sent.method == "POST"
    assert sent.url == "https://api.openai.com/v1/responses"
    assert sent.timeout_seconds == 30.0


def test_openai_adapter_injects_bearer_credential_and_correlation() -> None:
    adapter, transport = adapter_with_capture()
    adapter.generate(
        prompt()
    )

    headers = dict(
        transport.requests[0].headers
    )
    assert headers["Authorization"] == "Bearer secret-value"
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Client-Request-Id"] == "request-1"


def test_openai_payload_uses_strict_structured_output_schema() -> None:
    adapter, transport = adapter_with_capture()
    adapter.generate(
        prompt()
    )

    payload = json.loads(
        transport.requests[0].body
    )

    assert payload["model"] == "gpt-5.6"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["name"] == (
        "evidence_grounded_answer_v1"
    )
    assert payload["text"]["format"]["schema"][
        "additionalProperties"
    ] is False
    assert "EVIDENCE_GROUNDED_PROMPT@1" in payload["input"]


def test_api_key_is_not_present_in_request_body() -> None:
    adapter, transport = adapter_with_capture()
    adapter.generate(
        prompt()
    )

    assert "secret-value" not in transport.requests[0].body


def test_adapter_requires_openai_provider_identity() -> None:
    bad_config = GroundedProviderConfig(
        provider_identity="OTHER",
        model_identity="model-1",
        timeout_seconds=30,
        max_retries=0,
    )

    with pytest.raises(
        ValueError,
        match="provider_identity OPENAI",
    ):
        OpenAIGroundedModelAdapter(
            config=bad_config,
            credentials=StaticGroundedProviderCredentialSource(
                provider_identity="OTHER",
                api_key="secret",
            ),
            execution=GroundedProviderExecutionService(
                transport=CaptureTransport()
            ),
        )


def test_incomplete_openai_response_is_rejected() -> None:
    body = json.dumps(
        {
            "status": "incomplete",
            "output": [],
        }
    )

    with pytest.raises(
        ValueError,
        match="status must be completed",
    ):
        OpenAIGroundedModelAdapter._extract_output_text(
            body
        )


def test_missing_output_text_is_rejected() -> None:
    body = json.dumps(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "refusal",
                            "refusal": "Cannot comply",
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="no output_text",
    ):
        OpenAIGroundedModelAdapter._extract_output_text(
            body
        )


def test_multiple_output_text_parts_are_combined_deterministically() -> None:
    body = json.dumps(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "{",
                        },
                        {
                            "type": "output_text",
                            "text": "}",
                        },
                    ],
                }
            ],
        }
    )

    assert OpenAIGroundedModelAdapter._extract_output_text(
        body
    ) == "{}"


def test_adapter_imports_no_openai_sdk() -> None:
    import investment_terminal.ai.providers.openai_adapter as module

    assert "OpenAI" not in module.__dict__
