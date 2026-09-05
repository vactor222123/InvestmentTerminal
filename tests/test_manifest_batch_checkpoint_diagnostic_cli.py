import json

from investment_terminal.cli import manifest_batch_checkpoint_diagnostic as cli
from tests.test_manifest_bound_market_batch import NOW, manifest


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_reads_checkpoint_without_mutating_it(tmp_path):
    value, checksum = manifest()
    request_checksum = value["batches"][0]["request_checksum"]
    checkpoint = {
        "schema_version": 1,
        "request_checksum": request_checksum,
        "outcomes": {
            "AAA": {
                "status": "FAILED",
                "downloaded": None,
                "inserted": None,
                "duplicates": None,
                "failure_type": "YahooCandleInvalidResponseError",
            }
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    before = checkpoint_path.read_bytes()

    result = cli.main(arguments(tmp_path, checksum), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["coverage"]["failure_count"] == 1
    assert report["failure_types"] == ["YahooCandleInvalidResponseError"]
    assert checkpoint_path.read_bytes() == before
    assert "AAA" not in report_text


def test_invalid_checkpoint_writes_privacy_safe_failure_report(tmp_path):
    value, checksum = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "request_checksum": value["batches"][0]["request_checksum"],
                "outcomes": {},
            }
        ),
        encoding="utf-8",
    )

    result = cli.main(arguments(tmp_path, checksum), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["coverage"] is None
    assert report["failure_types"] == ["ValueError"]
    assert "AAA" not in report_text
