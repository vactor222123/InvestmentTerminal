import json

from investment_terminal.cli import manifest_partial_causal_evidence as cli
from tests.test_manifest_partial_causal_evidence import NOW, schema4_evidence
from tests.test_manifest_partial_failure_qualification import evidence


def prepare(tmp_path):
    manifest, checksum, _, _, _ = evidence()
    selection, checkpoint, selected = schema4_evidence()
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )
    return checksum, selection, selected


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_writes_redacted_available_report(tmp_path):
    checksum, _, selected = prepare(tmp_path)

    result = cli.main(arguments(tmp_path, checksum), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "EVIDENCE_AVAILABLE"
    assert report["causal_failure_evidence"]["category"] == "NO_PRICE_DATA"
    assert selected.symbol not in report_text
    assert str(tmp_path) not in report_text


def test_cli_writes_redacted_failure_report_on_binding_mismatch(tmp_path):
    checksum, _, selected = prepare(tmp_path)

    result = cli.main(arguments(tmp_path, "0" * 64), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["manifest_checksum"] is None
    assert report["failure"] == {
        "type": "ValueError",
        "reason": "Manifest partial causal-evidence diagnostic failed",
    }
    assert selected.symbol not in report_text
    assert str(tmp_path) not in report_text


def test_cli_reports_legacy_null_evidence_as_completed(tmp_path):
    checksum, _, _ = prepare(tmp_path)
    checkpoint = json.loads(
        (tmp_path / "checkpoint.json").read_text(encoding="utf-8")
    )
    failed = next(
        value
        for value in checkpoint["outcomes"].values()
        if value["status"] == "FAILED"
    )
    failed["causal_failure_evidence"] = None
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )

    result = cli.main(arguments(tmp_path, checksum), clock=lambda: NOW)

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 0
    assert report["status"] == "LEGACY_EVIDENCE_UNAVAILABLE"
    assert report["causal_failure_evidence"] is None
