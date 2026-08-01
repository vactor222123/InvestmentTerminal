"""
Tests for normalized fundamental-data models.
"""

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_data_quality_service import (
    FundamentalDataQualityService,
)


def create_snapshot() -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol=" msft ",
        currency=" usd ",
        generated_at=datetime(
            2026,
            8,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        market_cap=3_500_000_000_000,
        trailing_pe=35.0,
        forward_pe=30.0,
        revenue_growth=0.15,
        earnings_growth=0.12,
        gross_margin=0.69,
        operating_margin=0.44,
        net_margin=0.36,
        return_on_equity=0.33,
        total_debt=80_000_000_000,
        free_cash_flow=75_000_000_000,
    )


def test_snapshot_normalizes_symbol_and_currency() -> None:
    snapshot = create_snapshot()

    assert snapshot.symbol == "MSFT"
    assert snapshot.currency == "USD"


def test_snapshot_rejects_invalid_number() -> None:
    with pytest.raises(
        ValueError,
        match="trailing_pe",
    ):
        replace(
            create_snapshot(),
            trailing_pe=float("nan"),
        )


def test_quality_service_calculates_completeness() -> None:
    snapshot = create_snapshot()

    quality = FundamentalDataQualityService.evaluate(
        snapshot=snapshot,
        source="Yahoo Finance",
        fetched_at=datetime(
            2026,
            8,
            1,
            12,
            5,
            tzinfo=timezone.utc,
        ),
    )

    assert quality.available_fields == 11
    assert quality.total_fields == 28
    assert quality.completeness_percent == pytest.approx(
        39.29,
        abs=0.01,
    )
    assert "peg_ratio" in quality.missing_fields
    assert quality.source == "Yahoo Finance"


def test_snapshot_is_json_serializable() -> None:
    snapshot = create_snapshot()

    quality = FundamentalDataQualityService.evaluate(
        snapshot=snapshot,
        source="Yahoo Finance",
    )

    snapshot_with_quality = replace(
        snapshot,
        data_quality=quality,
    )

    payload = snapshot_with_quality.to_dict()
    serialized = json.dumps(payload)

    assert '"symbol": "MSFT"' in serialized
    assert (
        payload["generated_at"]
        == "2026-08-01T12:00:00+00:00"
    )
    assert isinstance(
        payload["data_quality"]["missing_fields"],
        list,
    )


def test_quality_service_rejects_empty_source() -> None:
    with pytest.raises(
        ValueError,
        match="source",
    ):
        FundamentalDataQualityService.evaluate(
            snapshot=create_snapshot(),
            source="   ",
        )