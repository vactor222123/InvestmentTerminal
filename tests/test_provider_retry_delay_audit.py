import json
from decimal import Decimal

from investment_terminal.ai.audit import (
    GroundedGenerationTraceService,
)
from investment_terminal.ai.model_adapter import (
    GroundedProviderOperationalMetadata,
)
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
from investment_terminal.ai.providers.retry_delay import (
    GroundedProviderRetryDelayPolicy,
)
from investment_terminal.ai.providers.sleeper import (
    GroundedProviderSleeper,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportResponse,
)


def openai_body() -> str:
    return json.dumps(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "answer_id": "answer-1",
                                    "protocol_identity": (
                                        "EVIDENCE_GROUNDED_ANSWER@1"
                                    ),
                                    "claims": [
                                        {
                                            "text": "x",
                                            "citations": [
                                                {
                                                    "knowledge_identity": "K@1",
                                                    "statement": "s",
                                                    "provenance_status": "COMPLETE",
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ),
                        }
                    ],
                }
            ],
        }
    )


class RecordingSleeper(GroundedProviderSleeper):
    def __init__(self) -> None:
        self.delays = []

    def sleep(self, *, delay_seconds):
        self.delays.append(delay_seconds)


class RetryAfterThenSuccessTransport(
    GroundedProviderTransport
):
    def __init__(self) -> None:
        self.calls = 0

    def send(self, request):
        self.calls += 1
        if self.calls == 1:
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message="do-not-audit-this-message",
                retryable=True,
                retry_after_seconds=Decimal("5"),
            )
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(
                ("Retry-After", "raw-header-must-not-appear"),
            ),
            body=openai_body(),
        )


def adapter():
    sleeper = RecordingSleeper()
    return (
        OpenAIGroundedModelAdapter(
            config=GroundedProviderConfig(
                provider_identity="OPENAI",
                model_identity="gpt-test",
                timeout_seconds=10,
                max_retries=1,
            ),
            credentials=StaticGroundedProviderCredentialSource(
                provider_identity="OPENAI",
                api_key="secret-value",
            ),
            execution=GroundedProviderExecutionService(
                transport=RetryAfterThenSuccessTransport(),
                retry_delay_policy=GroundedProviderRetryDelayPolicy(
                    initial_delay_seconds=Decimal("1"),
                    multiplier=Decimal("2"),
                    maximum_delay_seconds=Decimal("4"),
                ),
                sleeper=sleeper,
            ),
        ),
        sleeper,
    )


def test_operational_metadata_serialization_is_backward_compatible_without_delays() -> None:
    metadata = GroundedProviderOperationalMetadata(
        attempt_count=2,
        retry_count=1,
        transport_status_code=200,
    )

    assert metadata.to_dict() == {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
    }


def test_openai_operational_metadata_exposes_applied_effective_delay() -> None:
    model_adapter, sleeper = adapter()
    response = model_adapter.generate(
        GroundedPromptInput(
            request_id="request-1",
            protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
            user_query="Question",
            context=(),
        )
    )

    assert sleeper.delays == [Decimal("5")]
    assert response.operational_metadata is not None
    assert response.operational_metadata.retry_delay_seconds == (
        Decimal("5"),
    )
    assert response.operational_metadata.to_dict()[
        "retry_delay_seconds"
    ] == ["5"]


def test_safe_retry_delay_metadata_contains_no_raw_transport_data() -> None:
    model_adapter, _ = adapter()
    response = model_adapter.generate(
        GroundedPromptInput(
            request_id="request-1",
            protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
            user_query="Question",
            context=(),
        )
    )

    serialized = str(
        response.operational_metadata.to_dict()
    ).lower()

    for forbidden in (
        "retry-after",
        "raw-header-must-not-appear",
        "do-not-audit-this-message",
        "authorization",
        "secret-value",
        "headers",
        "body",
        "url",
    ):
        assert forbidden not in serialized
