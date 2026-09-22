import json

from investment_terminal.cli import (
    manifest_post_transition_residual_inventory as cli,
)
from tests.test_manifest_post_transition_residual_inventory import NOW, evidence


def prepare(tmp_path):
    (
        manifest,
        plan,
        checkpoints,
        inventory,
        inventory_checksum,
        transition,
        transition_checksum,
        symbols,
    ) = evidence()
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
    (tmp_path / "transition.json").write_bytes(transition)
    return plan, inventory_checksum, transition_checksum, symbols


def arguments(tmp_path, manifest_checksum, inventory_checksum, transition_checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", manifest_checksum,
        "--checkpoint-directory", str(tmp_path / "checkpoints"),
        "--inventory", str(tmp_path / "inventory.json"),
        "--inventory-checksum", inventory_checksum,
        "--transition-report", str(tmp_path / "transition.json"),
        "--transition-report-checksum", transition_checksum,
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_writes_redacted_read_only_inventory(tmp_path):
    plan, inventory_checksum, transition_checksum, symbols = prepare(tmp_path)
    before = {
        path.name: path.read_bytes()
        for path in (tmp_path / "checkpoints").iterdir()
    }

    result = cli.main(
        arguments(
            tmp_path,
            plan.manifest_checksum,
            inventory_checksum,
            transition_checksum,
        ),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    after = {
        path.name: path.read_bytes()
        for path in (tmp_path / "checkpoints").iterdir()
    }
    assert result == 0
    assert report["status"] == "SUCCESS"
    assert report["coverage"]["retryable_failure_count"] == 2
    assert before == after
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text


def test_cli_writes_redacted_failure_report(tmp_path):
    plan, inventory_checksum, transition_checksum, symbols = prepare(tmp_path)

    result = cli.main(
        arguments(
            tmp_path,
            plan.manifest_checksum,
            inventory_checksum,
            "0" * 64,
        ),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["coverage"] is None
    assert report["residual_causal_signatures"] == []
    assert report["final_failure_signatures"] == []
    assert report["failure"] == {
        "type": "ValueError",
        "reason": "Post-transition residual inventory failed",
    }
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text
