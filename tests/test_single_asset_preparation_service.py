"""
Tests for SingleAssetPreparationService.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.preparation.single_asset_preparation_service import (
    SingleAssetPreparationService,
)
from investment_terminal.services.historical_market_service import (
    HistoricalImportResult,
)


START = datetime(
    2025,
    8,
    1,
    tzinfo=timezone.utc,
)

END = datetime(
    2026,
    8,
    1,
    tzinfo=timezone.utc,
)

RUN_STARTED = datetime(
    2026,
    8,
    1,
    10,
    0,
    tzinfo=timezone.utc,
)

RUN_FINISHED = RUN_STARTED + timedelta(
    seconds=1.25
)


def create_clock():
    values = iter(
        [
            RUN_STARTED,
            RUN_FINISHED,
        ]
    )

    return lambda: next(values)


def test_prepare_returns_success_result() -> None:
    historical_service = Mock()

    historical_service.import_candles.return_value = (
        HistoricalImportResult(
            symbol="MSFT",
            resolution="D",
            downloaded=251,
            inserted=2,
            duplicates=249,
            stored_total=500,
            start=START,
            end=END,
        )
    )

    service = SingleAssetPreparationService(
        historical_service=historical_service,
        clock=create_clock(),
    )

    result = service.prepare(
        symbol=" msft ",
        resolution=" d ",
        start=START,
        end=END,
        currency=" usd ",
    )

    assert result.symbol == "MSFT"
    assert result.success is True
    assert result.downloaded == 251
    assert result.inserted == 2
    assert result.duplicates == 249
    assert result.elapsed_seconds == 1.25

    historical_service.import_candles.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
        start=START,
        end=END,
        currency="USD",
    )


def test_prepare_converts_error_to_failed_result() -> None:
    historical_service = Mock()
    historical_service.import_candles.side_effect = (
        RuntimeError(
            "Provider unavailable"
        )
    )

    service = SingleAssetPreparationService(
        historical_service=historical_service,
        clock=create_clock(),
    )

    result = service.prepare(
        symbol="AAPL",
        resolution="D",
        start=START,
        end=END,
    )

    assert result.symbol == "AAPL"
    assert result.success is False
    assert result.downloaded == 0
    assert result.inserted == 0
    assert result.duplicates == 0
    assert result.error_type == "RuntimeError"
    assert result.error_message == (
        "Provider unavailable"
    )


def test_prepare_rejects_invalid_date_range() -> None:
    service = SingleAssetPreparationService(
        historical_service=Mock(),
        clock=create_clock(),
    )

    with pytest.raises(
        ValueError,
        match="end must be after start",
    ):
        service.prepare(
            symbol="MSFT",
            resolution="D",
            start=END,
            end=START,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("symbol", ""),
        ("symbol", "   "),
        ("resolution", ""),
        ("currency", None),
    ],
)
def test_prepare_rejects_invalid_text(
    field_name,
    value,
) -> None:
    service = SingleAssetPreparationService(
        historical_service=Mock(),
        clock=create_clock(),
    )

    arguments = {
        "symbol": "MSFT",
        "resolution": "D",
        "start": START,
        "end": END,
        "currency": "USD",
    }
    arguments[field_name] = value

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        service.prepare(**arguments)


def test_prepare_rejects_invalid_start() -> None:
    service = SingleAssetPreparationService(
        historical_service=Mock(),
        clock=create_clock(),
    )

    with pytest.raises(
        TypeError,
        match="start",
    ):
        service.prepare(
            symbol="MSFT",
            resolution="D",
            start=None,
            end=END,
        )


def test_prepare_rejects_invalid_clock() -> None:
    service = SingleAssetPreparationService(
        historical_service=Mock(),
        clock=lambda: "invalid",
    )

    with pytest.raises(
        TypeError,
        match="clock",
    ):
        service.prepare(
            symbol="MSFT",
            resolution="D",
            start=START,
            end=END,
        )