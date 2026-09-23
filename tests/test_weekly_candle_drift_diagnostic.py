import json
from dataclasses import replace

import pytest
from yfinance.exceptions import YFRateLimitError

from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from investment_terminal.cli.weekly_candle_drift_diagnostic import main
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_drift_diagnostic import (
    WeeklyCandleDriftAggregateService,
    WeeklyCandleDriftDiagnosticService,
)
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.exceptions import APIError
from tests.test_manifest_collection_sweep import checkpoint as source_checkpoint
from tests.test_manifest_collection_sweep import manifest as source_manifest
from investment_terminal.operations.manifest_collection_sweep import ManifestCollectionSweepPlan
from tests.test_weekly_candle_refresh import (
    Client, END, LAST, candle, plan_and_sources,
)


def setup(tmp_path):
    manifest, checksum, sources = plan_and_sources(excluded=True)
    plan = WeeklyCandleRefreshPlan.from_manifest(
        manifest, checksum, sources.get, end=END
    )
    symbol = plan.items[0][0]
    checkpoint = {
        "schema_version": 1,
        "operation_identity": "WEEKLY_CANDLE_REFRESH",
        "manifest_checksum": checksum,
        "end": END.isoformat(),
        "selection_checksum": plan.selection_checksum,
        "outcomes": {
            symbol: {
                "status": "FAILED", "category": "STORED_CANDLE_DRIFT",
                "downloaded": 0, "inserted": 0, "duplicates": 0,
                "omitted_trailing_count": 0, "stored_count": 0,
            }
        },
    }
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    repo.save(candle(symbol, LAST))
    return manifest, checksum, sources, plan, checkpoint, db, repo


def test_reproduces_one_drift_with_field_counts_but_no_private_values(tmp_path):
    _, _, _, plan, checkpoint, db, repo = setup(tmp_path)
    client = Client(drift=True)
    report = WeeklyCandleDriftDiagnosticService(
        client=client, repository=repo, clock=lambda: END,
    ).run(plan, checkpoint)
    assert report["status"] == "REPRODUCED"
    assert report["overlap_count"] == 1
    assert report["changed_overlap_count"] == 1
    assert report["new_candle_count"] == 1
    assert report["changed_fields"] == [
        {"field": "close_price", "count": 1},
        {"field": "high_price", "count": 1},
    ]
    assert len(client.calls) == 1
    assert repo.count(plan.items[0][0], "D") == 1
    assert plan.items[0][0] not in str(report)
    assert "12.0" not in str(report)
    db.close()


def test_not_reproduced_and_provider_failure_are_distinct(tmp_path):
    _, _, _, plan, checkpoint, db, repo = setup(tmp_path)
    normal = WeeklyCandleDriftDiagnosticService(
        client=Client(), repository=repo, clock=lambda: END,
    ).run(plan, checkpoint)
    assert normal["status"] == "NOT_REPRODUCED"
    failed = WeeklyCandleDriftDiagnosticService(
        client=Client(failure=RuntimeError("private provider text")),
        repository=repo, clock=lambda: END,
    ).run(plan, checkpoint)
    assert failed["status"] == "PROVIDER_FAILURE"
    assert failed["failure_category"] == "UNEXPECTED"
    assert "private provider text" not in str(failed)
    db.close()


def test_invalid_checkpoint_and_no_drift_stop_before_provider(tmp_path):
    _, _, _, plan, checkpoint, db, repo = setup(tmp_path)
    client = Client()
    service = WeeklyCandleDriftDiagnosticService(
        client=client, repository=repo, clock=lambda: END,
    )
    checkpoint["selection_checksum"] = "0" * 64
    with pytest.raises(ValueError, match="binding"):
        service.run(plan, checkpoint)
    checkpoint["selection_checksum"] = plan.selection_checksum
    checkpoint["outcomes"][plan.items[0][0]]["category"] = "RESPONSE_NUMERIC"
    with pytest.raises(ValueError, match="No checkpointed"):
        service.run(plan, checkpoint)
    assert client.calls == []
    db.close()


def test_cli_read_only_database_and_checkpoint_with_redacted_report(tmp_path):
    manifest, checksum, sources, plan, checkpoint, db, repo = setup(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for index, payload in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    before = checkpoint_path.read_bytes()
    db.close()
    client = Client(drift=True)
    report_path = tmp_path / "report.json"
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(tmp_path / "candles.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(report_path),
    ]
    assert main(args, client=client, clock=lambda: END) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "REPRODUCED"
    assert checkpoint_path.read_bytes() == before
    db = Database(tmp_path / "candles.db")
    assert CandleRepository(db).count(plan.items[0][0], "D") == 1
    db.close()
    with pytest.raises(SystemExit, match="overwrite"):
        main(args, client=client, clock=lambda: END)
    assert len(client.calls) == 1


def test_cli_missing_database_fails_without_creating_one(tmp_path):
    report_path = tmp_path / "report.json"
    database_path = tmp_path / "absent.db"
    exit_code = main([
        "--manifest", str(tmp_path / "absent_manifest.json"),
        "--manifest-checksum", "a" * 64,
        "--source-checkpoint-directory", str(tmp_path / "source"),
        "--weekly-checkpoint", str(tmp_path / "absent_weekly.json"),
        "--database", str(database_path),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(report_path),
    ], clock=lambda: END)
    assert exit_code == 1
    assert not database_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "FAILED"
    assert "absent" not in str(report)


def aggregate_setup(tmp_path):
    manifest, checksum = source_manifest(batch_count=9)
    source = ManifestCollectionSweepPlan.from_manifest(
        manifest, checksum, max_batches=1
    )
    checkpoints = {
        index: source_checkpoint(request)
        for index, request in enumerate(source.requests, start=1)
    }
    plan = WeeklyCandleRefreshPlan.from_manifest(
        manifest, checksum, checkpoints.get, end=END
    )
    outcomes = {
        symbol: {
            "status": "FAILED", "category": "STORED_CANDLE_DRIFT",
            "downloaded": 0, "inserted": 0, "duplicates": 0,
            "omitted_trailing_count": 0, "stored_count": 0,
        }
        for symbol, _ in plan.items
    }
    weekly = {
        "schema_version": 1,
        "operation_identity": "WEEKLY_CANDLE_REFRESH",
        "manifest_checksum": checksum,
        "end": END.isoformat(),
        "selection_checksum": plan.selection_checksum,
        "outcomes": outcomes,
    }
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repository = CandleRepository(db)
    for symbol, _ in plan.items:
        repository.save(candle(symbol, LAST))
    return manifest, checksum, checkpoints, plan, weekly, db, repository


class AggregateClient:
    def __init__(self, *, failure_at=None):
        self.calls = []
        self.failure_at = failure_at

    def get_candle_projection(self, **kwargs):
        index = len(self.calls)
        self.calls.append(kwargs)
        if index == self.failure_at:
            error = APIError("private")
            error.__cause__ = YFRateLimitError()
            raise error
        current = candle(kwargs["symbol"], LAST)
        if index < 7:
            current = replace(current, volume=101.0)
        elif index == 7:
            current = candle(kwargs["symbol"], LAST, close=12.0)
        return YahooCandleProjection((current,), 0, ())


def test_aggregate_all_nine_is_redacted_and_distinguishes_volume_only(tmp_path):
    _, _, _, plan, weekly, db, repository = aggregate_setup(tmp_path)
    client = AggregateClient()
    report = WeeklyCandleDriftAggregateService(
        client=client, repository=repository, clock=lambda: END,
    ).run(plan, weekly, max_items=9)
    assert report["schema_version"] == 2
    assert report["status"] == "COMPLETE"
    assert report["attempted_count"] == 9
    assert report["reproduced_count"] == 8
    assert report["not_reproduced_count"] == 1
    assert report["volume_only_count"] == 7
    assert report["non_volume_only_drift_count"] == 1
    assert report["changed_fields"] == [
        {"field": "close_price", "count": 1},
        {"field": "high_price", "count": 1},
        {"field": "volume", "count": 7},
    ]
    assert len(client.calls) == 9
    assert all(symbol not in str(report) for symbol, _ in plan.items)
    db.close()


def test_aggregate_halts_on_rate_limit_and_rejects_partial_budget(tmp_path):
    _, _, _, plan, weekly, db, repository = aggregate_setup(tmp_path)
    client = AggregateClient(failure_at=3)
    service = WeeklyCandleDriftAggregateService(
        client=client, repository=repository, clock=lambda: END,
    )
    with pytest.raises(ValueError, match="full drift cohort"):
        service.run(plan, weekly, max_items=8)
    assert client.calls == []
    report = service.run(plan, weekly, max_items=9)
    assert report["status"] == "HALTED"
    assert report["attempted_count"] == 4
    assert report["remaining_count"] == 5
    assert report["provider_failure_categories"] == [
        {"category": "RATE_LIMITED", "count": 1}
    ]
    assert "private" not in str(report)
    db.close()


def test_cli_aggregate_preserves_database_and_weekly_checkpoint(tmp_path):
    manifest, checksum, sources, plan, weekly, db, repository = aggregate_setup(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for index, payload in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    weekly_path = tmp_path / "weekly.json"
    weekly_path.write_text(json.dumps(weekly), encoding="utf-8")
    before = weekly_path.read_bytes()
    db.close()
    report_path = tmp_path / "aggregate.json"
    client = AggregateClient()
    exit_code = main([
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(weekly_path),
        "--database", str(tmp_path / "candles.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(report_path), "--max-items", "9",
    ], client=client, clock=lambda: END)
    assert exit_code == 0
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "COMPLETE"
    assert weekly_path.read_bytes() == before
    db = Database(tmp_path / "candles.db")
    assert all(CandleRepository(db).count(symbol, "D") == 1
               for symbol, _ in plan.items)
    db.close()
