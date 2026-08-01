"""
Tests for MarketDataRefreshService.
"""

import json
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from unittest.mock import Mock

import pytest

from investment_terminal.services.historical_market_service import (
    HistoricalImportResult,
    HistoricalMarketService,
)
from investment_terminal.services.market_data_freshness_service import (
    MarketDataFreshnessResult,
    MarketDataFreshnessService,
)
from investment_terminal.services.market_data_refresh_service import (
    MarketDataRefreshService,
)


CHECKED_AT = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_freshness(
    *,
    status: str,
    symbol: str = "MSFT",
    resolution: str = "D",
    last_candle_at: datetime | None = None,
    age_hours: float | None = None,
) -> MarketDataFreshnessResult:
    return MarketDataFreshnessResult(
        symbol=symbol,
        resolution=resolution,
        checked_at=CHECKED_AT,
        maximum_age_hours=24.0,
        status=status,
        last_candle_at=last_candle_at,
        age_hours=age_hours,
    )


def create_import_result(
    *,
    symbol: str = "MSFT",
    resolution: str = "D",
    start: datetime,
    end: datetime,
    downloaded: int = 8,
    inserted: int = 1,
) -> HistoricalImportResult:
    return HistoricalImportResult(
        symbol=symbol,
        resolution=resolution,
        downloaded=downloaded,
        inserted=inserted,
        duplicates=(
            downloaded - inserted
        ),
        stored_total=752,
        start=start,
        end=end,
    )


def create_service(
    freshness_service,
    historical_market_service,
) -> MarketDataRefreshService:
    return MarketDataRefreshService(
        freshness_service=freshness_service,
        historical_market_service=(
            historical_market_service
        ),
    )


def test_fresh_data_skips_import() -> None:
    freshness = create_freshness(
        status="FRESH",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=12)
        ),
        age_hours=12.0,
    )

    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )
    freshness_service.check.return_value = (
        freshness
    )

    historical_service = Mock(
        spec=HistoricalMarketService
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_fresh(
        symbol=" msft ",
        resolution=" d ",
        currency=" usd ",
        checked_at=CHECKED_AT,
    )

    assert result.symbol == "MSFT"
    assert result.resolution == "D"
    assert result.refresh_attempted is False
    assert result.is_ready is True
    assert result.import_result is None
    assert result.downloaded == 0
    assert result.inserted == 0
    assert result.duplicates == 0

    freshness_service.check.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )
    historical_service.import_candles.assert_not_called()


def test_stale_data_is_refreshed_from_overlap() -> None:
    last_candle_at = (
        CHECKED_AT
        - timedelta(hours=48)
    )
    freshness_before = create_freshness(
        status="STALE",
        last_candle_at=last_candle_at,
        age_hours=48.0,
    )
    freshness_after = create_freshness(
        status="FRESH",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=4)
        ),
        age_hours=4.0,
    )

    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )
    freshness_service.check.side_effect = [
        freshness_before,
        freshness_after,
    ]

    historical_service = Mock(
        spec=HistoricalMarketService
    )

    expected_start = (
        last_candle_at
        - timedelta(days=7)
    )
    expected_end = (
        CHECKED_AT
        + timedelta(days=1)
    )

    historical_service.import_candles.return_value = (
        create_import_result(
            start=expected_start,
            end=expected_end,
        )
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_fresh(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.refresh_attempted is True
    assert result.is_ready is True
    assert result.freshness_before.is_stale
    assert result.freshness_after.is_fresh
    assert result.downloaded == 8
    assert result.inserted == 1
    assert result.duplicates == 7

    historical_service.import_candles.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
        start=expected_start,
        end=expected_end,
        currency="USD",
    )

    assert freshness_service.check.call_count == 2


def test_missing_data_uses_initial_lookback() -> None:
    freshness_before = create_freshness(
        status="MISSING",
    )
    freshness_after = create_freshness(
        status="FRESH",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=6)
        ),
        age_hours=6.0,
    )

    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )
    freshness_service.check.side_effect = [
        freshness_before,
        freshness_after,
    ]

    historical_service = Mock(
        spec=HistoricalMarketService
    )

    expected_start = (
        CHECKED_AT
        - timedelta(days=3 * 365)
    )
    expected_end = (
        CHECKED_AT
        + timedelta(days=1)
    )

    historical_service.import_candles.return_value = (
        create_import_result(
            start=expected_start,
            end=expected_end,
            downloaded=752,
            inserted=752,
        )
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_fresh(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.freshness_before.is_missing
    assert result.freshness_after.is_fresh
    assert result.refresh_attempted is True
    assert result.downloaded == 752
    assert result.inserted == 752
    assert result.duplicates == 0

    historical_service.import_candles.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
        start=expected_start,
        end=expected_end,
        currency="USD",
    )


def test_refresh_can_remain_stale() -> None:
    stale = create_freshness(
        status="STALE",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=48)
        ),
        age_hours=48.0,
    )

    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )
    freshness_service.check.side_effect = [
        stale,
        stale,
    ]

    historical_service = Mock(
        spec=HistoricalMarketService
    )

    start = (
        stale.last_candle_at
        - timedelta(days=7)
    )
    end = (
        CHECKED_AT
        + timedelta(days=1)
    )

    historical_service.import_candles.return_value = (
        create_import_result(
            start=start,
            end=end,
            downloaded=7,
            inserted=0,
        )
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_fresh(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.refresh_attempted is True
    assert result.is_ready is False
    assert result.freshness_after.is_stale
    assert result.inserted == 0
    assert result.duplicates == 7


def test_ensure_many_preserves_order() -> None:
    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )

    freshness_service.check.side_effect = [
        create_freshness(
            symbol="MSFT",
            status="FRESH",
            last_candle_at=(
                CHECKED_AT
                - timedelta(hours=8)
            ),
            age_hours=8.0,
        ),
        create_freshness(
            symbol="AAPL",
            status="FRESH",
            last_candle_at=(
                CHECKED_AT
                - timedelta(hours=9)
            ),
            age_hours=9.0,
        ),
        create_freshness(
            symbol="GOOGL",
            status="FRESH",
            last_candle_at=(
                CHECKED_AT
                - timedelta(hours=10)
            ),
            age_hours=10.0,
        ),
    ]

    historical_service = Mock(
        spec=HistoricalMarketService
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_many(
        symbols=(
            "msft",
            "aapl",
            "googl",
        ),
        resolution="d",
        checked_at=CHECKED_AT,
    )

    assert [
        item.symbol
        for item in result.results
    ] == [
        "MSFT",
        "AAPL",
        "GOOGL",
    ]

    assert result.universe_size == 3
    assert result.ready_count == 3
    assert result.failed_count == 0
    assert result.refreshed_count == 0
    assert result.all_ready is True
    assert result.failed_symbols == ()

    historical_service.import_candles.assert_not_called()


def test_ensure_many_reports_failed_symbols() -> None:
    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )

    msft_fresh = create_freshness(
        symbol="MSFT",
        status="FRESH",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=8)
        ),
        age_hours=8.0,
    )
    aapl_stale = create_freshness(
        symbol="AAPL",
        status="STALE",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=48)
        ),
        age_hours=48.0,
    )

    freshness_service.check.side_effect = [
        msft_fresh,
        aapl_stale,
        aapl_stale,
    ]

    historical_service = Mock(
        spec=HistoricalMarketService
    )
    historical_service.import_candles.return_value = (
        create_import_result(
            symbol="AAPL",
            start=(
                aapl_stale.last_candle_at
                - timedelta(days=7)
            ),
            end=(
                CHECKED_AT
                + timedelta(days=1)
            ),
            downloaded=7,
            inserted=0,
        )
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_many(
        symbols=(
            "MSFT",
            "AAPL",
        ),
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.ready_count == 1
    assert result.failed_count == 1
    assert result.refreshed_count == 1
    assert result.all_ready is False
    assert result.failed_symbols == (
        "AAPL",
    )


def test_ensure_many_rejects_duplicates() -> None:
    service = create_service(
        Mock(
            spec=MarketDataFreshnessService
        ),
        Mock(
            spec=HistoricalMarketService
        ),
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        service.ensure_many(
            symbols=(
                "MSFT",
                " msft ",
            ),
            resolution="D",
            checked_at=CHECKED_AT,
        )


def test_service_supports_custom_ranges() -> None:
    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )
    historical_service = Mock(
        spec=HistoricalMarketService
    )

    service = MarketDataRefreshService(
        freshness_service=freshness_service,
        historical_market_service=historical_service,
        initial_lookback=timedelta(
            days=365
        ),
        stale_overlap=timedelta(
            days=3
        ),
        end_buffer=timedelta(
            hours=12
        ),
    )

    assert service.initial_lookback == timedelta(
        days=365
    )
    assert service.stale_overlap == timedelta(
        days=3
    )
    assert service.end_buffer == timedelta(
        hours=12
    )


def test_universe_result_is_json_serializable() -> None:
    freshness_service = Mock(
        spec=MarketDataFreshnessService
    )

    fresh = create_freshness(
        status="FRESH",
        last_candle_at=(
            CHECKED_AT
            - timedelta(hours=8)
        ),
        age_hours=8.0,
    )
    freshness_service.check.return_value = (
        fresh
    )

    historical_service = Mock(
        spec=HistoricalMarketService
    )

    result = create_service(
        freshness_service,
        historical_service,
    ).ensure_many(
        symbols=(
            "MSFT",
        ),
        resolution="D",
        checked_at=CHECKED_AT,
    )

    payload = result.to_dict()
    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert payload["all_ready"] is True
    assert payload["ready_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["results"][0]["symbol"] == "MSFT"
    assert '"freshness_before"' in serialized
    assert '"freshness_after"' in serialized


@pytest.mark.parametrize(
    "field_name",
    [
        "initial_lookback",
        "stale_overlap",
        "end_buffer",
    ],
)
def test_service_rejects_non_positive_ranges(
    field_name,
) -> None:
    arguments = {
        "freshness_service": Mock(
            spec=MarketDataFreshnessService
        ),
        "historical_market_service": Mock(
            spec=HistoricalMarketService
        ),
        "initial_lookback": timedelta(
            days=365
        ),
        "stale_overlap": timedelta(
            days=7
        ),
        "end_buffer": timedelta(
            days=1
        ),
    }

    arguments[field_name] = timedelta(0)

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        MarketDataRefreshService(
            **arguments
        )