import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_terminal.ai.providers.usage_ledger import GroundedProviderUsageCostLedgerRecord
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import SQLiteGroundedProviderUsageCostLedgerRepository
from investment_terminal.ai.providers.usage_ledger_sqlite_store import GroundedProviderUsageCostLedgerSQLiteStore
from investment_terminal.cli.provider_usage_cost import main


def seed(database: Path) -> None:
    repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(database)
    )
    for request_id, minute, tokens, output, total, input_cost, output_cost in (
        ("request-001", 0, 100, 40, 140, "0.001000", "0.002000"),
        ("request-002", 1, 200, 60, 260, "0.002000", "0.003000"),
    ):
        repository.add(
            GroundedProviderUsageCostLedgerRecord(
                request_id=request_id,
                provider_identity="OPENAI",
                model_identity="gpt-test",
                input_tokens=tokens,
                output_tokens=output,
                total_tokens=total,
                currency="EUR",
                input_cost=Decimal(input_cost),
                output_cost=Decimal(output_cost),
                total_cost=Decimal(input_cost) + Decimal(output_cost),
                recorded_at=datetime(
                    2026, 8, 15, 12, minute, tzinfo=timezone.utc
                ),
            )
        )


def run_json(database: Path, capsys, *args):
    main(["--database", str(database), "--json", *args])
    return json.loads(capsys.readouterr().out)


def test_json_list(tmp_path: Path, capsys) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    report = run_json(database, capsys, "list")
    assert report["count"] == 2
    assert [item["request_id"] for item in report["records"]] == [
        "request-001", "request-002"
    ]


def test_json_recent_is_bounded_and_newest_first(tmp_path: Path, capsys) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    report = run_json(database, capsys, "recent", "--limit", "1")
    assert report["command"] == "recent"
    assert report["count"] == 1
    assert report["records"][0]["request_id"] == "request-002"


def test_json_between_uses_half_open_window(tmp_path: Path, capsys) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    report = run_json(
        database, capsys, "between",
        "--started-at", "2026-08-15T12:00:00+00:00",
        "--ended-at", "2026-08-15T12:01:00+00:00",
    )
    assert report["command"] == "between"
    assert [item["request_id"] for item in report["records"]] == [
        "request-001"
    ]


def test_recent_rejects_non_positive_limit(tmp_path: Path) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    with pytest.raises(SystemExit):
        main([
            "--database", str(database),
            "recent", "--limit", "0",
        ])


def test_between_rejects_naive_datetime(tmp_path: Path) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    with pytest.raises(SystemExit):
        main([
            "--database", str(database),
            "between",
            "--started-at", "2026-08-15T12:00:00",
            "--ended-at", "2026-08-15T12:02:00+00:00",
        ])


def test_json_show(tmp_path: Path, capsys) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    report = run_json(
        database, capsys, "show", "--request-id", "request-002"
    )
    assert report["record"]["request_id"] == "request-002"
    assert report["record"]["total_cost"] == "0.005000"


def test_json_summary_uses_exact_decimal_totals(tmp_path: Path, capsys) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    report = run_json(database, capsys, "summary")
    assert report == {
        "command": "summary",
        "request_count": 2,
        "currency": "EUR",
        "input_tokens": 300,
        "output_tokens": 100,
        "total_tokens": 400,
        "input_cost": "0.003000",
        "output_cost": "0.005000",
        "total_cost": "0.008000",
    }


def test_missing_database_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main([
            "--database", str(tmp_path / "missing.db"), "list"
        ])


def test_missing_request_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)
    with pytest.raises(SystemExit):
        main([
            "--database", str(database),
            "show", "--request-id", "missing",
        ])
