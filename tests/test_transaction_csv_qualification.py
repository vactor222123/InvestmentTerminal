import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.portfolio.transaction_csv_parser import (
    PortfolioTransactionCsvParser,
)
from investment_terminal.portfolio.transaction_csv_qualification import (
    TransactionCsvQualificationService,
    TransactionCsvQualificationStatus,
)


QUALIFIED_AT = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
HEADER = ",".join(PortfolioTransactionCsvParser.COLUMNS)


def clock():
    values = iter((QUALIFIED_AT, QUALIFIED_AT + timedelta(seconds=2)))
    return values.__next__


def write(path: Path, *rows: str) -> None:
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_success_reports_only_aggregate_coverage(tmp_path: Path) -> None:
    path = tmp_path / "private-broker-export.csv"
    write(
        path,
        "secret-buy,BUY,2026-01-02T10:00:00Z,EUR,WORLD,Private ETF,ETF,EUR,IE00B4L5Y983,IWDA,XAMS,9,123,,private-ref",
        "secret-fee,FEE,2026-02-03T10:00:00Z,EUR,,,,,,,,,,7,private-fee",
    )
    result = TransactionCsvQualificationService(clock=clock()).qualify(
        path, qualified_at=QUALIFIED_AT
    )
    payload = json.dumps(result.to_dict())

    assert result.status is TransactionCsvQualificationStatus.SUCCESS
    assert result.transaction_count == 2
    assert result.transaction_type_counts == (("BUY", 1), ("FEE", 1))
    assert result.duration_seconds == 2
    for private_value in (
        "private-broker-export", "secret-buy", "WORLD", "123", "private-ref"
    ):
        assert private_value not in payload


def test_empty_csv_is_explicit(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write(path)
    result = TransactionCsvQualificationService(clock=clock()).qualify(
        path, qualified_at=QUALIFIED_AT
    )
    assert result.status is TransactionCsvQualificationStatus.EMPTY
    assert result.transaction_count == 0


def test_parser_failure_becomes_redacted_failed_result(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write(path, "private-id,FEE,not-a-time,EUR,,,,,,,,,,1,private-ref")
    result = TransactionCsvQualificationService(clock=clock()).qualify(
        path, qualified_at=QUALIFIED_AT
    )
    payload = json.dumps(result.to_dict())
    assert result.status is TransactionCsvQualificationStatus.FAILED
    assert result.failure_type == "ValueError"
    assert result.failure_reason == "transaction CSV validation failed"
    assert "private-id" not in payload
    assert "private-ref" not in payload


def test_missing_input_failure_does_not_leak_private_path(tmp_path: Path) -> None:
    path = tmp_path / "private-name.csv"
    result = TransactionCsvQualificationService(clock=clock()).qualify(
        path, qualified_at=QUALIFIED_AT
    )
    payload = json.dumps(result.to_dict())

    assert result.failure_reason == "transaction CSV is unavailable"
    assert str(path) not in payload
    assert "private-name" not in payload


def test_naive_qualification_time_fails_before_read(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        TransactionCsvQualificationService(clock=clock()).qualify(
            tmp_path / "missing.csv",
            qualified_at=datetime(2026, 8, 25),
        )


def test_clock_moving_backwards_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "transactions.csv"
    write(path)
    values = iter((QUALIFIED_AT + timedelta(seconds=1), QUALIFIED_AT))
    with pytest.raises(ValueError, match="moved backwards"):
        TransactionCsvQualificationService(clock=values.__next__).qualify(
            path, qualified_at=QUALIFIED_AT
        )
