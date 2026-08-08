"""
Tests for the read-only historical recommendation outcome CLI.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.outcome_history import (
    main,
)
from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


IDS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)
T0 = datetime(
    2026,
    8,
    1,
    20,
    0,
    tzinfo=timezone.utc,
)
T1 = T0 + timedelta(
    days=10
)


def prepare_history(
    tmp_path: Path,
) -> Path:
    path = tmp_path / "history.db"
    store = HistoricalSQLiteStore(
        path
    )
    snapshots = HistoricalSnapshotRepository(
        store
    )

    snapshots.add_many(
        (
            _snapshot(
                IDS[0],
                T0,
                0,
            ),
            _snapshot(
                IDS[1],
                T1,
                1,
            ),
        )
    )

    with store.connect() as connection:
        for (
            snapshot_id,
            action,
            score,
        ) in (
            (
                IDS[0],
                "BUY",
                80.0,
            ),
            (
                IDS[1],
                "HOLD",
                75.0,
            ),
        ):
            connection.execute(
                """
                INSERT INTO recommendations (
                    snapshot_id,
                    recommendation_key,
                    symbol,
                    action,
                    score,
                    confidence,
                    rationale,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    "WORLD",
                    "IWDA",
                    action,
                    score,
                    0.8,
                    None,
                    json.dumps(
                        {
                            "recommendation_id": "WORLD",
                            "symbol": "IWDA",
                            "recommendation": action,
                        }
                    ),
                ),
            )

    return path


def prepare_market(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    path = tmp_path / "market.db"
    previous = Settings.DATABASE_PATH
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        path,
    )
    database = Database()
    database.initialize()
    repository = CandleRepository(
        database
    )

    try:
        for timestamp, close in (
            (
                T0,
                100.0,
            ),
            (
                T0 + timedelta(
                    days=5
                ),
                105.0,
            ),
            (
                T1,
                110.0,
            ),
            (
                T1 + timedelta(
                    days=5
                ),
                108.0,
            ),
        ):
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
    finally:
        database.close()
        monkeypatch.setattr(
            Settings,
            "DATABASE_PATH",
            previous,
        )

    return path


def test_json_output_contains_observations_and_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history = prepare_history(
        tmp_path
    )
    market = prepare_market(
        tmp_path,
        monkeypatch,
    )

    main(
        (
            "--history-database",
            str(
                history
            ),
            "--market-database",
            str(
                market
            ),
            "--recommendation-key",
            "WORLD",
            "--window-days",
            "5",
            "--as-of",
            (
                T1
                + timedelta(
                    days=5
                )
            ).isoformat(),
            "--resolution",
            "D",
            "--json",
        )
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "command"
    ] == "historical_outcomes"
    assert report[
        "count"
    ] == 2
    assert [
        item[
            "observation"
        ][
            "status"
        ]
        for item in report[
            "observations"
        ]
    ] == [
        "COMPLETE",
        "COMPLETE",
    ]
    assert report[
        "summary"
    ][
        "complete_count"
    ] == 2
    assert report[
        "summary"
    ][
        "coverage_fraction"
    ] == 1.0


def test_as_of_can_leave_later_observation_not_mature(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history = prepare_history(
        tmp_path
    )
    market = prepare_market(
        tmp_path,
        monkeypatch,
    )

    main(
        (
            "--history-database",
            str(
                history
            ),
            "--market-database",
            str(
                market
            ),
            "--recommendation-key",
            "WORLD",
            "--window-days",
            "5",
            "--as-of",
            (
                T1
                + timedelta(
                    days=4
                )
            ).isoformat(),
            "--json",
        )
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert [
        item[
            "observation"
        ][
            "status"
        ]
        for item in report[
            "observations"
        ]
    ] == [
        "COMPLETE",
        "NOT_MATURE",
    ]
    assert report[
        "summary"
    ][
        "complete_count"
    ] == 1
    assert report[
        "summary"
    ][
        "not_mature_count"
    ] == 1


def test_unknown_recommendation_returns_empty_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history = prepare_history(
        tmp_path
    )
    market = prepare_market(
        tmp_path,
        monkeypatch,
    )

    main(
        (
            "--history-database",
            str(
                history
            ),
            "--market-database",
            str(
                market
            ),
            "--recommendation-key",
            "UNKNOWN",
            "--window-days",
            "5",
            "--as-of",
            (
                T1
                + timedelta(
                    days=5
                )
            ).isoformat(),
            "--json",
        )
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "count"
    ] == 0
    assert report[
        "summary"
    ][
        "total_count"
    ] == 0
    assert report[
        "summary"
    ][
        "coverage_fraction"
    ] is None


def test_human_output_keeps_metric_semantics_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history = prepare_history(
        tmp_path
    )
    market = prepare_market(
        tmp_path,
        monkeypatch,
    )

    main(
        (
            "--history-database",
            str(
                history
            ),
            "--market-database",
            str(
                market
            ),
            "--recommendation-key",
            "WORLD",
            "--window-days",
            "5",
            "--as-of",
            (
                T1
                + timedelta(
                    days=5
                )
            ).isoformat(),
        )
    )

    output = capsys.readouterr().out

    assert "Historical recommendation outcomes" in output
    assert "not portfolio performance" in output
    assert "evidence of causality" in output


def test_missing_market_database_is_actionable_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history = prepare_history(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ):
        main(
            (
                "--history-database",
                str(
                    history
                ),
                "--market-database",
                str(
                    tmp_path
                    / "missing.db"
                ),
                "--recommendation-key",
                "WORLD",
                "--window-days",
                "5",
                "--as-of",
                T1.isoformat(),
            )
        )

    assert "Market database does not exist" in (
        capsys.readouterr().err
    )


def test_window_days_must_be_positive() -> None:
    with pytest.raises(
        SystemExit,
    ):
        main(
            (
                "--recommendation-key",
                "WORLD",
                "--window-days",
                "0",
                "--as-of",
                T1.isoformat(),
            )
        )


def _snapshot(
    snapshot_id: str,
    generated_at: datetime,
    index: int,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=f"review-{index}",
        package_schema_version="1.0",
        product_version="0.14.0",
        generated_at=generated_at,
        archived_at=generated_at + timedelta(
            minutes=1
        ),
        relative_path=f"2026/08/{snapshot_id}.json",
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )
