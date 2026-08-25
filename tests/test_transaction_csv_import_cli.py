import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli import transaction_csv_import as cli
from investment_terminal.portfolio.transaction_csv_parser import (
    PortfolioTransactionCsvParser,
)
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import (
    SQLitePortfolioTransactionRepository,
)
from investment_terminal.portfolio.transaction_ledger_sqlite_store import (
    PortfolioTransactionSQLiteStore,
)


NOW = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
HEADER = ",".join(PortfolioTransactionCsvParser.COLUMNS)


def clock():
    values = iter((NOW, NOW + timedelta(seconds=1)))
    return values.__next__


def arguments(tmp_path: Path) -> list[str]:
    return [
        "--input", str(tmp_path / "private.csv"),
        "--database", str(tmp_path / "transactions.db"),
        "--ledger-id", "main",
        "--portfolio-name", "Private Portfolio",
        "--base-currency", "EUR",
        "--imported-at", NOW.isoformat(),
        "--output", str(tmp_path / "report.json"),
        "--json",
    ]


def write_source(tmp_path: Path) -> None:
    (tmp_path / "private.csv").write_text(
        HEADER
        + "\nsecret-id,FEE,2026-01-01T10:00:00Z,EUR,,,,,,,,,,1,secret-ref\n",
        encoding="utf-8",
    )


def read_report(tmp_path: Path) -> dict[str, object]:
    return json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))


def test_cli_import_and_exact_repeat_are_redacted(
    tmp_path: Path, capsys
) -> None:
    write_source(tmp_path)

    assert cli.main(arguments(tmp_path), clock=clock()) == 0
    first = read_report(tmp_path)
    assert first["coverage"]["imported_count"] == 1
    assert cli.main(arguments(tmp_path), clock=clock()) == 0
    repeated = read_report(tmp_path)
    output = capsys.readouterr().out

    assert repeated["coverage"] == {
        "submitted_count": 1,
        "imported_count": 0,
        "duplicate_count": 1,
        "stored_total": 1,
        "earliest_occurred_at": "2026-01-01T10:00:00+00:00",
        "latest_occurred_at": "2026-01-01T10:00:00+00:00",
    }
    for private in ("secret-id", "secret-ref", "private.csv", "transactions.db"):
        assert private not in json.dumps(repeated)
        assert private not in output


def test_cli_parse_failure_writes_report_before_nonzero_without_database(
    tmp_path: Path,
) -> None:
    assert cli.main(arguments(tmp_path), clock=clock()) == 1

    payload = read_report(tmp_path)
    assert payload["status"] == "FAILED"
    assert payload["failure"] == {
        "type": "FileNotFoundError",
        "reason": "transaction CSV is unavailable",
    }
    assert not (tmp_path / "transactions.db").exists()


def test_cli_metadata_mismatch_is_redacted_and_preserves_database(
    tmp_path: Path,
) -> None:
    write_source(tmp_path)
    database = tmp_path / "transactions.db"
    original = PortfolioTransactionSQLiteStore(
        database,
        ledger_id="other",
        portfolio_name="Other",
        base_currency="USD",
    )
    original.initialize()

    assert cli.main(arguments(tmp_path), clock=clock()) == 1
    payload = read_report(tmp_path)

    assert payload["failure"]["reason"] == (
        "transaction CSV or database metadata validation failed"
    )
    assert SQLitePortfolioTransactionRepository(original).list_all() == ()


def test_post_commit_report_failure_is_visible_and_exact_repeat_reconciles(
    tmp_path: Path, monkeypatch
) -> None:
    write_source(tmp_path)
    original_write = cli.write_json_atomic

    def fail_write(*args, **kwargs):
        raise OSError("private report path")

    monkeypatch.setattr(cli, "write_json_atomic", fail_write)
    with pytest.raises(
        cli.TransactionImportReportAfterCommitError,
        match="import committed.*rerun the exact input",
    ) as error:
        cli.main(arguments(tmp_path), clock=clock())
    assert "private report path" not in str(error.value)

    monkeypatch.setattr(cli, "write_json_atomic", original_write)
    assert cli.main(arguments(tmp_path), clock=clock()) == 0
    assert read_report(tmp_path)["coverage"]["duplicate_count"] == 1


def test_cli_rejects_naive_import_time(tmp_path: Path) -> None:
    values = arguments(tmp_path)
    values[values.index(NOW.isoformat())] = "2026-08-25T12:00:00"
    with pytest.raises(SystemExit) as error:
        cli.main(values, clock=clock())
    assert error.value.code == 2
