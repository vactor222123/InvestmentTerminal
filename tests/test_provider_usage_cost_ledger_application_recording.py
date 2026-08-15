from decimal import Decimal

from investment_terminal.ai.providers.usage_ledger_recording import (
    GroundedProviderUsageCostLedgerRecordingService,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    InMemoryGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)
from investment_terminal.application.usage_ledger import (
    UsageCostRecordingGroundedAIApplicationService,
)


class SuccessfulApplication(
    GroundedAIApplicationService
):
    def execute(
        self,
        request: GroundedAIApplicationRequest,
    ) -> GroundedAIApplicationResult:
        return GroundedAIApplicationResult(
            generation={
                "prompt": {
                    "request_id": request.request_id,
                },
                "answer": "ok",
            },
            trace={
                "request_id": request.request_id,
                "provider_input_tokens": 100,
                "provider_output_tokens": 40,
                "provider_total_tokens": 140,
                "provider_cost": {
                    "provider_identity": "OPENAI",
                    "model_identity": "gpt-test",
                    "currency": "EUR",
                    "input_cost": "0.001000",
                    "output_cost": "0.002000",
                    "total_cost": "0.003000",
                },
            },
        )


def test_successful_application_records_usage_and_cost() -> None:
    repository = (
        InMemoryGroundedProviderUsageCostLedgerRepository()
    )
    service = UsageCostRecordingGroundedAIApplicationService(
        application_service=SuccessfulApplication(),
        recording_service=(
            GroundedProviderUsageCostLedgerRecordingService(
                repository=repository
            )
        ),
    )
    request = GroundedAIApplicationRequest(
        request_id="request-001",
        user_query="question",
    )

    result = service.execute(request)

    assert result.generation == {
        "prompt": {
            "request_id": "request-001",
        },
        "answer": "ok",
    }

    record = repository.require(
        "request-001"
    )
    assert record.input_tokens == 100
    assert record.output_tokens == 40
    assert record.total_tokens == 140
    assert record.total_cost == Decimal("0.003000")
    assert record.recorded_at.tzinfo is not None
