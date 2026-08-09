"""
Tests for methodology-aware historical price evidence.
"""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
    HistoricalSessionCalendarIdentity,
)
from investment_terminal.history.historical_methodology_aware_price_evidence import (
    HistoricalMethodologyAwarePriceEvidenceService,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalEvidenceSelectionPolicy,
    HistoricalOutcomeMethodology,
)
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
    10,
    15,
    30,
    tzinfo=timezone.utc,
)


def prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    Database,
    CandleRepository,
    HistoricalMethodologyAwarePriceEvidenceService,
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
    service = HistoricalMethodologyAwarePriceEvidenceService(
        HistoricalPriceEvidenceSelectionService(
            HistoricalOutcomePriceEvidenceProvider(
                repository
            )
        )
    )
    return database, repository, service


def save_close(
    repository: CandleRepository,
    *,
    timestamp: datetime = TARGET,
    close: float = 100.0,
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
            currency="EUR",
        )
    )


def session() -> HistoricalMarketSession:
    calendar = HistoricalSessionCalendarIdentity(
        calendar_id="XETRA",
        version=1,
        timezone="Europe/Berlin",
        source="LOCAL_SESSION_FIXTURE",
    )
    return HistoricalMarketSession(
        session_key="XETRA:2026-08-10",
        session_date=date(
            2026,
            8,
            10,
        ),
        opens_at=datetime(
            2026,
            8,
            10,
            7,
            0,
            tzinfo=timezone.utc,
        ),
        closes_at=TARGET,
        calendar=calendar,
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


def test_exact_methodology_preserves_sprint_14_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
            close=105.0,
        )
        methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()

        evidence = service.select_for_exact_timestamp(
            methodology=methodology,
            instrument_key="IWDA",
            resolution="D",
            target_at=TARGET,
        )

        assert evidence is not None
        assert (
            evidence.methodology.identity_key
            == "ELAPSED_DAYS_EXACT_CLOSE@1"
        )
        assert evidence.intended_endpoint_at == TARGET
        assert evidence.observed_at == TARGET
        assert evidence.session is None
        assert evidence.selected_evidence.price_point.price == 105.0
    finally:
        database.close()


def test_session_methodology_preserves_session_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
            close=110.0,
        )
        endpoint_session = session()

        evidence = service.select_for_session_close(
            methodology=session_methodology(),
            instrument_key="IWDA",
            resolution="D",
            session=endpoint_session,
        )

        assert evidence is not None
        assert (
            evidence.methodology.identity_key
            == "TRADING_SESSIONS_EXACT_CLOSE@1"
        )
        assert evidence.session == endpoint_session
        assert evidence.intended_endpoint_at == endpoint_session.closes_at
        assert evidence.observed_at == endpoint_session.closes_at
        assert (
            evidence.selected_evidence.selection_policy.identity_key
            == "SESSION_CLOSE_EXACT@1"
        )
    finally:
        database.close()


def test_missing_exact_evidence_remains_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        evidence = service.select_for_session_close(
            methodology=session_methodology(),
            instrument_key="IWDA",
            resolution="D",
            session=session(),
        )

        assert evidence is None
    finally:
        database.close()


def test_methodology_policy_mismatch_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, _, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        with pytest.raises(
            ValueError,
            match="does not match requested selector",
        ):
            service.select_for_session_close(
                methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
                instrument_key="IWDA",
                resolution="D",
                session=session(),
            )
    finally:
        database.close()


def test_output_is_json_ready_with_full_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
        )

        evidence = service.select_for_session_close(
            methodology=session_methodology(),
            instrument_key="IWDA",
            resolution="D",
            session=session(),
        )

        assert evidence is not None
        data = evidence.to_dict()

        assert data[
            "methodology"
        ][
            "identity_key"
        ] == "TRADING_SESSIONS_EXACT_CLOSE@1"
        assert data[
            "session"
        ][
            "session_key"
        ] == "XETRA:2026-08-10"
        assert data[
            "selected_evidence"
        ][
            "selection_policy"
        ][
            "identity_key"
        ] == "SESSION_CLOSE_EXACT@1"
        assert data[
            "selected_evidence"
        ][
            "price_point"
        ][
            "source"
        ] == "LOCAL_CANDLE_REPOSITORY_CLOSE"
    finally:
        database.close()


def test_selected_policy_must_match_methodology_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, repository, service = prepare(
        tmp_path,
        monkeypatch,
    )
    try:
        save_close(
            repository,
        )
        bad_methodology = HistoricalOutcomeMethodology(
            methodology_id="BAD",
            version=1,
            window_kind="TRADING_SESSIONS",
            endpoint_policy=HistoricalEndpointPolicy(
                policy_id="TRADING_SESSION_CLOSE",
                version=1,
            ),
            evidence_selection_policy=HistoricalEvidenceSelectionPolicy(
                policy_id="SESSION_CLOSE_EXACT",
                version=1,
                price_field="OPEN",
            ),
        )

        with pytest.raises(
            ValueError,
            match="only CLOSE",
        ):
            service.select_for_session_close(
                methodology=bad_methodology,
                instrument_key="IWDA",
                resolution="D",
                session=session(),
            )
    finally:
        database.close()
