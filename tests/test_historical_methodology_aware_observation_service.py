"""
Focused tests for methodology-aware historical outcome observation.
"""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
)
from investment_terminal.history.historical_local_session_calendar import (
    HistoricalLocalSessionCalendar,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
    HistoricalSessionCalendarIdentity,
)
from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationService,
)
from investment_terminal.history.historical_methodology_aware_price_evidence import (
    HistoricalMethodologyAwarePriceEvidenceService,
)
from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
)
from investment_terminal.history.historical_trading_session_window import (
    HistoricalTradingSessionWindowPolicy,
)
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import CandleRepository


ORIGIN = datetime(2026, 8, 7, 15, 30, tzinfo=timezone.utc)
MONDAY_CLOSE = datetime(2026, 8, 10, 15, 30, tzinfo=timezone.utc)
SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"


def state() -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=SNAPSHOT_ID,
        generated_at=ORIGIN,
        recommendation_key="WORLD",
        present=True,
        symbol="IWDA",
        action="BUY",
        score=80.0,
        confidence=0.8,
    )


def session_methodology() -> HistoricalOutcomeMethodology:
    return HistoricalOutcomeMethodology(
        methodology_id="TRADING_SESSIONS_EXACT_CLOSE",
        version=1,
        window_kind="TRADING_SESSIONS",
        endpoint_policy=HistoricalEndpointPolicy(
            policy_id="TRADING_SESSION_CLOSE",
            version=1,
        ),
        evidence_selection_policy=(
            HistoricalPriceEvidenceSelectionService.session_close_exact_v1()
        ),
    )


def prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(Settings, "DATABASE_PATH", tmp_path / "market.db")
    database = Database()
    database.initialize()
    repository = CandleRepository(database)

    identity = HistoricalSessionCalendarIdentity(
        calendar_id="XETRA",
        version=1,
        timezone="Europe/Berlin",
        source="LOCAL_SESSION_FIXTURE",
    )
    monday = HistoricalMarketSession(
        session_key="XETRA:2026-08-10",
        session_date=date(2026, 8, 10),
        opens_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
        closes_at=MONDAY_CLOSE,
        calendar=identity,
    )
    calendar = HistoricalLocalSessionCalendar(
        identity=identity,
        sessions=(monday,),
    )

    raw = HistoricalOutcomePriceEvidenceProvider(repository)
    selection = HistoricalPriceEvidenceSelectionService(raw)
    methodology_evidence = HistoricalMethodologyAwarePriceEvidenceService(
        selection
    )
    service = HistoricalMethodologyAwareObservationService(
        elapsed_window_policy=HistoricalObservationWindowPolicy(),
        trading_session_window_policy=HistoricalTradingSessionWindowPolicy(
            calendar
        ),
        selection_service=selection,
        methodology_evidence_service=methodology_evidence,
        calculator=HistoricalRecommendationOutcomeCalculator(),
    )
    return database, repository, service


def save_close(repository: CandleRepository, timestamp: datetime, close: float):
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
            currency="EUR",
        )
    )


def test_trading_session_methodology_completes_with_explicit_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(tmp_path, monkeypatch)
    try:
        save_close(repository, ORIGIN, 100.0)
        save_close(repository, MONDAY_CLOSE, 105.0)

        result = service.observe(
            state=state(),
            window=HistoricalObservationWindow(
                kind="TRADING_SESSIONS",
                value=1,
            ),
            methodology=session_methodology(),
            as_of=MONDAY_CLOSE,
            resolution="D",
        )

        assert result.observation.status == "COMPLETE"
        assert result.outcome is not None
        assert result.outcome.price_change_fraction == pytest.approx(0.05)
        assert (
            result.origin_selected_evidence.selection_policy.identity_key
            == "EXACT_TIMESTAMP_CLOSE@1"
        )
        assert (
            result.endpoint_methodology_evidence.methodology.identity_key
            == "TRADING_SESSIONS_EXACT_CLOSE@1"
        )
        assert (
            result.endpoint_methodology_evidence.session.session_key
            == "XETRA:2026-08-10"
        )
    finally:
        database.close()


def test_session_observation_is_not_mature_before_session_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(tmp_path, monkeypatch)
    try:
        save_close(repository, ORIGIN, 100.0)

        result = service.observe(
            state=state(),
            window=HistoricalObservationWindow(
                kind="TRADING_SESSIONS",
                value=1,
            ),
            methodology=session_methodology(),
            as_of=datetime(
                2026, 8, 10, 15, 29, 59, tzinfo=timezone.utc
            ),
            resolution="D",
        )

        assert result.observation.status == "NOT_MATURE"
        assert result.outcome is None
        assert result.endpoint_methodology_evidence is None
    finally:
        database.close()


def test_elapsed_exact_methodology_remains_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(tmp_path, monkeypatch)
    try:
        endpoint = datetime(2026, 8, 8, 15, 30, tzinfo=timezone.utc)
        save_close(repository, ORIGIN, 100.0)
        save_close(repository, endpoint, 102.0)

        result = service.observe(
            state=state(),
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=1,
            ),
            methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
            as_of=endpoint,
            resolution="D",
        )

        assert result.observation.status == "COMPLETE"
        assert result.outcome is not None
        assert result.outcome.price_change_fraction == pytest.approx(0.02)
        assert result.endpoint_methodology_evidence.session is None
    finally:
        database.close()


def test_window_kind_must_match_methodology(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, service = prepare(tmp_path, monkeypatch)
    try:
        with pytest.raises(
            ValueError,
            match="window_kind must match",
        ):
            service.observe(
                state=state(),
                window=HistoricalObservationWindow(
                    kind="ELAPSED_DAYS",
                    value=1,
                ),
                methodology=session_methodology(),
                as_of=MONDAY_CLOSE,
                resolution="D",
            )
    finally:
        database.close()


def test_missing_endpoint_exact_evidence_is_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(tmp_path, monkeypatch)
    try:
        save_close(repository, ORIGIN, 100.0)

        result = service.observe(
            state=state(),
            window=HistoricalObservationWindow(
                kind="TRADING_SESSIONS",
                value=1,
            ),
            methodology=session_methodology(),
            as_of=MONDAY_CLOSE,
            resolution="D",
        )

        assert result.observation.status == "PARTIAL"
        assert result.outcome is None
    finally:
        database.close()


def test_json_output_contains_methodology_and_both_selection_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(tmp_path, monkeypatch)
    try:
        save_close(repository, ORIGIN, 100.0)
        save_close(repository, MONDAY_CLOSE, 105.0)

        result = service.observe(
            state=state(),
            window=HistoricalObservationWindow(
                kind="TRADING_SESSIONS",
                value=1,
            ),
            methodology=session_methodology(),
            as_of=MONDAY_CLOSE,
            resolution="D",
        )
        data = result.to_dict()

        assert data["methodology"]["identity_key"] == (
            "TRADING_SESSIONS_EXACT_CLOSE@1"
        )
        assert data["origin_selected_evidence"][
            "selection_policy"
        ]["identity_key"] == "EXACT_TIMESTAMP_CLOSE@1"
        assert data["endpoint_methodology_evidence"][
            "selected_evidence"
        ]["selection_policy"]["identity_key"] == "SESSION_CLOSE_EXACT@1"
    finally:
        database.close()
