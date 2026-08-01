"""
Tests for MarketDataFreshnessService.
"""

import json
from datetime import (
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
)


CHECKED_AT = datetime(
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


def test_check_returns_fresh_result(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=(
                CHECKED_AT
                - timedelta(hours=12)
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol=" msft ",
        resolution=" d ",
        checked_at=CHECKED_AT,
    )

    assert result.symbol == "MSFT"
    assert result.resolution == "D"
    assert result.status == "FRESH"
    assert result.is_fresh is True
    assert result.is_stale is False
    assert result.is_missing is False
    assert result.requires_refresh is False
    assert result.age_hours == pytest.approx(
        12.0
    )
    assert result.maximum_age_hours == pytest.approx(
        24.0
    )


def test_check_treats_exact_limit_as_fresh(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=(
                CHECKED_AT
                - timedelta(hours=24)
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.status == "FRESH"
    assert result.age_hours == pytest.approx(
        24.0
    )


def test_check_returns_stale_result(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=(
                CHECKED_AT
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
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.status == "STALE"
    assert result.is_fresh is False
    assert result.is_stale is True
    assert result.requires_refresh is True
    assert result.age_hours > 24.0


def test_check_returns_missing_result(
    repository,
) -> None:
    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.status == "MISSING"
    assert result.last_candle_at is None
    assert result.age_hours is None
    assert result.is_missing is True
    assert result.requires_refresh is True


def test_check_uses_custom_maximum_age(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=(
                CHECKED_AT
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
        resolution="D",
        checked_at=CHECKED_AT,
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
                timestamp=(
                    CHECKED_AT
                    - timedelta(hours=30)
                ),
            ),
            create_candle(
                timestamp=(
                    CHECKED_AT
                    - timedelta(hours=8)
                ),
            ),
            create_candle(
                timestamp=(
                    CHECKED_AT
                    - timedelta(hours=48)
                ),
            ),
        ]
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    assert result.status == "FRESH"
    assert result.age_hours == pytest.approx(
        8.0
    )


def test_check_many_preserves_symbol_order(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                symbol="MSFT",
                timestamp=(
                    CHECKED_AT
                    - timedelta(hours=8)
                ),
            ),
            create_candle(
                symbol="AAPL",
                timestamp=(
                    CHECKED_AT
                    - timedelta(hours=30)
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
        checked_at=CHECKED_AT,
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
            checked_at=CHECKED_AT,
        )


def test_check_rejects_future_candle(
    repository,
) -> None:
    repository.save(
        create_candle(
            timestamp=(
                CHECKED_AT
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
            checked_at=CHECKED_AT,
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
            timestamp=(
                CHECKED_AT
                - timedelta(hours=6)
            ),
        )
    )

    result = MarketDataFreshnessService(
        repository
    ).check(
        symbol="MSFT",
        resolution="D",
        checked_at=CHECKED_AT,
    )

    payload = result.to_dict()

    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert payload["status"] == "FRESH"
    assert payload["age_hours"] == pytest.approx(
        6.0
    )
    assert payload["requires_refresh"] is False
    assert '"last_candle_at"' in serialized


def test_result_rejects_inconsistent_missing_state() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain",
    ):
        MarketDataFreshnessResult(
            symbol="MSFT",
            resolution="D",
            checked_at=CHECKED_AT,
            maximum_age_hours=24.0,
            status="MISSING",
            last_candle_at=(
                CHECKED_AT
                - timedelta(hours=1)
            ),
            age_hours=1.0,
        )