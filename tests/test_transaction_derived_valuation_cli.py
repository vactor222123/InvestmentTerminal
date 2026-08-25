"""CLI tests for bounded transaction-derived valuation."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli import transaction_derived_valuation as cli
from tests.test_transaction_derived_valuation import NOW, buy, repositories


def arguments(tmp_path: Path) -> list[str]:
    quotes = tmp_path / "private-quotes.json"
    quotes.write_text(json.dumps({"quotes": [{"instrument_key": "MSFT", "exchange_ticker": "MSFT", "price": 120, "currency": "USD", "quoted_at": NOW.isoformat(), "source": "TEST"}]}), encoding="utf-8")
    return ["--transaction-database", str(tmp_path / "tx.db"), "--quotes", str(quotes), "--valuation-database", str(tmp_path / "values.db"), "--ledger-id", "main", "--portfolio-name", "Personal", "--base-currency", "EUR", "--snapshot-id", "v-1", "--valued-at", NOW.isoformat(), "--output", str(tmp_path / "report.json")]


def test_cli_writes_strict_redacted_success_report(tmp_path: Path) -> None:
    repositories(tmp_path)[0].add(buy())
    assert cli.main(arguments(tmp_path), clock=lambda: NOW) == 0
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"
    assert payload["coverage"]["stored_snapshot_total"] == 1
    text = json.dumps(payload)
    for private in (str(tmp_path), "MSFT", "Personal", "120"):
        assert private not in text


def test_failed_valuation_writes_report_and_exits_nonzero(tmp_path: Path) -> None:
    repositories(tmp_path)[0].add(buy(NOW.replace(year=2027)))
    assert cli.main(arguments(tmp_path), clock=lambda: NOW) == 1
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["failure"]["reason"] == "transaction-derived valuation failed"


def test_report_failure_after_commit_is_distinct(tmp_path: Path, monkeypatch) -> None:
    repositories(tmp_path)[0].add(buy())
    monkeypatch.setattr(cli, "write_json_atomic", lambda *_a, **_k: (_ for _ in ()).throw(OSError("blocked")))
    with pytest.raises(cli.ValuationReportAfterCommitError):
        cli.main(arguments(tmp_path), clock=lambda: NOW)
    assert len(repositories(tmp_path)[1].list_all()) == 1


def test_cli_rejects_naive_valuation_time() -> None:
    with pytest.raises(SystemExit):
        cli.build_argument_parser().parse_args(["--valued-at", "2026-01-01T00:00:00"])
