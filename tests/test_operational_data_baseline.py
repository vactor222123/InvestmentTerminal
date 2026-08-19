"""Tests for the Phase 7 operational data baseline report."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.database.database import Database
from investment_terminal.models.candle import Candle
from investment_terminal.operations.operational_data_baseline import (
    OperationalDataBaselineInputs,
    OperationalDataBaselineService,
    OperationalState,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.universe.maintained_universe_sqlite_store import (
    MaintainedAssetUniverseSQLiteStore,
)


NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def build(
    *,
    inputs: OperationalDataBaselineInputs | None = None,
    environment: dict[str, str] | None = None,
):
    return OperationalDataBaselineService(
        inputs=inputs or OperationalDataBaselineInputs(),
        environment=environment or {},
        clock=lambda: NOW,
    ).build()


def by_store(report, identity: str):
    return next(
        item for item in report.stores if item.store_identity == identity
    )


def by_provider(report, identity: str):
    return next(
        item
        for item in report.providers
        if item.provider_identity == identity
    )


def test_empty_baseline_preserves_absent_and_unmeasured_states() -> None:
    report = build()

    assert all(item.state is OperationalState.ABSENT for item in report.stores)
    assert report.refresh_observability is OperationalState.UNMEASURED
    assert report.measured_performance is OperationalState.UNMEASURED
    assert report.to_dict()["authority"] == {
        "populated_coverage_is_measured_only": True,
        "analytical_evidence_is_interpretation": False,
        "grants_trade_execution_authority": False,
    }


def test_provider_configuration_is_explicit_and_secrets_are_redacted() -> None:
    secret = "do-not-serialize-this-secret"
    report = build(
        environment={
            "FINNHUB_API_KEY": secret,
            "INVESTMENT_TERMINAL_OPENAI_API_KEY": secret,
        }
    )
    payload = json.dumps(report.to_dict())

    assert by_provider(report, "FINNHUB").state is OperationalState.CONFIGURED
    assert by_provider(report, "OPENAI").state is OperationalState.CONFIGURED
    assert secret not in payload
    assert "environment:FINNHUB_API_KEY" in payload


def test_custom_openai_credential_variable_is_reported_without_value() -> None:
    report = build(
        environment={
            "INVESTMENT_TERMINAL_OPENAI_API_KEY_ENV": "CUSTOM_OPENAI_KEY",
            "CUSTOM_OPENAI_KEY": "secret",
        }
    )
    provider = by_provider(report, "OPENAI")

    assert provider.state is OperationalState.CONFIGURED
    assert provider.configuration_source == "environment:CUSTOM_OPENAI_KEY"
    assert "secret" not in json.dumps(report.to_dict())


def test_candle_coverage_is_grouped_and_deterministically_ordered(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "market.db"
    from investment_terminal.config.settings import Settings

    monkeypatch.setattr(Settings, "DATABASE_PATH", database_path)
    database = Database()
    database.initialize()
    repository = CandleRepository(database)
    repository.save_many(
        [
            Candle(
                symbol=symbol,
                resolution="D",
                timestamp=NOW,
                open_price=99,
                high_price=102,
                low_price=98,
                close_price=101,
                volume=1000,
                currency="USD",
            )
            for symbol in ("MSFT", "AAPL")
        ]
    )
    database.close()

    store = by_store(
        build(inputs=OperationalDataBaselineInputs(market_database=database_path)),
        "MARKET_CANDLES",
    )

    assert store.state is OperationalState.READY
    assert store.record_count == 2
    assert [item.identity for item in store.records] == [
        "AAPL:D:USD",
        "MSFT:D:USD",
    ]
    assert store.records[0].attributes == (("freshness", "UNMEASURED"),)


def test_inspection_does_not_create_an_absent_database(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"
    store = by_store(
        build(inputs=OperationalDataBaselineInputs(market_database=database_path)),
        "MARKET_CANDLES",
    )

    assert store.state is OperationalState.ABSENT
    assert not database_path.exists()


def test_malformed_sqlite_is_reported_as_error(tmp_path: Path) -> None:
    database_path = tmp_path / "malformed.db"
    database_path.write_text("not sqlite", encoding="utf-8")

    store = by_store(
        build(inputs=OperationalDataBaselineInputs(market_database=database_path)),
        "MARKET_CANDLES",
    )

    assert store.state is OperationalState.ERROR
    assert store.error is not None
    assert "DatabaseError" in store.error


def test_unsupported_store_schema_is_reported_as_error(tmp_path: Path) -> None:
    database_path = tmp_path / "universes.db"
    MaintainedAssetUniverseSQLiteStore(database_path).initialize()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE maintained_universe_metadata SET value = '999' "
            "WHERE key = 'schema_version'"
        )

    store = by_store(
        build(
            inputs=OperationalDataBaselineInputs(
                maintained_universe_database=database_path
            )
        ),
        "MAINTAINED_UNIVERSES",
    )

    assert store.state is OperationalState.ERROR
    assert "schema version mismatch" in (store.error or "")


def test_invalid_portfolio_is_reported_without_exposing_contents(
    tmp_path: Path,
) -> None:
    portfolio = tmp_path / "portfolio.json"
    portfolio.write_text('{"private": "sensitive"}', encoding="utf-8")

    store = by_store(
        build(inputs=OperationalDataBaselineInputs(current_portfolio=portfolio)),
        "CURRENT_PORTFOLIO",
    )

    assert store.state is OperationalState.ERROR
    assert "sensitive" not in json.dumps(store.to_dict())


def test_naive_generation_clock_fails_closed() -> None:
    service = OperationalDataBaselineService(
        inputs=OperationalDataBaselineInputs(),
        environment={},
        clock=lambda: datetime(2026, 8, 19, 12, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        service.build()


def test_report_serialization_is_deterministic() -> None:
    first = build().to_dict()
    second = build().to_dict()

    assert first == second
    assert [item["provider_identity"] for item in first["providers"]] == sorted(
        item["provider_identity"] for item in first["providers"]
    )
    assert [item["store_identity"] for item in first["stores"]] == sorted(
        item["store_identity"] for item in first["stores"]
    )


def test_workflow_report_turns_observability_into_measured_evidence(
    tmp_path: Path,
) -> None:
    path = tmp_path / "workflow.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "run-1",
                "started_at": "2026-08-19T12:00:00+00:00",
                "completed_at": "2026-08-19T12:00:09+00:00",
                "stages": [
                    {"status": "COMPLETED"},
                    {"status": "FAILED"},
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build(
        inputs=OperationalDataBaselineInputs(workflow_report=path)
    )
    record = by_store(report, "WORKFLOW_REPORT").records[0]

    assert report.refresh_observability is OperationalState.READY
    assert report.measured_performance is OperationalState.READY
    assert dict(record.attributes) == {
        "duration_seconds": 9,
        "failed_stage_count": 1,
    }
