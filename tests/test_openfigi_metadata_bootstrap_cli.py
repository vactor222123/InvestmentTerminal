"""CLI and privacy tests for OpenFIGI metadata bootstrap."""

from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.cli.openfigi_metadata_bootstrap import main
from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransaction
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore

NOW = datetime(2026, 8, 26, 12, tzinfo=timezone.utc)


class Client:
    def map_isins(self, isins):
        return json.dumps([{"data": [{"figi": "PRIVATE-FIGI", "ticker": "ACME"}]}]).encode()


def arguments(tmp_path):
    return [
        "--transaction-database", str(tmp_path / "transactions.db"),
        "--quotes", str(tmp_path / "quotes.json"),
        "--ledger-id", "main", "--portfolio-name", "Personal",
        "--base-currency", "EUR", "--run-id", "run-1",
        "--response-archive", str(tmp_path / "private-responses"),
        "--metadata-output", str(tmp_path / "metadata.json"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def setup(tmp_path):
    identity = InstrumentIdentity("ACME", "Acme", "STOCK", "EUR", isin="DE0000000001")
    repository = SQLitePortfolioTransactionRepository(PortfolioTransactionSQLiteStore(
        tmp_path / "transactions.db", ledger_id="main", portfolio_name="Personal", base_currency="EUR"
    ))
    repository.add(PortfolioTransaction("buy", "BUY", NOW, "EUR", identity, 1, 10))
    (tmp_path / "quotes.json").write_text(json.dumps({"quotes": [{
        "instrument_key": identity.instrument_key, "exchange_ticker": "ACME",
        "price": 11, "currency": "EUR", "quoted_at": NOW.isoformat(), "source": "PRIVATE"
    }]}))


def test_cli_success_writes_private_metadata_and_redacted_report(tmp_path: Path):
    setup(tmp_path)
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 0
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["schema_version"] == 2
    assert report["status"] == "SUCCESS"
    assert report["coverage"] == {
        "requested_count": 1, "matched_count": 1,
        "batch_count": 1, "archived_response_count": 1,
    }
    text = (tmp_path / "report.json").read_text()
    assert "ACME" not in text and "DE0000000001" not in text
    assert "PRIVATE-FIGI" not in text and str(tmp_path) not in text


def test_cli_failure_is_redacted_and_reports_archived_response(tmp_path: Path):
    setup(tmp_path)
    class Bad:
        def map_isins(self, isins): return b"not-json"
    assert main(arguments(tmp_path), client=Bad(), clock=lambda: NOW) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "FAILED"
    assert report["failure"]["category"] == "RESPONSE_INVALID"
    assert report["coverage"]["archived_response_count"] == 1
    assert not (tmp_path / "metadata.json").exists()


def test_cli_failure_category_does_not_expose_provider_text(tmp_path: Path):
    setup(tmp_path)
    class Rejected:
        def map_isins(self, isins):
            return json.dumps([{"error": "PRIVATE provider detail"}]).encode()
    assert main(arguments(tmp_path), client=Rejected(), clock=lambda: NOW) == 1
    text = (tmp_path / "report.json").read_text()
    report = json.loads(text)
    assert report["failure"]["category"] == "PROVIDER_ERROR"
    assert "PRIVATE provider detail" not in text


def test_missing_transaction_database_does_not_create_it(tmp_path: Path):
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 1
    assert not (tmp_path / "transactions.db").exists()
    assert json.loads((tmp_path / "report.json").read_text())["status"] == "FAILED"
    assert json.loads((tmp_path / "report.json").read_text())["failure"]["category"] == (
        "INPUT_OR_RUNTIME_FAILURE"
    )
