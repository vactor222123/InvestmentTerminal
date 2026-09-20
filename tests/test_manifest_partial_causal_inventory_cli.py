import json

from investment_terminal.cli import manifest_partial_causal_inventory as cli
from tests.test_manifest_partial_causal_inventory import NOW, evidence


def prepare(tmp_path):
    manifest, checksum, selection, checkpoint, symbols = evidence()
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )
    return checksum, selection, symbols


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_writes_redacted_aggregate_report(tmp_path):
    checksum, _, symbols = prepare(tmp_path)

    result = cli.main(arguments(tmp_path, checksum), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "SUCCESS"
    assert report["coverage"]["retryable_failure_count"] == 3
    assert report["coverage"]["blocking_failure_count"] == 1
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text


def test_cli_writes_redacted_failure_report_on_binding_mismatch(tmp_path):
    _, _, symbols = prepare(tmp_path)

    result = cli.main(arguments(tmp_path, "0" * 64), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["coverage"] is None
    assert report["causal_signatures"] == []
    assert report["failure"] == {
        "type": "ValueError",
        "reason": "Manifest partial causal inventory failed",
    }
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text
