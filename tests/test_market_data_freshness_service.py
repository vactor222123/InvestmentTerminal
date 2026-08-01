"""
Tests for trading-session-aware market-data freshness.
"""

import json
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)

import pytest

from investment_terminal.config.settings import (
    Settings,
)
from investment_terminal.database.database import (
    Database,
)
from investment_terminal.models.candle import (
    Candle,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)
from investment_terminal.services.market_data_freshness_service import (
    MarketDataFreshnessResult,
    MarketDataFreshnessService,
    UnitedStatesMarketCalendar,
)


SATURDAY_CHECK = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


@pytest.fixture
def repository(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        tmp_path / "freshness.db",
    )

    database = Database()
    database.initialize()

    yield CandleRepository(
        database
    )

    database.close()


def create_candle(
    *,
    symbol: str = "MSFT",
    resolution: str = "D",
    timestamp: datetime,
) -> Candle:
    return Candle(
        symbol=symbol,
        resolution=resolution,
        timestamp=timestamp,
        open_price=100.0,
        high_price=105.0,
        low_price=98.0,
        close_price=103.0,
        volume=1_000_000.0,
        currency="USD",
    )


def daily_timestamp(
    year: int,
    month: int,
    day: int,
) -> datetime:
    """
    Approximate Yahoo daily timestamp at midnight New York time.
    """
    return datetime(
        year,
        month,
        day,
        4,
        0,
        tzinfo=timezone.utc,
    )


def test_friday_daily_candle_is_fresh_on_saturday(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=daily_timestamp(
                2026,
                7,
                31,
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol=" msft ",
        resolution=" d ",
        checked_at=SATURDAY_CHECK,
    )

    assert result.symbol == "MSFT"
    assert result.resolution == "D"
    assert result.status == "FRESH"
    assert result.policy == "TRADING_SESSION"
    assert result.age_hours > 24.0
    assert result.expected_session_date == date(
        2026,
        7,
        31,
    )
    assert result.last_candle_session_date == date(
        2026,
        7,
        31,
    )
    assert result.requires_refresh is False


def test_friday_candle_is_fresh_before_monday_cutoff(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=daily_timestamp(
                2026,
                7,
                31,
            ),
        )
    )

    monday_before_cutoff = datetime(
        2026,
        8,
        3,
        20,
        0,
        tzinfo=timezone.utc,
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=monday_before_cutoff,
    )

    assert result.status == "FRESH"
    assert result.expected_session_date == date(
        2026,
        7,
        31,
    )


def test_friday_candle_is_stale_after_monday_cutoff(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=daily_timestamp(
                2026,
                7,
                31,
            ),
        )
    )

    monday_after_cutoff = datetime(
        2026,
        8,
        3,
        22,
        30,
        tzinfo=timezone.utc,
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=monday_after_cutoff,
    )

    assert result.status == "STALE"
    assert result.expected_session_date == date(
        2026,
        8,
        3,
    )
    assert result.last_candle_session_date == date(
        2026,
        7,
        31,
    )
    assert result.requires_refresh is True


def test_monday_candle_is_fresh_after_cutoff(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=daily_timestamp(
                2026,
                8,
                3,
            ),
        )
    )

    checked_at = datetime(
        2026,
        8,
        3,
        22,
        30,
        tzinfo=timezone.utc,
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=checked_at,
    )

    assert result.status == "FRESH"
    assert result.expected_session_date == date(
        2026,
        8,
        3,
    )


def test_labor_day_is_not_a_trading_day(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=daily_timestamp(
                2026,
                9,
                4,
            ),
        )
    )

    labor_day = datetime(
        2026,
        9,
        7,
        23,
        0,
        tzinfo=timezone.utc,
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=labor_day,
    )

    assert result.status == "FRESH"
    assert result.expected_session_date == date(
        2026,
        9,
        4,
    )


def test_good_friday_is_not_a_trading_day() -> None:
    calendar = UnitedStatesMarketCalendar()

    assert calendar.is_trading_day(
        date(
            2026,
            4,
            3,
        )
    ) is False

    assert calendar.is_trading_day(
        date(
            2026,
            4,
            2,
        )
    ) is True


def test_daily_missing_result_contains_expected_session(
    repository,
) -> None:
    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=SATURDAY_CHECK,
    )

    assert result.status == "MISSING"
    assert result.policy == "TRADING_SESSION"
    assert result.last_candle_at is None
    assert result.age_hours is None
    assert result.expected_session_date == date(
        2026,
        7,
        31,
    )
    assert result.last_candle_session_date is None


def test_non_daily_resolution_uses_age_policy(
    repository,
) -> None:
    repository.save(
        create_candle(
            resolution="H",
            timestamp=(
                SATURDAY_CHECK
                - timedelta(hours=12)
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="H",
        checked_at=SATURDAY_CHECK,
    )

    assert result.status == "FRESH"
    assert result.policy == "AGE"
    assert result.age_hours == pytest.approx(
        12.0
    )
    assert result.expected_session_date is None


def test_non_daily_exact_age_limit_is_fresh(
    repository,
) -> None:
    repository.save(
        create_candle(
            resolution="H",
            timestamp=(
                SATURDAY_CHECK
                - timedelta(hours=24)
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="H",
        checked_at=SATURDAY_CHECK,
    )

    assert result.status == "FRESH"


def test_non_daily_data_over_limit_is_stale(
    repository,
) -> None:
    repository.save(
        create_candle(
            resolution="H",
            timestamp=(
                SATURDAY_CHECK
                - timedelta(
                    hours=24,
                    seconds=1,
                )
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="H",
        checked_at=SATURDAY_CHECK,
    )

    assert result.status == "STALE"
    assert result.requires_refresh is True


def test_custom_maximum_age_applies_to_age_policy(
    repository,
) -> None:
    repository.save(
        create_candle(
            resolution="H",
            timestamp=(
                SATURDAY_CHECK
                - timedelta(hours=10)
            ),
        )
    )

    service = MarketDataFreshnessService(
        repository=repository,
        maximum_age=timedelta(
            hours=8
        ),
    )

    result = service.check(
        symbol="MSFT",
        resolution="H",
        checked_at=SATURDAY_CHECK,
    )

    assert result.status == "STALE"
    assert result.maximum_age_hours == pytest.approx(
        8.0
    )


def test_check_uses_latest_stored_candle(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                timestamp=daily_timestamp(
                    2026,
                    7,
                    29,
                ),
            ),
            create_candle(
                timestamp=daily_timestamp(
                    2026,
                    7,
                    31,
                ),
            ),
            create_candle(
                timestamp=daily_timestamp(
                    2026,
                    7,
                    30,
                ),
            ),
        ]
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=SATURDAY_CHECK,
    )

    assert result.status == "FRESH"
    assert result.last_candle_session_date == date(
        2026,
        7,
        31,
    )


def test_check_many_preserves_symbol_order(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                symbol="MSFT",
                timestamp=daily_timestamp(
                    2026,
                    7,
                    31,
                ),
            ),
            create_candle(
                symbol="AAPL",
                timestamp=daily_timestamp(
                    2026,
                    7,
                    30,
                ),
            ),
        ]
    )

    results = MarketDataFreshnessService(
        repository
    ).check_many(
        symbols=(
            "msft",
            "aapl",
            "googl",
        ),
        resolution="d",
        checked_at=SATURDAY_CHECK,
    )

    assert [
        result.symbol
        for result in results
    ] == [
        "MSFT",
        "AAPL",
        "GOOGL",
    ]

    assert [
        result.status
        for result in results
    ] == [
        "FRESH",
        "STALE",
        "MISSING",
    ]


def test_check_many_rejects_duplicate_symbols(
    repository,
) -> None:
    with pytest.raises(
        ValueError,
        match="unique",
    ):
        MarketDataFreshnessService(
            repository
        ).check_many(
            symbols=(
                "MSFT",
                " msft ",
            ),
            resolution="D",
            checked_at=SATURDAY_CHECK,
        )


def test_check_rejects_future_candle(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=(
                SATURDAY_CHECK
                + timedelta(hours=1)
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="later than checked_at",
    ):
        MarketDataFreshnessService(
            repository
        ).check(
            symbol="MSFT",
            resolution="D",
            checked_at=SATURDAY_CHECK,
        )


def test_check_rejects_naive_checked_at(
    repository,
) -> None:
    naive_checked_at = datetime(
        2026,
        8,
        1,
        12,
        0,
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        MarketDataFreshnessService(
            repository
        ).check(
            symbol="MSFT",
            resolution="D",
            checked_at=naive_checked_at,
        )


def test_service_rejects_invalid_maximum_age(
    repository,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        MarketDataFreshnessService(
            repository=repository,
            maximum_age=timedelta(0),
        )


def test_result_is_json_serializable(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=daily_timestamp(
                2026,
                7,
                31,
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=SATURDAY_CHECK,
    )

    payload = result.to_dict()

    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert payload["status"] == "FRESH"
    assert payload["policy"] == "TRADING_SESSION"
    assert (
        payload["expected_session_date"]
        == "2026-07-31"
    )
    assert (
        payload["last_candle_session_date"]
        == "2026-07-31"
    )
    assert '"last_candle_at"' in serialized


def test_result_rejects_inconsistent_missing_state() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain",
    ):
        MarketDataFreshnessResult(
            symbol="MSFT",
            resolution="D",
            checked_at=SATURDAY_CHECK,
            maximum_age_hours=24.0,
            status="MISSING",
            last_candle_at=(
                SATURDAY_CHECK
                - timedelta(hours=1)
            ),
            age_hours=1.0,
        )