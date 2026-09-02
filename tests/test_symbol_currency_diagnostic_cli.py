import json

from investment_terminal.cli.symbol_currency_diagnostic import main
from tests.test_symbol_currency_diagnostic import NOW, Client, checkpoint
from tests.test_symbol_currency_qualification import checksum, projection


def test_cli_writes_redacted_report_without_mutating_checkpoint(tmp_path):
    value = projection(); source = tmp_path / "projection.json"
    check = tmp_path / "checkpoint.json"; report = tmp_path / "report.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    original = json.dumps(checkpoint(value), sort_keys=True)
    check.write_text(original, encoding="utf-8")
    exit_code = main(["--projection", str(source), "--projection-checksum", checksum(value),
                      "--checkpoint", str(check), "--report-output", str(report)],
                     client=Client(), clock=lambda: NOW)
    assert exit_code == 0
    assert json.dumps(json.loads(check.read_text(encoding="utf-8")), sort_keys=True) == original
    assert "AAA" not in report.read_text(encoding="utf-8")


def test_cli_failure_is_redacted(tmp_path):
    report = tmp_path / "report.json"
    exit_code = main(["--projection", str(tmp_path / "private.json"),
                      "--projection-checksum", "x", "--checkpoint", str(tmp_path / "secret.json"),
                      "--report-output", str(report)], clock=lambda: NOW)
    text = report.read_text(encoding="utf-8")
    assert exit_code == 1 and "private.json" not in text and "secret.json" not in text
