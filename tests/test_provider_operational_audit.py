import json
from datetime import datetime, timezone

from investment_terminal.ai.audit import (
    GroundedGenerationTraceService,
)
from investment_terminal.ai.context_selection import (
    GroundedContextSelectionService,
)
from investment_terminal.ai.model_adapter import (
    GroundedModelResponse,
    GroundedProviderOperationalMetadata,
    StaticGroundedModelAdapter,
)
from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
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
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportResponse,
)
from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelopeService,
)
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def envelope():
    record = KnowledgeRecord(
        knowledge_id="WORLD_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="WORLD was present historically.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(2),
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id="11111111-1111-4111-8111-111111111111",
                observed_at=dt(1),
                checksum_sha256="a" * 64,
            ),
        ),
    )
    return KnowledgeRecordEnvelopeService().build(
        record
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
                            "text": answer_json(),
                        }
                    ],
                }
            ],
        }
    )


class RetryThenSuccessTransport(
    GroundedProviderTransport
):
    def __init__(self) -> None:
        self.calls = 0

    def send(self, request):
        self.calls += 1
        if self.calls == 1:
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message="temporary",
                retryable=True,
            )
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(
                ("x-request-id", "provider-secret-ish-metadata"),
            ),
            body=openai_body(),
        )


def openai_adapter(
    transport,
):
    return OpenAIGroundedModelAdapter(
        config=GroundedProviderConfig(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=2,
        ),
        credentials=StaticGroundedProviderCredentialSource(
            provider_identity="OPENAI",
            api_key="secret-value",
        ),
        execution=GroundedProviderExecutionService(
            transport=transport
        ),
    )


def test_openai_model_response_carries_safe_operational_metadata() -> None:
    transport = RetryThenSuccessTransport()
    response = openai_adapter(
        transport
    ).generate(
        GroundedPromptInput(
            request_id="request-1",
            protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
            user_query="Question",
            context=(),
        )
    )

    assert response.operational_metadata is not None
    assert response.operational_metadata.attempt_count == 2
    assert response.operational_metadata.retry_count == 1
    assert response.operational_metadata.transport_status_code == 200
    assert response.operational_metadata.transport_outcome == "SUCCESS"


def test_operational_metadata_serializes_without_http_or_secret_payload() -> None:
    response = GroundedModelResponse(
        request_id="request-1",
        provider_identity="OPENAI",
        model_identity="gpt-test",
        raw_text="{}",
        operational_metadata=GroundedProviderOperationalMetadata(
            attempt_count=2,
            retry_count=1,
            transport_status_code=200,
        ),
    )

    data = response.to_dict()

    assert data["operational_metadata"] == {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
    }
    serialized = str(
        data["operational_metadata"]
    ).lower()
    for forbidden in (
        "authorization",
        "api_key",
        "secret-value",
        "headers",
        "body",
        "url",
    ):
        assert forbidden not in serialized


def test_static_adapter_remains_backward_compatible_without_operational_key() -> None:
    response = StaticGroundedModelAdapter(
        provider_identity="STATIC",
        model_identity="STATIC@1",
        raw_text="{}",
    ).generate(
        GroundedPromptInput(
            request_id="request-1",
            protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
            user_query="Question",
            context=(),
        )
    )

    assert response.operational_metadata is None
    assert "operational_metadata" not in response.to_dict()


def test_generation_trace_exposes_safe_provider_operation() -> None:
    transport = RetryThenSuccessTransport()
    result = GroundedGenerationService(
        adapter=openai_adapter(
            transport
        )
    ).generate(
        request_id="request-1",
        user_query="Question",
        knowledge=(
            envelope(),
        ),
    )

    trace = GroundedGenerationTraceService().build(
        result
    )
    data = trace.to_dict()

    assert data["provider_operation"] == {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
    }

    serialized = str(data).lower()
    for forbidden in (
        "authorization",
        "secret-value",
        "provider-secret-ish-metadata",
        "headers",
        "raw_text",
        "body",
    ):
        assert forbidden not in serialized


def test_static_generation_trace_has_no_provider_operation_extension() -> None:
    source = envelope()
    raw = answer_json()

    result = GroundedGenerationService(
        adapter=StaticGroundedModelAdapter(
            provider_identity="STATIC_REFERENCE",
            model_identity="STATIC_REFERENCE_MODEL@1",
            raw_text=raw,
        )
    ).generate(
        request_id="request-1",
        user_query="Question",
        knowledge=(
            source,
        ),
    )

    data = GroundedGenerationTraceService().build(
        result
    ).to_dict()

    assert "provider_operation" not in data
