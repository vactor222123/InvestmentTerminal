"""
Tests for the local historical outcome price-evidence boundary.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
)
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


TARGET = datetime(
    2026,
    8,
    3,
    20,
    0,
    tzinfo=timezone.utc,
)


def prepare_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Database, CandleRepository]:
    database_path = tmp_path / "market.db"
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        database_path,
    )

    database = Database()
    database.initialize()
    return (
        database,
        CandleRepository(
            database
        ),
    )


def candle(
    *,
    timestamp: datetime,
    close_price: float = 105.0,
) -> Candle:
    return Candle(
        symbol="IWDA",
        resolution="D",
        timestamp=timestamp,
        open_price=100.0,
        high_price=max(
            106.0,
            close_price,
        ),
        low_price=99.0,
        close_price=close_price,
        volume=1000.0,
        currency="EUR",
    )


def test_exact_match_returns_close_price_with_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        repository.save(
            candle(
                timestamp=TARGET,
            )
        )

        point = HistoricalOutcomePriceEvidenceProvider(
            repository
        ).get_exact(
            instrument_key=" iwda ",
            resolution=" d ",
            observed_at=TARGET,
        )

        assert point is not None
        assert point.instrument_key == "IWDA"
        assert point.observed_at == TARGET
        assert point.price == 105.0
        assert point.currency == "EUR"
        assert point.resolution == "D"
        assert point.source == (
            "LOCAL_CANDLE_REPOSITORY_CLOSE"
        )
    finally:
        database.close()


def test_equal_instant_with_different_offset_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        repository.save(
            candle(
                timestamp=TARGET,
            )
        )

        requested = datetime.fromisoformat(
            "2026-08-03T22:00:00+02:00"
        )

        point = HistoricalOutcomePriceEvidenceProvider(
            repository
        ).get_exact(
            instrument_key="IWDA",
            resolution="D",
            observed_at=requested,
        )

        assert point is not None
        assert point.observed_at == TARGET
    finally:
        database.close()


def test_missing_exact_timestamp_returns_none_without_nearest_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        repository.save(
            candle(
                timestamp=TARGET,
            )
        )

        point = HistoricalOutcomePriceEvidenceProvider(
            repository
        ).get_exact(
            instrument_key="IWDA",
            resolution="D",
            observed_at=datetime(
                2026,
                8,
                4,
                20,
                0,
                tzinfo=timezone.utc,
            ),
        )

        assert point is None
    finally:
        database.close()


def test_provider_rejects_naive_requested_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        provider = HistoricalOutcomePriceEvidenceProvider(
            repository
        )

        with pytest.raises(
            ValueError,
            match="observed_at must be timezone-aware",
        ):
            provider.get_exact(
                instrument_key="IWDA",
                resolution="D",
                observed_at=datetime(
                    2026,
                    8,
                    3,
                    20,
                    0,
                ),
            )
    finally:
        database.close()


def test_provider_rejects_naive_stored_candle_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        repository.save(
            candle(
                timestamp=datetime(
                    2026,
                    8,
                    3,
                    20,
                    0,
                ),
            )
        )

        with pytest.raises(
            ValueError,
            match="stored candle timestamp must be timezone-aware",
        ):
            HistoricalOutcomePriceEvidenceProvider(
                repository
            ).get_exact(
                instrument_key="IWDA",
                resolution="D",
                observed_at=TARGET,
            )
    finally:
        database.close()


def test_provider_does_not_use_latest_candle_as_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        repository.save(
            candle(
                timestamp=TARGET,
            )
        )
        repository.save(
            candle(
                timestamp=datetime(
                    2026,
                    8,
                    10,
                    20,
                    0,
                    tzinfo=timezone.utc,
                ),
                close_price=120.0,
            )
        )

        point = HistoricalOutcomePriceEvidenceProvider(
            repository
        ).get_exact(
            instrument_key="IWDA",
            resolution="D",
            observed_at=datetime(
                2026,
                8,
                5,
                20,
                0,
                tzinfo=timezone.utc,
            ),
        )

        assert point is None
    finally:
        database.close()


def test_price_point_is_json_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository = prepare_repository(
        tmp_path,
        monkeypatch,
    )
    try:
        repository.save(
            candle(
                timestamp=TARGET,
            )
        )

        point = HistoricalOutcomePriceEvidenceProvider(
            repository
        ).get_exact(
            instrument_key="IWDA",
            resolution="D",
            observed_at=TARGET,
        )

        assert point is not None
        assert point.to_dict() == {
            "instrument_key": "IWDA",
            "observed_at": TARGET.isoformat(),
            "price": 105.0,
            "currency": "EUR",
            "resolution": "D",
            "source": "LOCAL_CANDLE_REPOSITORY_CLOSE",
        }
    finally:
        database.close()
