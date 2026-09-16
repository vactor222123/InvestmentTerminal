from datetime import datetime, timezone
from hashlib import sha256
import json

from investment_terminal.cli.manifest_partial_no_price_isolation import main
from investment_terminal.operations.market_batch_manifest import _manifest_checksum
from investment_terminal.operations.resumable_market_batch import MarketBatchRequest


NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def inputs(tmp_path):
    request = MarketBatchRequest.from_dict({
        "schema_version": 1,
        "resolution": "D",
        "start": "2016-09-16T00:00:00+00:00",
        "end": "2026-09-16T00:00:00+00:00",
        "items": [
            {"symbol": "AAA", "currency": "USD"},
            {"symbol": "PRIVATE", "currency": "EUR"},
            {"symbol": "ZZZ", "currency": "USD"},
        ],
    })
    manifest = {
        "schema_version": 1,
        "manifest_identity": "QUALIFIED_MARKET_BATCH_MANIFEST",
        "projection_checksum": "a" * 64,
        "currency_request_checksum": "b" * 64,
        "batches": [{
            "batch_index": 1,
            "request_checksum": request.checksum,
            "request": request.canonical_dict(),
        }],
    }
    manifest_checksum = _manifest_checksum(manifest)
    checkpoint = {
        "schema_version": 1,
        "request_checksum": request.checksum,
        "outcomes": {
            "AAA": {"status": "SUCCESS", "downloaded": 1, "inserted": 1,
                    "duplicates": 0, "failure_type": None},
            "PRIVATE": {"status": "FAILED", "downloaded": None,
                        "inserted": None, "duplicates": None,
                        "failure_type": "APIError"},
        },
    }
    qualification = {
        "schema_version": 1,
        "provider_identity": "YAHOO_FINANCE",
        "qualification_identity": "MANIFEST_PARTIAL_FAILURE_QUALIFICATION",
        "status": "FAILED",
        "manifest_checksum": manifest_checksum,
        "batch_index": 1,
        "batch_count": 1,
        "request_checksum": request.checksum,
        "requested_start": request.start.isoformat(),
        "requested_end": request.end.isoformat(),
        "selection": {"requested_count": 3, "checkpoint_outcome_count": 2,
                      "missing_count": 1, "failed_candidate_count": 1,
                      "selected_count": 1,
                      "checkpoint_failure_types": ["APIError"]},
        "coverage": None,
        "failure": {"category": "NO_PRICE_DATA",
                    "exception_type_chain": [
                        "investment_terminal.utils.exceptions.APIError",
                        "yfinance.exceptions.YFPricesMissingError"],
                    "reason": "Manifest partial-failure qualification failed"},
    }
    paths = {name: tmp_path / name for name in (
        "manifest.json", "checkpoint.json", "qualification.json", "report.json"
    )}
    paths["manifest.json"].write_text(json.dumps(manifest), encoding="utf-8")
    paths["checkpoint.json"].write_text(json.dumps(checkpoint), encoding="utf-8")
    raw = json.dumps(qualification).encode("utf-8")
    paths["qualification.json"].write_bytes(raw)
    args = [
        "--manifest", str(paths["manifest.json"]),
        "--manifest-checksum", manifest_checksum,
        "--batch-index", "1",
        "--checkpoint", str(paths["checkpoint.json"]),
        "--qualification", str(paths["qualification.json"]),
        "--qualification-checksum", sha256(raw).hexdigest(),
        "--report-output", str(paths["report.json"]),
    ]
    return args, paths


def test_cli_commits_checkpoint_before_success_report(tmp_path):
    args, paths = inputs(tmp_path)
    writes = []

    code = main(
        args, clock=lambda: NOW,
        checkpoint_writer=lambda path, value: writes.append(("checkpoint", path, value)),
        report_writer=lambda path, value: writes.append(("report", path, value)),
    )

    assert code == 0
    assert [item[0] for item in writes] == ["checkpoint", "report"]
    assert writes[0][2]["schema_version"] == 4
    assert writes[1][2]["status"] == "SUCCESS"
    assert writes[0][1] == paths["checkpoint.json"]


def test_cli_checkpoint_write_failure_cannot_claim_success(tmp_path):
    args, _ = inputs(tmp_path)
    reports = []

    def fail_checkpoint(path, value):
        raise OSError("private path")

    code = main(
        args, clock=lambda: NOW, checkpoint_writer=fail_checkpoint,
        report_writer=lambda path, value: reports.append(value),
    )

    assert code == 1
    assert reports[0]["status"] == "FAILED"
    assert reports[0]["failure"]["category"] == "CHECKPOINT_WRITE_FAILED"
    assert "private path" not in str(reports[0])


def test_cli_validation_failure_does_not_write_checkpoint(tmp_path):
    args, _ = inputs(tmp_path)
    args[args.index("--qualification-checksum") + 1] = "0" * 64
    checkpoint_writes = []
    reports = []

    code = main(
        args, clock=lambda: NOW,
        checkpoint_writer=lambda path, value: checkpoint_writes.append(value),
        report_writer=lambda path, value: reports.append(value),
    )

    assert code == 1
    assert checkpoint_writes == []
    assert reports[0]["failure"]["category"] == "VALIDATION_OR_IO_ERROR"
