import json

from investment_terminal.cli import manifest_failed_series_diagnostic as cli
from tests.test_manifest_bound_market_batch import NOW, manifest
from tests.test_manifest_failed_series_diagnostic import Client


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_writes_bound_report_without_mutating_checkpoint(tmp_path):
    value, checksum = manifest()
    request_checksum = value["batches"][0]["request_checksum"]
    checkpoint = {
        "schema_version": 1,
        "request_checksum": request_checksum,
        "outcomes": {
            "AAA": {
                "status": "FAILED",
                "failure_type": "YahooCandleInvalidResponseError",
            }
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    before = checkpoint_path.read_bytes()

    result = cli.main(arguments(tmp_path, checksum), client=Client(), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "SUCCESS"
    assert report["schema_version"] == 2
    assert report["manifest_checksum"] == checksum
    assert report["batch_index"] == 1
    assert checkpoint_path.read_bytes() == before
    assert "AAA" not in report_text


def test_invalid_checkpoint_writes_redacted_failure_without_provider_call(tmp_path):
    value, checksum = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / "checkpoint.json").write_text(
        json.dumps({
            "schema_version": 1,
            "request_checksum": value["batches"][0]["request_checksum"],
            "outcomes": {},
        }),
        encoding="utf-8",
    )
    client = Client()

    result = cli.main(arguments(tmp_path, checksum), client=client, clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["schema_version"] == 2
    assert report["failure"]["type"] == "ValueError"
    assert client.calls == []
    assert "AAA" not in report_text
