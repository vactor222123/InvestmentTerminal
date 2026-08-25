import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_terminal.portfolio.transaction_csv_import import (
    TransactionCsvImportService,
    TransactionCsvImportStatus,
)
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


def write(path: Path, *rows: str) -> None:
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def repository(path: Path) -> SQLitePortfolioTransactionRepository:
    return SQLitePortfolioTransactionRepository(
        PortfolioTransactionSQLiteStore(
            path,
            ledger_id="main",
            portfolio_name="Personal",
            base_currency="EUR",
        )
    )


def test_import_reports_only_aggregate_coverage(tmp_path: Path) -> None:
    source = tmp_path / "private.csv"
    write(
        source,
        "private-id,FEE,2026-01-01T10:00:00Z,EUR,,,,,,,,,,7,private-ref",
    )
    result = TransactionCsvImportService(
        repository(tmp_path / "transactions.db"), clock=clock()
    ).import_csv(source, imported_at=NOW)
    payload = json.dumps(result.to_dict())

    assert result.status is TransactionCsvImportStatus.SUCCESS
    assert result.submitted_count == result.imported_count == result.stored_total == 1
    assert result.duplicate_count == 0
    assert result.earliest_occurred_at == datetime(
        2026, 1, 1, 10, tzinfo=timezone.utc
    )
    for private in ("private.csv", "private-id", "private-ref", "Personal"):
        assert private not in payload


def test_empty_input_does_not_initialize_database(tmp_path: Path) -> None:
    source = tmp_path / "empty.csv"
    database = tmp_path / "transactions.db"
    write(source)

    result = TransactionCsvImportService(
        repository(database), clock=clock()
    ).import_csv(source, imported_at=NOW)

    assert result.status is TransactionCsvImportStatus.EMPTY
    assert result.submitted_count == result.imported_count == 0
    assert not database.exists()


def test_later_sqlite_failure_rolls_back_and_returns_redacted_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private.csv"
    database = tmp_path / "transactions.db"
    write(
        source,
        "candidate,FEE,2026-01-01T10:00:00Z,EUR,,,,,,,,,,1,first-ref",
        "fail,FEE,2026-01-02T10:00:00Z,EUR,,,,,,,,,,1,second-ref",
    )
    repo = repository(database)
    repo.store.initialize()
    with repo.store.connect() as connection:
        connection.execute(
            "CREATE TRIGGER fail_import BEFORE INSERT ON portfolio_transactions "
            "WHEN NEW.transaction_id = 'fail' "
            "BEGIN SELECT RAISE(ABORT, 'private failure'); END"
        )
        connection.commit()

    result = TransactionCsvImportService(repo, clock=clock()).import_csv(
        source, imported_at=NOW
    )

    assert result.status is TransactionCsvImportStatus.FAILED
    assert result.failure_type == "IntegrityError"
    assert result.failure_reason == "transaction database operation failed"
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM portfolio_transactions"
        ).fetchone()[0] == 0


def test_missing_input_failure_does_not_leak_path_or_create_database(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-name.csv"
    database = tmp_path / "transactions.db"

    result = TransactionCsvImportService(
        repository(database), clock=clock()
    ).import_csv(source, imported_at=NOW)
    payload = json.dumps(result.to_dict())

    assert result.status is TransactionCsvImportStatus.FAILED
    assert result.failure_reason == "transaction CSV is unavailable"
    assert str(source) not in payload
    assert "private-name" not in payload
    assert not database.exists()
