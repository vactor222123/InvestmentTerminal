from datetime import datetime, timezone
from hashlib import sha256
import json

from investment_terminal.cli.manifest_terminal_series_isolation import main
from investment_terminal.operations.market_batch_manifest import _manifest_checksum
from investment_terminal.operations.resumable_market_batch import MarketBatchRequest


NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


def fixture_files(tmp_path):
    request = MarketBatchRequest.from_dict({
        "schema_version": 1,
        "resolution": "D",
        "start": "2016-09-13T00:00:00+00:00",
        "end": "2026-09-13T00:00:00+00:00",
        "items": [
            {"symbol": "AAA", "currency": "USD"},
            {"symbol": "PRIVATE", "currency": "EUR"},
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
            "AAA": {"status": "SUCCESS", "failure_type": None},
            "PRIVATE": {
                "status": "FAILED",
                "failure_type": "YahooCandleInvalidResponseError",
            },
        },
    }
    common = {
        "provider_identity": "YAHOO_FINANCE",
        "manifest_checksum": manifest_checksum,
        "batch_index": 1,
        "batch_count": 1,
        "request_checksum": request.checksum,
        "requested_start": request.start.isoformat(),
        "requested_end": request.end.isoformat(),
        "selection": {
            "requested_count": 2,
            "failed_candidate_count": 1,
            "selected_count": 1,
            "checkpoint_failure_types": ["YahooCandleInvalidResponseError"],
        },
        "failure": None,
    }
    normal = {
        **common,
        "schema_version": 3,
        "diagnostic_identity": "MANIFEST_FAILED_SERIES_RAW_CANDLE_DIAGNOSTIC",
        "status": "SUCCESS",
        "coverage": {"strict_projection": {
            "status": "REJECTED",
            "projected_candle_count": None,
            "failure_category": "RESPONSE_NUMERIC",
        }},
    }
    repaired = {
        **common,
        "schema_version": 2,
        "qualification_identity": "MANIFEST_REPAIRED_SERIES_QUALIFICATION",
        "status": "REJECTED",
        "repair": {
            "method_identity": "YFINANCE_PRICE_REPAIR_V1",
            "requested": True,
        },
        "coverage": {
            "projected_candle_count": None,
            "projection_failure_category": "RESPONSE_NUMERIC",
        },
    }
    values = {
        "manifest": manifest,
        "checkpoint": checkpoint,
        "normal": normal,
        "repaired": repaired,
    }
    paths = {}
    checksums = {}
    for name, value in values.items():
        path = tmp_path / f"{name}.json"
        raw = json.dumps(value, sort_keys=True).encode("utf-8")
        path.write_bytes(raw)
        paths[name] = path
        checksums[name] = sha256(raw).hexdigest()
    return paths, checksums, manifest_checksum


def arguments(tmp_path, paths, checksums, manifest_checksum):
    return [
        "--manifest", str(paths["manifest"]),
        "--manifest-checksum", manifest_checksum,
        "--batch-index", "1",
        "--checkpoint", str(paths["checkpoint"]),
        "--normal-diagnostic", str(paths["normal"]),
        "--normal-diagnostic-checksum", checksums["normal"],
        "--repaired-qualification", str(paths["repaired"]),
        "--repaired-qualification-checksum", checksums["repaired"],
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_commits_checkpoint_before_success_report(tmp_path):
    paths, checksums, manifest_checksum = fixture_files(tmp_path)
    writes = []

    exit_code = main(
        arguments(tmp_path, paths, checksums, manifest_checksum),
        clock=lambda: NOW,
        checkpoint_writer=lambda path, value: writes.append(("checkpoint", value)),
        report_writer=lambda path, value: writes.append(("report", value)),
    )

    assert exit_code == 0
    assert [name for name, value in writes] == ["checkpoint", "report"]
    assert writes[0][1]["outcomes"]["PRIVATE"]["status"] == "FINAL_FAILED"
    assert "PRIVATE" not in str(writes[1][1])


def test_cli_writer_failure_does_not_claim_checkpoint_transition(tmp_path):
    paths, checksums, manifest_checksum = fixture_files(tmp_path)
    reports = []

    def fail_checkpoint(path, value):
        raise OSError("private path")

    exit_code = main(
        arguments(tmp_path, paths, checksums, manifest_checksum),
        clock=lambda: NOW,
        checkpoint_writer=fail_checkpoint,
        report_writer=lambda path, value: reports.append(value),
    )

    assert exit_code == 1
    assert reports[0]["status"] == "FAILED"
    assert reports[0]["failure"]["category"] == "CHECKPOINT_WRITE_FAILED"
    assert reports[0]["coverage"] is None
    assert "private path" not in str(reports[0])
