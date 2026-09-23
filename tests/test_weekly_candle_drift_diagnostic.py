import json

import pytest

from investment_terminal.cli.weekly_candle_drift_diagnostic import main
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_drift_diagnostic import (
    WeeklyCandleDriftDiagnosticService,
)
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
)
from investment_terminal.repositories.candle_repository import CandleRepository
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
