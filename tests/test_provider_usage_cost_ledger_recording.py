from datetime import datetime, timezone
from decimal import Decimal

import pytest

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import GroundedProviderCost
from investment_terminal.ai.providers.usage_ledger_recording import (
    GroundedProviderUsageCostLedgerRecordingService,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    InMemoryGroundedProviderUsageCostLedgerRepository,
)


def usage() -> GroundedProviderUsage:
    return GroundedProviderUsage(
        input_tokens=100,
        output_tokens=40,
        total_tokens=140,
    )


def cost() -> GroundedProviderCost:
    return GroundedProviderCost(
        provider_identity="openai",
        model_identity="gpt-test",
        currency="eur",
        input_cost=Decimal("0.001000"),
        output_cost=Decimal("0.002000"),
        total_cost=Decimal("0.003000"),
    )


def recorded_at() -> datetime:
    return datetime(
        2026,
        8,
        15,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_service_requires_repository() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedProviderUsageCostLedgerRepository",
    ):
        GroundedProviderUsageCostLedgerRecordingService(
            repository=object(),  # type: ignore[arg-type]
        )


def test_record_translates_usage_and_cost_exactly() -> None:
    repository = InMemoryGroundedProviderUsageCostLedgerRepository()
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=repository,
    )

    result = service.record(
        request_id="request-001",
        usage=usage(),
        cost=cost(),
        recorded_at=recorded_at(),
    )

    assert repository.require("request-001") == result
    assert result.request_id == "request-001"
    assert result.provider_identity == "OPENAI"
    assert result.model_identity == "gpt-test"
    assert result.input_tokens == 100
    assert result.output_tokens == 40
    assert result.total_tokens == 140
    assert result.currency == "EUR"
    assert result.input_cost == Decimal("0.001000")
    assert result.output_cost == Decimal("0.002000")
    assert result.total_cost == Decimal("0.003000")
    assert result.recorded_at == recorded_at()


def test_record_normalizes_request_identity() -> None:
    repository = InMemoryGroundedProviderUsageCostLedgerRepository()
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=repository,
    )

    result = service.record(
        request_id="  request-001  ",
        usage=usage(),
        cost=cost(),
        recorded_at=recorded_at(),
    )

    assert result.request_id == "request-001"
    assert repository.require("request-001") == result


def test_record_rejects_wrong_usage_type() -> None:
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=InMemoryGroundedProviderUsageCostLedgerRepository(),
    )

    with pytest.raises(
        TypeError,
        match="GroundedProviderUsage",
    ):
        service.record(
            request_id="request-001",
            usage=object(),  # type: ignore[arg-type]
            cost=cost(),
            recorded_at=recorded_at(),
        )


def test_record_rejects_wrong_cost_type() -> None:
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=InMemoryGroundedProviderUsageCostLedgerRepository(),
    )

    with pytest.raises(
        TypeError,
        match="GroundedProviderCost",
    ):
        service.record(
            request_id="request-001",
            usage=usage(),
            cost=object(),  # type: ignore[arg-type]
            recorded_at=recorded_at(),
        )


def test_record_rejects_duplicate_request_identity() -> None:
    repository = InMemoryGroundedProviderUsageCostLedgerRepository()
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=repository,
    )

    service.record(
        request_id="request-001",
        usage=usage(),
        cost=cost(),
        recorded_at=recorded_at(),
    )

    with pytest.raises(
        ValueError,
        match="request identity already exists",
    ):
        service.record(
            request_id="request-001",
            usage=usage(),
            cost=cost(),
            recorded_at=recorded_at(),
        )


def test_record_rejects_naive_recorded_at() -> None:
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=InMemoryGroundedProviderUsageCostLedgerRepository(),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        service.record(
            request_id="request-001",
            usage=usage(),
            cost=cost(),
            recorded_at=datetime(2026, 8, 15, 12, 0),
        )
