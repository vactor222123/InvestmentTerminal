import json

from investment_terminal.cli.symbol_currency_qualification import main
from tests.test_symbol_currency_qualification import NOW, checksum, projection


class Client:
    def search_symbol(self, symbol):
        return [{"symbol": symbol, "currency": "USD"}]


def test_cli_writes_private_checkpoint_and_redacted_report(tmp_path):
    value = projection(); source = tmp_path / "projection.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    checkpoint = tmp_path / "checkpoint.json"; report = tmp_path / "report.json"
    exit_code = main(["--projection", str(source), "--projection-checksum", checksum(value),
                      "--checkpoint", str(checkpoint), "--report-output", str(report),
                      "--max-items", "1"], client=Client(), clock=lambda: NOW)
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert exit_code == 0 and payload["status"] == "IN_PROGRESS"
    assert checkpoint.exists() and "AAA" not in report.read_text(encoding="utf-8")


def test_cli_failure_report_does_not_leak_paths(tmp_path):
    source = tmp_path / "private-name.json"
    report = tmp_path / "report.json"
    exit_code = main(["--projection", str(source), "--projection-checksum", "x",
                      "--checkpoint", str(tmp_path / "checkpoint.json"),
                      "--report-output", str(report)], clock=lambda: NOW)
    text = report.read_text(encoding="utf-8")
    assert exit_code == 1
    assert "private-name" not in text
    assert json.loads(text)["status"] == "FAILED"


def test_checkpoint_write_failure_produces_redacted_failure_report(tmp_path, monkeypatch):
    value = projection(); source = tmp_path / "projection.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    checkpoint = tmp_path / "checkpoint.json"; report = tmp_path / "report.json"
    original = __import__(
        "investment_terminal.cli.symbol_currency_qualification", fromlist=["write_json_atomic"]
    ).write_json_atomic

    def writer(path, payload):
        if path == checkpoint:
            raise OSError("private persistence detail")
        original(path, payload)

    monkeypatch.setattr(
        "investment_terminal.cli.symbol_currency_qualification.write_json_atomic", writer
    )
    exit_code = main(["--projection", str(source), "--projection-checksum", checksum(value),
                      "--checkpoint", str(checkpoint), "--report-output", str(report),
                      "--max-items", "1"], client=Client(), clock=lambda: NOW)
    text = report.read_text(encoding="utf-8")
    assert exit_code == 1 and "private persistence detail" not in text
    assert json.loads(text)["failure_categories"] == ["OSError"]
