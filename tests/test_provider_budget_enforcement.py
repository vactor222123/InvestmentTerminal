import json
from decimal import Decimal

import pytest

from investment_terminal.ai.prompt_input import GroundedPromptInput
from investment_terminal.ai.providers.contracts import (
    GroundedProviderConfig,
    StaticGroundedProviderCredentialSource,
)
from investment_terminal.ai.providers.execution import (
    GroundedProviderExecutionService,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.ai.providers.openai_adapter import (
    OpenAIGroundedModelAdapter,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportResponse,
)


class CaptureTransport(GroundedProviderTransport):
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body=json.dumps({
                "status": "completed",
                "output": [{
                    "type": "message",
                    "content": [{
                        "type": "output_text",
                        "text": json.dumps({
                            "answer_id": "a1",
                            "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
                            "claims": [{
                                "text": "x",
                                "citations": [{
                                    "knowledge_identity": "K@1",
                                    "statement": "s",
                                    "provenance_status": "COMPLETE",
                                }],
                            }],
                        }),
                    }],
                }],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                },
            }),
        )


def adapter(max_output_tokens):
    transport = CaptureTransport()
    instance = OpenAIGroundedModelAdapter(
        config=GroundedProviderConfig(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=0,
            max_output_tokens=max_output_tokens,
        ),
        credentials=StaticGroundedProviderCredentialSource(
            provider_identity="OPENAI",
            api_key="secret",
        ),
        execution=GroundedProviderExecutionService(
            transport=transport
        ),
    )
    return instance, transport


def prompt():
    return GroundedPromptInput(
        request_id="r1",
        protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        user_query="Question",
        context=(),
    )


def test_config_serializes_optional_max_output_tokens() -> None:
    config = GroundedProviderConfig(
        provider_identity="OPENAI",
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=0,
        max_output_tokens=500,
    )
    assert config.to_dict()["max_output_tokens"] == 500


def test_openai_request_includes_real_output_cap() -> None:
    instance, transport = adapter(500)
    instance.generate(prompt())

    body = json.loads(transport.requests[0].body)
    assert body["max_output_tokens"] == 500


def test_openai_request_omits_cap_when_not_configured() -> None:
    instance, transport = adapter(None)
    instance.generate(prompt())

    body = json.loads(transport.requests[0].body)
    assert "max_output_tokens" not in body


def test_pre_execution_budget_rejects_requested_cap() -> None:
    policy = GroundedProviderBudgetPolicy(
        max_output_tokens=500
    )
    with pytest.raises(PermissionError):
        policy.require_request_allowed(
            requested_max_output_tokens=501
        )


def test_post_execution_usage_and_cost_guardrails_remain_separate() -> None:
    policy = GroundedProviderBudgetPolicy(
        max_total_tokens=120,
        max_total_cost=Decimal("0.010000"),
        currency="USD",
    )
    assert policy.max_total_tokens == 120
    assert policy.max_total_cost == Decimal("0.010000")


def test_governance_and_budget_are_distinct_policies() -> None:
    governance = GroundedProviderGovernancePolicy(
        allowed_models=(
            GroundedProviderModelAllowance(
                provider_identity="OPENAI",
                model_identity="gpt-test",
            ),
        )
    )
    governance.require_allowed(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    )
    GroundedProviderBudgetPolicy(
        max_output_tokens=500
    ).require_request_allowed(
        requested_max_output_tokens=500
    )
