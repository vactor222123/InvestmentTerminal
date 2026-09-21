import json

from investment_terminal.cli import manifest_collection_failure_inventory as cli
from tests.test_manifest_collection_failure_inventory import NOW, evidence


def prepare(tmp_path):
    manifest, plan, checkpoints, sweep, checksum, symbols = evidence()
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    checkpoint_directory = tmp_path / "checkpoints"
    checkpoint_directory.mkdir()
    for index, checkpoint in checkpoints.items():
        (checkpoint_directory / f"batch_{index:04d}.json").write_text(
            json.dumps(checkpoint), encoding="utf-8"
        )
    (tmp_path / "sweep.json").write_bytes(sweep)
    return plan, checksum, symbols


def arguments(tmp_path, manifest_checksum, sweep_checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", manifest_checksum,
        "--checkpoint-directory", str(tmp_path / "checkpoints"),
        "--sweep-report", str(tmp_path / "sweep.json"),
        "--sweep-report-checksum", sweep_checksum,
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_writes_redacted_aggregate_inventory(tmp_path):
    plan, sweep_checksum, symbols = prepare(tmp_path)

    result = cli.main(
        arguments(tmp_path, plan.manifest_checksum, sweep_checksum),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "SUCCESS"
    assert report["coverage"]["checkpoint_outcome_count"] == 4
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text


def test_cli_writes_redacted_failure_report(tmp_path):
    plan, sweep_checksum, symbols = prepare(tmp_path)

    result = cli.main(
        arguments(tmp_path, "0" * 64, sweep_checksum),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["coverage"] is None
    assert report["retryable_causal_signatures"] == []
    assert report["final_failure_signatures"] == []
    assert report["failure"] == {
        "type": "ValueError",
        "reason": "Manifest collection failure inventory failed",
    }
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text
