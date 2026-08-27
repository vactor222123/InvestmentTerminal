"""CLI privacy and persistence tests for Yahoo ISIN-search qualification."""

from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.cli.yahoo_isin_search_qualification import main

NOW = datetime(2026, 8, 27, 18, tzinfo=timezone.utc)


class Client:
    def search_isin(self, isin):
        return [{"symbol": "PRIVATE.DE", "exchange": "GER", "exchDisp": "Xetra",
                 "quoteType": "EQUITY", "currency": "EUR", "longname": "Private Name"}]


def arguments(tmp_path):
    return [
        "--candidate-diagnostic", str(tmp_path / "diagnostic.json"),
        "--private-candidates-output", str(tmp_path / "private-candidates.json"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def diagnostic(tmp_path):
    (tmp_path / "diagnostic.json").write_text(json.dumps({
        "schema_version": 1,
        "failure_category": "CANDIDATE_TICKER_ABSENT",
        "instrument_key": "DE0000000001",
    }))


def test_cli_writes_private_candidates_and_redacted_report(tmp_path: Path, capsys):
    diagnostic(tmp_path)
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 0
    private = json.loads((tmp_path / "private-candidates.json").read_text())
    assert private["candidates"] == [{
        "symbol": "PRIVATE.DE", "exchange": "GER", "exchange_display": "Xetra",
        "quote_type": "EQUITY", "currency": "EUR",
    }]
    report_text = (tmp_path / "report.json").read_text()
    report = json.loads(report_text)
    assert report["status"] == "SUCCESS"
    assert report["coverage"] == {
        "candidate_count": 1, "unique_symbol_count": 1, "unique_exchange_count": 1,
    }
    stdout = capsys.readouterr().out
    for private_value in ("DE0000000001", "PRIVATE.DE", "GER", "Xetra", str(tmp_path)):
        assert private_value not in report_text
        assert private_value not in stdout


def test_missing_diagnostic_writes_failed_report_without_private_output(tmp_path: Path):
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "FAILED"
    assert report["failure"]["type"] == "FileNotFoundError"
    assert not (tmp_path / "private-candidates.json").exists()


def test_private_write_failure_is_redacted(tmp_path: Path, monkeypatch):
    diagnostic(tmp_path)
    from investment_terminal.cli import yahoo_isin_search_qualification as command
    real_writer = command.write_json_atomic

    def fail_private(path, payload, **kwargs):
        if Path(path).name == "private-candidates.json":
            raise OSError("private path detail")
        return real_writer(path, payload, **kwargs)

    monkeypatch.setattr(command, "write_json_atomic", fail_private)
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 1
    report_text = (tmp_path / "report.json").read_text()
    assert json.loads(report_text)["failure"]["type"] == "OSError"
    assert "private path detail" not in report_text
    assert str(tmp_path) not in report_text
