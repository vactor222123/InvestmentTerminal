import json

from investment_terminal.cli import manifest_collection_sweep as cli
from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from investment_terminal.models.candle import Candle
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
)
from tests.test_manifest_collection_sweep import NOW, checkpoint, manifest


class Client:
    def get_candle_projection(self, *, symbol, resolution, start, end, currency,
                              allow_trailing_incomplete):
        return YahooCandleProjection((Candle(
            symbol=symbol,
            resolution=resolution,
            timestamp=NOW.replace(day=14),
            open_price=1,
            high_price=1,
            low_price=1,
            close_price=1,
            volume=1,
            currency=currency,
        ),), 0, ())


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--checkpoint-directory", str(tmp_path / "checkpoints"),
        "--database", str(tmp_path / "market.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(tmp_path / "report.json"),
        "--max-batches", "1",
    ]


def test_cli_resumes_after_sweep_covered_checkpoint(tmp_path):
    value, checksum = manifest(batch_count=2)
    plan = ManifestCollectionSweepPlan.from_manifest(
        value, checksum, max_batches=1
    )
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    (directory / "batch_0001.json").write_text(
        json.dumps(checkpoint(plan.requests[0])), encoding="utf-8"
    )

    result = cli.main(arguments(tmp_path, checksum), client=Client(), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "COMPLETE"
    assert report["starting_coverage"]["sweep_covered_batch_count"] == 1
    assert report["ending_coverage"]["sweep_covered_batch_count"] == 2
    assert "S2_1" not in report_text
    assert (directory / "batch_0002.json").exists()


def test_invalid_manifest_fails_before_database_open(tmp_path, monkeypatch):
    value, _ = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")

    class DatabaseMustNotOpen:
        def __init__(self, path):
            raise AssertionError("database opened")

    monkeypatch.setattr(cli, "Database", DatabaseMustNotOpen)
    result = cli.main(arguments(tmp_path, "0" * 64), client=Client(), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["failure_types"] == ["ValueError"]
    assert "database opened" not in report_text


def test_invalid_checkpoint_fails_before_database_open(tmp_path, monkeypatch):
    value, checksum = manifest(batch_count=2)
    plan = ManifestCollectionSweepPlan.from_manifest(
        value, checksum, max_batches=1
    )
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    (directory / "batch_0002.json").write_text(
        json.dumps(checkpoint(plan.requests[1])), encoding="utf-8"
    )

    class DatabaseMustNotOpen:
        def __init__(self, path):
            raise AssertionError("database opened")

    monkeypatch.setattr(cli, "Database", DatabaseMustNotOpen)
    result = cli.main(arguments(tmp_path, checksum), client=Client(), clock=lambda: NOW)

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["failure_types"] == ["ValueError"]
