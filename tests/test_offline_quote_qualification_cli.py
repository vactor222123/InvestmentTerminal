"""CLI tests for redacted offline quote qualification reports."""

import json
from pathlib import Path

from investment_terminal.cli.offline_quote_qualification import main
from tests.test_offline_quote_qualification import NOW, buy, repository


def args(tmp_path: Path):
    return ["--transaction-database", str(tmp_path / "tx.db"), "--quotes", str(tmp_path / "quotes.json"), "--ledger-id", "main", "--portfolio-name", "Personal", "--base-currency", "EUR", "--valued-at", NOW.isoformat(), "--output", str(tmp_path / "report.json")]


def test_cli_success_does_not_create_valuation_database(tmp_path: Path):
    repository(tmp_path).add(buy())
    (tmp_path / "quotes.json").write_text(json.dumps({"quotes": [{"instrument_key": "MSFT", "exchange_ticker": "MSFT", "price": 120, "currency": "USD", "quoted_at": NOW.isoformat(), "source": "TEST"}]}), encoding="utf-8")
    assert main(args(tmp_path), clock=lambda: NOW) == 0
    assert json.loads((tmp_path / "report.json").read_text())["status"] == "SUCCESS"
    assert not (tmp_path / "valuations.db").exists()


def test_malformed_private_input_still_writes_privacy_safe_failure(tmp_path: Path):
    repository(tmp_path).add(buy())
    (tmp_path / "quotes.json").write_text("not-json", encoding="utf-8")
    assert main(args(tmp_path), clock=lambda: NOW) == 1
    text = (tmp_path / "report.json").read_text()
    assert '"status": "FAILED"' in text
    assert str(tmp_path) not in text and "not-json" not in text
