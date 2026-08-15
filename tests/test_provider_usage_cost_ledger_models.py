from datetime import datetime, timezone
from decimal import Decimal

import pytest

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
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


def record(
    **overrides,
) -> GroundedProviderUsageCostLedgerRecord:
    values = {
        "request_id": "request-001",
        "provider_identity": "openai",
        "model_identity": "gpt-test",
        "input_tokens": 100,
        "output_tokens": 40,
        "total_tokens": 140,
        "currency": "eur",
        "input_cost": Decimal("0.001000"),
        "output_cost": Decimal("0.002000"),
        "total_cost": Decimal("0.003000"),
        "recorded_at": recorded_at(),
    }
    values.update(overrides)
    return GroundedProviderUsageCostLedgerRecord(
        **values
    )


def test_record_normalizes_provider_and_currency() -> None:
    result = record()

    assert result.provider_identity == "OPENAI"
    assert result.currency == "EUR"
    assert result.identity_key == "request-001"


def test_record_preserves_exact_usage_and_cost() -> None:
    result = record()

    assert result.input_tokens == 100
    assert result.output_tokens == 40
    assert result.total_tokens == 140
    assert result.input_cost == Decimal("0.001000")
    assert result.output_cost == Decimal("0.002000")
    assert result.total_cost == Decimal("0.003000")


def test_record_requires_token_total_consistency() -> None:
    with pytest.raises(
        ValueError,
        match="total_tokens must equal",
    ):
        record(
            total_tokens=141,
        )


def test_record_requires_cost_total_consistency() -> None:
    with pytest.raises(
        ValueError,
        match="total_cost must equal",
    ):
        record(
            total_cost=Decimal("0.004000"),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "input_tokens",
        "output_tokens",
        "total_tokens",
    ),
)
def test_record_rejects_negative_token_counts(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="non-negative integer",
    ):
        record(
            **{field_name: -1},
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "input_cost",
        "output_cost",
        "total_cost",
    ),
)
def test_record_rejects_negative_costs(
    field_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="finite non-negative decimal",
    ):
        record(
            **{field_name: Decimal("-0.000001")},
        )


def test_record_requires_timezone_aware_recorded_at() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        record(
            recorded_at=datetime(2026, 8, 15, 12, 0),
        )


def test_record_serializes_deterministically() -> None:
    result = record()

    assert result.to_dict() == {
        "request_id": "request-001",
        "provider_identity": "OPENAI",
        "model_identity": "gpt-test",
        "input_tokens": 100,
        "output_tokens": 40,
        "total_tokens": 140,
        "currency": "EUR",
        "input_cost": "0.001000",
        "output_cost": "0.002000",
        "total_cost": "0.003000",
        "recorded_at": "2026-08-15T12:00:00+00:00",
    }
