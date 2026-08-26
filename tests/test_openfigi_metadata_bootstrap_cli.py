"""CLI and privacy tests for OpenFIGI metadata bootstrap."""

from datetime import datetime, timezone
from hashlib import sha256
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
        "--private-diagnostic-output", str(tmp_path / "private-diagnostic.json"),
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
    assert report["schema_version"] == 3
    assert report["status"] == "SUCCESS"
    assert report["coverage"] == {
        "requested_count": 1, "matched_count": 1,
        "batch_count": 1, "archived_response_count": 1,
    }
    text = (tmp_path / "report.json").read_text()
    assert "ACME" not in text and "DE0000000001" not in text
    assert "PRIVATE-FIGI" not in text and str(tmp_path) not in text
    assert not (tmp_path / "private-diagnostic.json").exists()


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
    assert not (tmp_path / "private-diagnostic.json").exists()


def test_candidate_absence_writes_private_diagnostic_and_redacted_report(
    tmp_path: Path, capsys
):
    setup(tmp_path)

    class Absent:
        def map_isins(self, isins):
            return json.dumps([{"data": [
                {"figi": "PRIVATE-FIGI", "ticker": "OTHER", "exchCode": "US"}
            ]}]).encode()

    assert main(arguments(tmp_path), client=Absent(), clock=lambda: NOW) == 1
    diagnostic = json.loads((tmp_path / "private-diagnostic.json").read_text())
    assert diagnostic == {
        "schema_version": 1,
        "run_id": "run-1",
        "retrieved_at": NOW.isoformat(),
        "failure_category": "CANDIDATE_TICKER_ABSENT",
        "request_ordinal": 1,
        "batch_number": 1,
        "instrument_key": "DE0000000001",
        "candidate_ticker": "ACME",
        "provider_tickers": ["OTHER"],
        "response_sha256": sha256(
            json.dumps([{"data": [
                {"figi": "PRIVATE-FIGI", "ticker": "OTHER", "exchCode": "US"}
            ]}]).encode()
        ).hexdigest(),
    }
    report_text = (tmp_path / "report.json").read_text()
    assert json.loads(report_text)["failure"]["category"] == "CANDIDATE_TICKER_ABSENT"
    stdout = capsys.readouterr().out
    for private_value in (
        "DE0000000001", "ACME", "OTHER", "PRIVATE-FIGI",
        "private-diagnostic.json", str(tmp_path),
    ):
        assert private_value not in report_text
        assert private_value not in stdout


def test_private_diagnostic_write_failure_is_redacted_and_nonzero(
    tmp_path: Path, monkeypatch
):
    setup(tmp_path)

    class Absent:
        def map_isins(self, isins):
            return json.dumps([{"data": [{"figi": "PRIVATE-FIGI", "ticker": "OTHER"}]}]).encode()

    from investment_terminal.cli import openfigi_metadata_bootstrap as command
    real_writer = command.write_json_atomic

    def fail_private(path, payload, **kwargs):
        if Path(path).name == "private-diagnostic.json":
            raise OSError("PRIVATE path failure")
        return real_writer(path, payload, **kwargs)

    monkeypatch.setattr(command, "write_json_atomic", fail_private)
    assert main(arguments(tmp_path), client=Absent(), clock=lambda: NOW) == 1
    assert not (tmp_path / "private-diagnostic.json").exists()
    assert not (tmp_path / "metadata.json").exists()
    report_text = (tmp_path / "report.json").read_text()
    report = json.loads(report_text)
    assert report["failure"] == {
        "type": "OSError",
        "category": "INPUT_OR_RUNTIME_FAILURE",
        "reason": "OpenFIGI metadata bootstrap failed",
    }
    assert "PRIVATE path failure" not in report_text
    assert str(tmp_path) not in report_text


def test_missing_transaction_database_does_not_create_it(tmp_path: Path):
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 1
    assert not (tmp_path / "transactions.db").exists()
    assert json.loads((tmp_path / "report.json").read_text())["status"] == "FAILED"
    assert json.loads((tmp_path / "report.json").read_text())["failure"]["category"] == (
        "INPUT_OR_RUNTIME_FAILURE"
    )
