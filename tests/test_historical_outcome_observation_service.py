"""
Tests for historical outcome observation orchestration.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_observation_service import (
    HistoricalOutcomeObservationService,
)
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
)
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"
ORIGIN = datetime(
    2026,
    8,
    3,
    20,
    0,
    tzinfo=timezone.utc,
)
ENDPOINT = ORIGIN + timedelta(
    days=5
)


def prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    Database,
    CandleRepository,
    HistoricalOutcomeObservationService,
]:
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        tmp_path / "market.db",
    )
    database = Database()
    database.initialize()
    repository = CandleRepository(
        database
    )
    return (
        database,
        repository,
        HistoricalOutcomeObservationService(
            window_policy=HistoricalObservationWindowPolicy(),
            price_provider=HistoricalOutcomePriceEvidenceProvider(
                repository
            ),
            calculator=HistoricalRecommendationOutcomeCalculator(),
        ),
    )


def state(
    *,
    present: bool = True,
    symbol: str | None = "IWDA",
) -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=SNAPSHOT_ID,
        generated_at=ORIGIN,
        recommendation_key="WORLD",
        present=present,
        symbol=(
            symbol
            if present
            else None
        ),
        action=(
            "BUY"
            if present
            else None
        ),
        score=(
            80.0
            if present
            else None
        ),
        confidence=(
            0.8
            if present
            else None
        ),
    )


def save_candle(
    repository: CandleRepository,
    *,
    timestamp: datetime,
    close: float,
    currency: str = "EUR",
) -> None:
    repository.save(
        Candle(
            symbol="IWDA",
            resolution="D",
            timestamp=timestamp,
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=1000.0,
            currency=currency,
        )
    )


def window() -> HistoricalObservationWindow:
    return HistoricalObservationWindow(
        kind="ELAPSED_DAYS",
        value=5,
    )


def test_complete_observation_calculates_raw_price_movement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_candle(
            repository,
            timestamp=ORIGIN,
            close=100.0,
        )
        save_candle(
            repository,
            timestamp=ENDPOINT,
            close=105.0,
        )

        result = service.observe(
            state=state(),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.COMPLETE
        )
        assert result.outcome is not None
        assert result.outcome.price_change == 5.0
        assert result.outcome.price_change_fraction == pytest.approx(
            0.05
        )
        assert result.observation.evidence is not None
        assert result.observation.evidence.origin_currency == "EUR"
        assert result.observation.evidence.endpoint_resolution == "D"
        assert "not portfolio performance" in (
            result.observation.warnings[0]
        )
    finally:
        database.close()


def test_not_mature_does_not_read_endpoint_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_candle(
            repository,
            timestamp=ORIGIN,
            close=100.0,
        )

        result = service.observe(
            state=state(),
            window=window(),
            as_of=ENDPOINT - timedelta(
                seconds=1
            ),
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.NOT_MATURE
        )
        assert result.outcome is None
        assert result.observation.evidence is not None
        assert result.observation.evidence.origin_price == 100.0
        assert result.observation.evidence.endpoint_price is None
    finally:
        database.close()


def test_missing_one_price_is_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_candle(
            repository,
            timestamp=ORIGIN,
            close=100.0,
        )

        result = service.observe(
            state=state(),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.PARTIAL
        )
        assert result.outcome is None
        assert "endpoint" in result.observation.warnings[0]
    finally:
        database.close()


def test_missing_both_prices_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        result = service.observe(
            state=state(),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.UNAVAILABLE
        )
        assert result.outcome is None
    finally:
        database.close()


def test_currency_mismatch_is_partial_without_fx_assumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_candle(
            repository,
            timestamp=ORIGIN,
            close=100.0,
            currency="EUR",
        )
        save_candle(
            repository,
            timestamp=ENDPOINT,
            close=105.0,
            currency="USD",
        )

        result = service.observe(
            state=state(),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.PARTIAL
        )
        assert result.outcome is None
        assert "FX-adjusted" in result.observation.warnings[0]
    finally:
        database.close()


def test_absent_recommendation_is_unavailable_without_price_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        result = service.observe(
            state=state(
                present=False
            ),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.UNAVAILABLE
        )
        assert result.observation.evidence is None
        assert result.outcome is None
    finally:
        database.close()


def test_present_recommendation_without_symbol_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        result = service.observe(
            state=state(
                symbol=None
            ),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )

        assert result.observation.status == (
            HistoricalRecommendationObservation.UNAVAILABLE
        )
        assert result.outcome is None
        assert "no symbol" in result.observation.warnings[0]
    finally:
        database.close()


def test_result_is_json_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_candle(
            repository,
            timestamp=ORIGIN,
            close=100.0,
        )
        save_candle(
            repository,
            timestamp=ENDPOINT,
            close=105.0,
        )

        result = service.observe(
            state=state(),
            window=window(),
            as_of=ENDPOINT,
            resolution="D",
        )
        data = result.to_dict()

        assert data["observation"]["status"] == "COMPLETE"
        assert data["outcome"]["price_change_fraction"] == pytest.approx(
            0.05
        )
    finally:
        database.close()
