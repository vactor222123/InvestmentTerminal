"""Tests for the provider-neutral transaction CSV parsing boundary."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.portfolio.transaction_csv_parser import (
    PortfolioTransactionCsvParser,
)

HEADER = ",".join(PortfolioTransactionCsvParser.COLUMNS)
IMPORTED_AT = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


def write_csv(path: Path, *rows: str) -> None:
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_parser_loads_trade_dividend_and_fee_without_reordering(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write_csv(
        path,
        "trade-1,BUY,2026-08-01T10:00:00+00:00,eur,WORLD,World ETF,ETF,eur,IE00B4L5Y983,IWDA,XAMS,2,100,,broker-1",
        "div-1,DIVIDEND,2026-08-02T10:00:00Z,EUR,WORLD,World ETF,ETF,EUR,IE00B4L5Y983,IWDA,XAMS,,,4.5,broker-2",
        "fee-1,FEE,2026-08-03T10:00:00+00:00,EUR,,,,,,,,,,1.25,broker-3",
    )

    batch = PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)

    assert batch.source_name == "transactions.csv"
    assert batch.imported_at == IMPORTED_AT
    assert tuple(item.transaction_id for item in batch.transactions) == (
        "trade-1",
        "div-1",
        "fee-1",
    )
    assert batch.transactions[0].instrument.instrument_key == "IE00B4L5Y983"
    assert batch.transactions[0].quantity == 2.0
    assert batch.transactions[1].cash_amount == 4.5
    assert batch.transactions[2].instrument is None


def test_parser_preserves_duplicate_transaction_rows(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    row = "fee-1,FEE,2026-08-03T10:00:00+00:00,EUR,,,,,,,,,,1.25,ref"
    write_csv(path, row, row)

    batch = PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)

    assert [item.transaction_id for item in batch.transactions] == ["fee-1", "fee-1"]


def test_parser_accepts_empty_transaction_file(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write_csv(path)

    batch = PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)

    assert batch.transactions == ()


def test_parser_rejects_missing_column(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    path.write_text("transaction_id,transaction_type\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing columns"):
        PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)


def test_parser_rejects_duplicate_header(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    path.write_text(HEADER + ",transaction_id\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate columns: transaction_id"):
        PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)


def test_parser_reports_line_for_invalid_number(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write_csv(path, "fee-1,FEE,2026-08-03T10:00:00Z,EUR,,,,,,,,,,invalid,ref")

    with pytest.raises(ValueError, match="CSV line 2: cash_amount must be numeric"):
        PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)


def test_parser_reports_line_for_naive_occurrence_time(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write_csv(path, "fee-1,FEE,2026-08-03T10:00:00,EUR,,,,,,,,,,1.25,ref")

    with pytest.raises(
        ValueError, match="CSV line 2: occurred_at must be timezone-aware"
    ):
        PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)


def test_parser_rejects_partial_instrument(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write_csv(path, "trade-1,BUY,2026-08-01T10:00:00Z,EUR,WORLD,,,,,,,2,100,,ref")

    with pytest.raises(ValueError, match="partial instrument is missing fields"):
        PortfolioTransactionCsvParser.load(path, imported_at=IMPORTED_AT)


def test_parser_rejects_non_file_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must point to a file"):
        PortfolioTransactionCsvParser.load(tmp_path, imported_at=IMPORTED_AT)
