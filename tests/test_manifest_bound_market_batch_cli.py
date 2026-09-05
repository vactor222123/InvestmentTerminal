import json

from investment_terminal.cli import manifest_bound_market_batch as cli
from investment_terminal.models.candle import Candle
from tests.test_manifest_bound_market_batch import NOW, manifest


class Client:
    def get_candles(self, *, symbol, resolution, start, end, currency):
        return [
            Candle(
                symbol=symbol,
                resolution=resolution,
                timestamp=NOW.replace(year=2026, month=9, day=4),
                open_price=1,
                high_price=1,
                low_price=1,
                close_price=1,
                volume=1,
                currency=currency,
            )
        ]


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--database", str(tmp_path / "market.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_executes_one_manifest_batch_and_writes_bound_report(tmp_path):
    value, checksum = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")

    result = cli.main(arguments(tmp_path, checksum), client=Client(), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "SUCCESS"
    assert report["manifest_checksum"] == checksum
    assert report["batch_index"] == 1
    assert report["coverage"]["current_run"]["attempted_count"] == 1
    assert "AAA" not in report_text
    assert (tmp_path / "checkpoint.json").exists()


def test_invalid_manifest_fails_before_database_open(tmp_path, monkeypatch):
    value, checksum = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")

    class DatabaseMustNotOpen:
        def __init__(self, path):
            raise AssertionError("database opened")

    monkeypatch.setattr(cli, "Database", DatabaseMustNotOpen)
    result = cli.main(arguments(tmp_path, "0" * 64), client=Client(), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["failure_types"] == ["ValueError"]
    assert report["manifest_checksum"] is None
    assert "AAA" not in report_text
    assert "database opened" not in report_text


def test_checkpoint_mismatch_writes_bound_failure_report(tmp_path):
    value, checksum = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / "checkpoint.json").write_text(
        json.dumps({"schema_version": 1, "request_checksum": "0" * 64, "outcomes": {}}),
        encoding="utf-8",
    )

    result = cli.main(arguments(tmp_path, checksum), client=Client(), clock=lambda: NOW)

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["manifest_checksum"] == checksum
    assert report["batch_index"] == 1
    assert report["failure_types"] == ["ValueError"]
