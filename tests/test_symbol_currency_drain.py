from datetime import datetime, timezone
import json

import pytest
from yfinance.exceptions import YFRateLimitError

from investment_terminal.cli.symbol_currency_drain import main
from investment_terminal.operations.symbol_currency_drain import (
    SymbolCurrencyDrainService,
)
from tests.test_symbol_currency_qualification import checksum


NOW = datetime(2026, 9, 3, tzinfo=timezone.utc)


def projection(count):
    return {
        "schema_version": 1,
        "projection_identity": "ELIGIBILITY_SUCCESS_UNIVERSE",
        "request_checksum": "a" * 64,
        "universe_checksum": "b" * 64,
        "members": [
            {"source": "TEST", "source_symbol": f"S{i:03d}",
             "yahoo_symbol": f"S{i:03d}"}
            for i in range(count)
        ],
    }


class Client:
    def __init__(self, rate_limit_at=None):
        self.calls = []
        self.rate_limit_at = rate_limit_at

    def get_currency(self, symbol):
        self.calls.append(symbol)
        if len(self.calls) == self.rate_limit_at:
            raise RuntimeError("private") from YFRateLimitError()
        return "USD"


def test_completes_multiple_slices_and_partial_final_slice():
    value = projection(205); writes = []; client = Client()
    report = SymbolCurrencyDrainService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), max_total_items=300)
    assert report["status"] == "COMPLETE"
    assert report["current_run"] == {
        "slice_count": 3, "attempted_count": 205, "provider_request_count": 205}
    assert report["ending_coverage"]["success_count"] == 205
    assert "S000" not in str(report) and "USD" not in str(report)


def test_budget_exhaustion_is_resumable():
    value = projection(205); writes = []; client = Client()
    service = SymbolCurrencyDrainService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW)
    first = service.run(value, checksum(value), max_total_items=150)
    second = service.run(value, checksum(value), writes[-1], max_total_items=100)
    assert first["status"] == "BUDGET_EXHAUSTED"
    assert second["status"] == "COMPLETE"
    assert second["current_run"]["attempted_count"] == 55


def test_halts_immediately_on_rate_limit():
    value = projection(20); writes = []; client = Client(rate_limit_at=4)
    report = SymbolCurrencyDrainService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), max_total_items=20)
    assert report["status"] == "HALTED"
    assert report["halt_category"] == "RATE_LIMITED"
    assert report["current_run"]["attempted_count"] == 4
    assert len(client.calls) == 4


def test_exact_complete_resume_performs_no_provider_work():
    value = projection(2); writes = []; client = Client()
    service = SymbolCurrencyDrainService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW)
    service.run(value, checksum(value), max_total_items=2)
    client.calls.clear()
    report = service.run(value, checksum(value), writes[-1], max_total_items=2)
    assert report["status"] == "COMPLETE"
    assert report["current_run"]["attempted_count"] == 0
    assert client.calls == []


def test_zero_progress_fails(monkeypatch):
    value = projection(2)
    monkeypatch.setattr(
        "investment_terminal.operations.symbol_currency_drain."
        "SymbolCurrencyQualificationService.run",
        lambda *args, **kwargs: {
            "status": "IN_PROGRESS", "coverage": {"attempted_count": 0},
            "halt_category": None, "failure_categories": []},
    )
    with pytest.raises(RuntimeError, match="zero progress"):
        SymbolCurrencyDrainService(
            client=Client(), checkpoint_writer=lambda value: None, clock=lambda: NOW
        ).run(value, checksum(value), max_total_items=2)


@pytest.mark.parametrize("value", [0, 20001, True, 1.5])
def test_budget_is_bounded(value):
    item = projection(1)
    with pytest.raises((TypeError, ValueError)):
        SymbolCurrencyDrainService(
            client=Client(), checkpoint_writer=lambda value: None, clock=lambda: NOW
        ).run(item, checksum(item), max_total_items=value)


def test_cli_writes_redacted_report_and_private_checkpoint(tmp_path):
    value = projection(2); source = tmp_path / "projection.json"
    checkpoint = tmp_path / "checkpoint.json"; report = tmp_path / "report.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    checkpoint.write_text(json.dumps({"schema_version": 2,
        "request_checksum": checksum({"schema_version": 2,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "projection_checksum": checksum(value)}),
        "projection_checksum": checksum(value), "outcomes": {}}), encoding="utf-8")
    code = main(["--projection", str(source), "--projection-checksum", checksum(value),
        "--checkpoint", str(checkpoint), "--report-output", str(report),
        "--max-total-items", "2"], client=Client(), clock=lambda: NOW)
    text = report.read_text(encoding="utf-8")
    assert code == 0 and json.loads(text)["status"] == "COMPLETE"
    assert "S000" not in text and "USD" not in text


def test_cli_failure_is_redacted_and_report_write_failure_surfaces(tmp_path):
    source = tmp_path / "private-projection.json"
    checkpoint = tmp_path / "private-checkpoint.json"
    report = tmp_path / "report.json"
    source.write_text("{}", encoding="utf-8")
    checkpoint.write_text("{}", encoding="utf-8")
    assert main(["--projection", str(source), "--projection-checksum", "x",
        "--checkpoint", str(checkpoint), "--report-output", str(report),
        "--max-total-items", "1"], clock=lambda: NOW) == 1
    text = report.read_text(encoding="utf-8")
    assert "private-projection" not in text and "private-checkpoint" not in text

    def fail_writer(path, payload):
        raise OSError("private report detail")

    with pytest.raises(OSError, match="private report detail"):
        main(["--projection", str(source), "--projection-checksum", "x",
            "--checkpoint", str(checkpoint), "--report-output", str(report),
            "--max-total-items", "1"], clock=lambda: NOW, writer=fail_writer)
