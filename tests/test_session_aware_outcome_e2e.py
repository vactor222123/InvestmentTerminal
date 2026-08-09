"""
Realistic deterministic E2E coverage for Sprint 15 session-aware outcomes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.methodology_outcome_history import (
    SESSION_METHODOLOGY,
    _methodology_window_calendar,
)
from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
)
from investment_terminal.history.historical_methodology_aware_aggregation import (
    HistoricalMethodologyOutcomeAggregator,
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
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


FRIDAY_ORIGIN = datetime(
    2026,
    8,
    7,
    15,
    30,
    tzinfo=timezone.utc,
)
MONDAY_CLOSE = datetime(
    2026,
    8,
    10,
    15,
    30,
    tzinfo=timezone.utc,
)


def write_session_calendar(
    tmp_path: Path,
) -> Path:
    path = tmp_path / "xetra_sessions.json"
    path.write_text(
        json.dumps(
            {
                "calendar": {
                    "calendar_id": "XETRA",
                    "version": 1,
                    "timezone": "Europe/Berlin",
                    "source": "SPRINT_15_E2E_FIXTURE",
                },
                "sessions": [
                    {
                        "session_key": "XETRA:2026-08-10",
                        "session_date": "2026-08-10",
                        "opens_at": "2026-08-10T09:00:00+02:00",
                        "closes_at": "2026-08-10T17:30:00+02:00",
                    },
                    {
                        "session_key": "XETRA:2026-08-11",
                        "session_date": "2026-08-11",
                        "opens_at": "2026-08-11T09:00:00+02:00",
                        "closes_at": "2026-08-11T17:30:00+02:00",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def recommendation_state() -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id="11111111-1111-4111-8111-111111111111",
        generated_at=FRIDAY_ORIGIN,
        recommendation_key="WORLD",
        present=True,
        symbol="IWDA",
        action="BUY",
        score=80.0,
        confidence=0.8,
    )


def prepare_stack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    market_path = tmp_path / "market.db"
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        market_path,
    )
    database = Database()
    database.initialize()
    repository = CandleRepository(
        database
    )

    methodology, window, calendar = _methodology_window_calendar(
        methodology_name=SESSION_METHODOLOGY,
        window_value=1,
        session_calendar_path=write_session_calendar(
            tmp_path
        ),
    )

    raw_provider = HistoricalOutcomePriceEvidenceProvider(
        repository
    )
    selection_service = HistoricalPriceEvidenceSelectionService(
        raw_provider
    )
    methodology_evidence_service = (
        HistoricalMethodologyAwarePriceEvidenceService(
            selection_service
        )
    )
    observation_service = HistoricalMethodologyAwareObservationService(
        elapsed_window_policy=HistoricalObservationWindowPolicy(),
        trading_session_window_policy=HistoricalTradingSessionWindowPolicy(
            calendar
        ),
        selection_service=selection_service,
        methodology_evidence_service=methodology_evidence_service,
        calculator=HistoricalRecommendationOutcomeCalculator(),
    )

    return (
        database,
        repository,
        methodology,
        window,
        calendar,
        observation_service,
    )


def save_close(
    repository: CandleRepository,
    *,
    timestamp: datetime,
    price: float,
) -> None:
    repository.save(
        Candle(
            symbol="IWDA",
            resolution="D",
            timestamp=timestamp,
            open_price=price,
            high_price=price,
            low_price=price,
            close_price=price,
            volume=1000.0,
            currency="EUR",
        )
    )


def test_friday_to_monday_session_close_is_complete_and_aggregates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        database,
        repository,
        methodology,
        window,
        calendar,
        observation_service,
    ) = prepare_stack(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
            timestamp=FRIDAY_ORIGIN,
            price=100.0,
        )
        save_close(
            repository,
            timestamp=MONDAY_CLOSE,
            price=105.0,
        )

        result = observation_service.observe(
            state=recommendation_state(),
            window=window,
            methodology=methodology,
            as_of=MONDAY_CLOSE,
            resolution="D",
        )

        assert result.observation.status == "COMPLETE"
        assert result.outcome is not None
        assert result.outcome.price_change_fraction == pytest.approx(
            0.05
        )

        assert result.methodology.identity_key == (
            "TRADING_SESSIONS_EXACT_CLOSE@1"
        )
        assert (
            result.endpoint_methodology_evidence
            is not None
        )
        assert (
            result.endpoint_methodology_evidence.session
            is not None
        )
        assert (
            result.endpoint_methodology_evidence.session.session_key
            == "XETRA:2026-08-10"
        )
        assert (
            result.endpoint_methodology_evidence.session.calendar.source
            == "SPRINT_15_E2E_FIXTURE"
        )
        assert (
            result.endpoint_methodology_evidence.selected_evidence
            .selection_policy.identity_key
            == "SESSION_CLOSE_EXACT@1"
        )

        summary = HistoricalMethodologyOutcomeAggregator().summarize_one(
            (result,)
        )
        assert summary.methodology.identity_key == (
            "TRADING_SESSIONS_EXACT_CLOSE@1"
        )
        assert summary.total_count == 1
        assert summary.complete_count == 1
        assert summary.coverage_fraction == 1.0
        assert summary.mean_price_change_fraction == pytest.approx(
            0.05
        )

        report = {
            "methodology": methodology.to_dict(),
            "window": window.to_dict(),
            "session_calendar": calendar.identity.to_dict(),
            "observations": [
                result.to_dict()
            ],
            "summary": summary.to_dict(),
        }
        rendered = json.loads(
            json.dumps(
                report,
                allow_nan=False,
            )
        )

        assert rendered[
            "methodology"
        ][
            "identity_key"
        ] == "TRADING_SESSIONS_EXACT_CLOSE@1"
        assert rendered[
            "session_calendar"
        ][
            "identity_key"
        ] == "XETRA@1"
        assert rendered[
            "observations"
        ][
            0
        ][
            "endpoint_methodology_evidence"
        ][
            "session"
        ][
            "session_key"
        ] == "XETRA:2026-08-10"
    finally:
        database.close()


def test_session_window_is_not_mature_before_monday_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        database,
        repository,
        methodology,
        window,
        _,
        observation_service,
    ) = prepare_stack(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
            timestamp=FRIDAY_ORIGIN,
            price=100.0,
        )

        result = observation_service.observe(
            state=recommendation_state(),
            window=window,
            methodology=methodology,
            as_of=datetime(
                2026,
                8,
                10,
                15,
                29,
                59,
                tzinfo=timezone.utc,
            ),
            resolution="D",
        )

        assert result.observation.status == "NOT_MATURE"
        assert result.outcome is None
        assert result.endpoint_methodology_evidence is None
    finally:
        database.close()


def test_missing_exact_monday_close_evidence_is_partial_without_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        database,
        repository,
        methodology,
        window,
        _,
        observation_service,
    ) = prepare_stack(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
            timestamp=FRIDAY_ORIGIN,
            price=100.0,
        )
        save_close(
            repository,
            timestamp=datetime(
                2026,
                8,
                10,
                15,
                29,
                59,
                tzinfo=timezone.utc,
            ),
            price=104.0,
        )
        save_close(
            repository,
            timestamp=datetime(
                2026,
                8,
                10,
                15,
                30,
                1,
                tzinfo=timezone.utc,
            ),
            price=106.0,
        )

        result = observation_service.observe(
            state=recommendation_state(),
            window=window,
            methodology=methodology,
            as_of=MONDAY_CLOSE,
            resolution="D",
        )

        assert result.observation.status == "PARTIAL"
        assert result.outcome is None
        assert result.endpoint_methodology_evidence is None
        assert (
            result.observation.evidence
            is not None
        )
        assert (
            result.observation.evidence.endpoint_price
            is None
        )
    finally:
        database.close()


def test_outcome_flow_does_not_create_history_outcome_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        database,
        repository,
        methodology,
        window,
        _,
        observation_service,
    ) = prepare_stack(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
            timestamp=FRIDAY_ORIGIN,
            price=100.0,
        )
        save_close(
            repository,
            timestamp=MONDAY_CLOSE,
            price=105.0,
        )

        result = observation_service.observe(
            state=recommendation_state(),
            window=window,
            methodology=methodology,
            as_of=MONDAY_CLOSE,
            resolution="D",
        )
        assert result.observation.status == "COMPLETE"

        rows = database.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()
        table_names = {
            row[0]
            for row in rows
        }

        assert not any(
            "outcome" in name.lower()
            for name in table_names
        )
    finally:
        database.close()
