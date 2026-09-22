import json

import pytest

from investment_terminal.cli import (
    manifest_completed_sweep_no_price_transition as cli,
)
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_manifest_completed_sweep_no_price_transition import NOW, evidence


def prepare(tmp_path):
    manifest, plan, checkpoints, inventory, checksum, symbols = evidence()
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    checkpoint_directory = tmp_path / "checkpoints"
    checkpoint_directory.mkdir()
    for index, checkpoint in checkpoints.items():
        (checkpoint_directory / f"batch_{index:04d}.json").write_text(
            json.dumps(checkpoint), encoding="utf-8"
        )
    (tmp_path / "inventory.json").write_bytes(inventory)
    return plan, checksum, symbols


def arguments(tmp_path, manifest_checksum, inventory_checksum, *, budget="3"):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", manifest_checksum,
        "--checkpoint-directory", str(tmp_path / "checkpoints"),
        "--inventory", str(tmp_path / "inventory.json"),
        "--inventory-checksum", inventory_checksum,
        "--report-output", str(tmp_path / "report.json"),
        "--max-checkpoints", budget,
    ]


def test_cli_atomically_transitions_checkpoints_and_writes_redacted_report(tmp_path):
    plan, inventory_checksum, symbols = prepare(tmp_path)

    result = cli.main(
        arguments(tmp_path, plan.manifest_checksum, inventory_checksum),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "COMPLETE"
    assert report["ending_coverage"]["final_count"] == 3
    assert report["ending_coverage"]["remaining_count"] == 0
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text


def test_cli_preflight_failure_writes_report_without_checkpoint_mutation(tmp_path):
    plan, inventory_checksum, symbols = prepare(tmp_path)
    before = {
        path.name: path.read_bytes()
        for path in (tmp_path / "checkpoints").iterdir()
    }

    result = cli.main(
        arguments(tmp_path, "0" * 64, inventory_checksum),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    after = {
        path.name: path.read_bytes()
        for path in (tmp_path / "checkpoints").iterdir()
    }
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["starting_coverage"] is None
    assert report["failure"] == {
        "type": "ValueError",
        "reason": "Completed-sweep no-price transition failed",
    }
    assert before == after
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text


def test_report_write_failure_is_recoverable_by_exact_resume(tmp_path):
    plan, inventory_checksum, _ = prepare(tmp_path)

    def fail_report(path, payload):
        if path.name == "report.json":
            raise OSError("private")
        write_json_atomic(path, payload)

    with pytest.raises(OSError, match="private"):
        cli.main(
            arguments(tmp_path, plan.manifest_checksum, inventory_checksum),
            clock=lambda: NOW,
            writer=fail_report,
        )

    result = cli.main(
        arguments(tmp_path, plan.manifest_checksum, inventory_checksum),
        clock=lambda: NOW,
    )
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 0
    assert report["status"] == "COMPLETE"
    assert report["starting_coverage"]["already_final_count"] == 3
    assert report["current_run"] == {
        "processed_checkpoint_count": 0,
        "eligible_count": 3,
        "transitioned_count": 0,
        "already_final_count": 3,
        "remaining_count": 0,
    }
