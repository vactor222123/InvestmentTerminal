import json

from investment_terminal.cli.market_batch_manifest import main
from tests.test_market_batch_manifest import NOW, START, evidence


def write_inputs(tmp_path):
    projection, checksum, checkpoint = evidence(2)
    projection_path = tmp_path / "projection.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    projection_path.write_text(json.dumps(projection), encoding="utf-8")
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    return projection_path, checksum, checkpoint_path


def arguments(projection_path, checksum, checkpoint_path, private_path, report_path):
    return [
        "--projection", str(projection_path),
        "--projection-checksum", checksum,
        "--currency-checkpoint", str(checkpoint_path),
        "--private-output", str(private_path),
        "--report-output", str(report_path),
        "--resolution", "D",
        "--start", START.isoformat(),
        "--end", NOW.isoformat(),
    ]


def test_cli_writes_private_manifest_and_redacted_report(tmp_path):
    projection_path, checksum, checkpoint_path = write_inputs(tmp_path)
    private_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"

    result = main(
        arguments(projection_path, checksum, checkpoint_path, private_path, report_path),
        clock=lambda: NOW,
    )

    assert result == 0
    assert len(json.loads(private_path.read_text(encoding="utf-8"))["batches"]) == 1
    report_text = report_path.read_text(encoding="utf-8")
    assert json.loads(report_text)["status"] == "SUCCESS"
    assert "S000" not in report_text


def test_cli_failure_writes_only_redacted_report(tmp_path):
    projection_path, checksum, checkpoint_path = write_inputs(tmp_path)
    private_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"

    result = main(
        arguments(projection_path, "0" * 64, checkpoint_path, private_path, report_path),
        clock=lambda: NOW,
    )

    report_text = report_path.read_text(encoding="utf-8")
    assert result == 1
    assert not private_path.exists()
    assert json.loads(report_text)["failure"] == {
        "type": "ValueError",
        "reason": "Market batch manifest construction failed",
    }
    assert "S000" not in report_text


def test_cli_private_write_failure_is_redacted(tmp_path):
    projection_path, checksum, checkpoint_path = write_inputs(tmp_path)
    private_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"

    def writer(path, payload):
        if path == private_path:
            raise OSError("private output detail")
        path.write_text(json.dumps(payload), encoding="utf-8")

    result = main(
        arguments(projection_path, checksum, checkpoint_path, private_path, report_path),
        clock=lambda: NOW,
        writer=writer,
    )

    report_text = report_path.read_text(encoding="utf-8")
    assert result == 1
    assert "private output detail" not in report_text
    assert json.loads(report_text)["failure"]["type"] == "OSError"
