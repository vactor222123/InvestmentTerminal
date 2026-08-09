"""
Tests for deterministic historical evidence-selection policies.
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
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEvidenceSelectionPolicy,
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
    HistoricalPriceEvidenceSelectionService,
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
    service = HistoricalPriceEvidenceSelectionService(
        HistoricalOutcomePriceEvidenceProvider(
            repository
        )
    )
    return database, repository, service


def save_close(
    repository: CandleRepository,
    *,
    timestamp: datetime,
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


def test_exact_timestamp_policy_preserves_sprint_14_behavior(
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
            timestamp=TARGET,
            close=105.0,
        )

        selected = service.select_exact_timestamp(
            instrument_key="IWDA",
            resolution="D",
            target_at=TARGET,
            policy=service.exact_timestamp_close_v1(),
        )

        assert selected is not None
        assert selected.target_at == TARGET
        assert selected.price_point.price == 105.0
        assert (
            selected.selection_policy.identity_key
            == "EXACT_TIMESTAMP_CLOSE@1"
        )
    finally:
        database.close()


def test_session_close_policy_selects_only_explicit_session_close(
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
            timestamp=TARGET,
            close=110.0,
        )

        selected = service.select_session_close(
            instrument_key="IWDA",
            resolution="D",
            session=session(),
            policy=service.session_close_exact_v1(),
        )

        assert selected is not None
        assert selected.target_at == TARGET
        assert selected.price_point.price == 110.0
        assert (
            selected.selection_policy.identity_key
            == "SESSION_CLOSE_EXACT@1"
        )
    finally:
        database.close()


def test_session_close_missing_exact_evidence_returns_none(
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
            timestamp=datetime(
                2026,
                8,
                10,
                15,
                29,
                tzinfo=timezone.utc,
            ),
        )

        selected = service.select_session_close(
            instrument_key="IWDA",
            resolution="D",
            session=session(),
            policy=service.session_close_exact_v1(),
        )

        assert selected is None
    finally:
        database.close()


def test_no_nearest_or_previous_close_fallback(
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
            timestamp=datetime(
                2026,
                8,
                10,
                15,
                29,
                59,
                tzinfo=timezone.utc,
            ),
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
        )

        selected = service.select_session_close(
            instrument_key="IWDA",
            resolution="D",
            session=session(),
            policy=service.session_close_exact_v1(),
        )

        assert selected is None
    finally:
        database.close()


def test_selector_rejects_policy_mismatch(
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
            service.select_session_close(
                instrument_key="IWDA",
                resolution="D",
                session=session(),
                policy=service.exact_timestamp_close_v1(),
            )
    finally:
        database.close()


def test_only_close_price_field_is_supported(
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
            match="only CLOSE",
        ):
            service.select_exact_timestamp(
                instrument_key="IWDA",
                resolution="D",
                target_at=TARGET,
                policy=HistoricalEvidenceSelectionPolicy(
                    policy_id="EXACT_TIMESTAMP_CLOSE",
                    version=1,
                    price_field="OPEN",
                ),
            )
    finally:
        database.close()


def test_selected_evidence_is_json_ready(
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
            timestamp=TARGET,
        )

        selected = service.select_session_close(
            instrument_key="IWDA",
            resolution="D",
            session=session(),
            policy=service.session_close_exact_v1(),
        )

        assert selected is not None
        data = selected.to_dict()
        assert data[
            "selection_policy"
        ][
            "identity_key"
        ] == "SESSION_CLOSE_EXACT@1"
        assert data[
            "price_point"
        ][
            "observed_at"
        ] == TARGET.isoformat()
    finally:
        database.close()
