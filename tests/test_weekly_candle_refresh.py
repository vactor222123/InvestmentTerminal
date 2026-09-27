from datetime import datetime, timedelta, timezone
import json

import pytest
from yfinance.exceptions import YFRateLimitError

from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from investment_terminal.cli.weekly_candle_refresh import main
from investment_terminal.database.database import Database
from investment_terminal.indicators.technical_indicators import TechnicalIndicators
from investment_terminal.models.candle import Candle
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    WeeklyCandleRefreshService,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.exceptions import APIError
from tests.test_manifest_collection_sweep import checkpoint, manifest, outcome
from investment_terminal.operations.manifest_collection_sweep import ManifestCollectionSweepPlan


END = datetime(2026, 9, 22, tzinfo=timezone.utc)
LAST = END - timedelta(days=2)


def candle(symbol, timestamp, close=10.0):
    return Candle(symbol=symbol, resolution="D", timestamp=timestamp,
                  open_price=10.0, high_price=max(11.0, close), low_price=9.0,
                  close_price=close, volume=100.0, currency="USD")


def plan_and_sources(*, missing=False, excluded=False):
    value, checksum = manifest(batch_count=2)
    source = ManifestCollectionSweepPlan.from_manifest(value, checksum, max_batches=1)
    sources = {i: checkpoint(request) for i, request in enumerate(source.requests, 1)}
    if missing:
        sources.pop(2)
    if excluded:
        symbol = source.requests[1].items[0].symbol
        sources[2]["outcomes"][symbol] = outcome("EMPTY")
    return value, checksum, sources


class Client:
    def __init__(self, *, drift=False, failure=None):
        self.calls = []
        self.drift = drift
        self.failure = failure

    def get_candle_projection(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure is not None:
            raise self.failure
        symbol = kwargs["symbol"]
        return YahooCandleProjection((
            candle(symbol, LAST, close=12.0 if self.drift else 10.0),
            candle(symbol, LAST + timedelta(days=1)),
        ), 0, ())


def test_plan_requires_complete_bound_source_and_excludes_non_success():
    value, checksum, sources = plan_and_sources(missing=True)
    with pytest.raises(ValueError, match="Complete source"):
        WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    value, checksum, sources = plan_and_sources(excluded=True)
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    assert len(plan.items) == 1 and plan.excluded_count == 1
    with pytest.raises(ValueError):
        WeeklyCandleRefreshPlan.from_manifest(value, "0" * 64, sources.get, end=END)


def test_stores_new_candle_and_resumes_without_extra_provider_call(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    client = Client()
    written = []
    service = WeeklyCandleRefreshService(
        client=client, repository=repo, checkpoint_writer=written.append,
        clock=lambda: END,
    )
    first = service.run(plan, max_items=1)
    assert first["status"] == "BUDGET_EXHAUSTED"
    assert first["coverage"]["inserted_total"] == 1
    assert first["coverage"]["duplicate_total"] == 1
    assert repo.count(plan.items[0][0], "D") == 2
    second = service.run(plan, written[-1], max_items=2)
    assert second["status"] == "COMPLETE"
    assert second["coverage"]["remaining_count"] == 0
    assert len(client.calls) == 2
    assert len(written) == 2
    assert repo.get_range(plan.items[0][0], "D")[-1].close_price == 10.0
    assert TechnicalIndicators.sma(repo.get_range(plan.items[0][0], "D"), 2)[-1] == 10.0
    assert all(symbol not in str(second) for symbol, _ in plan.items)
    db.close()


def test_drift_is_isolated_and_preserves_existing_candle(tmp_path):
    value, checksum, sources = plan_and_sources(excluded=True)
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    repo.save(candle(plan.items[0][0], LAST))
    written = []
    report = WeeklyCandleRefreshService(
        client=Client(drift=True), repository=repo,
        checkpoint_writer=written.append, clock=lambda: END,
    ).run(plan, max_items=1)
    assert report["status"] == "COMPLETE_WITH_FAILURES"
    assert report["failure_categories"] == [
        {"category": "STORED_CANDLE_DRIFT", "count": 1}
    ]
    assert repo.count(plan.items[0][0], "D") == 1
    assert written[-1]["outcomes"][plan.items[0][0]]["status"] == "FAILED"
    db.close()


def test_rate_limit_halts_and_invalid_resume_does_not_call_provider(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    error = APIError("private provider text")
    error.__cause__ = YFRateLimitError()
    client = Client(failure=error)
    written = []
    service = WeeklyCandleRefreshService(
        client=client, repository=repo,
        checkpoint_writer=written.append, clock=lambda: END,
    )
    report = service.run(plan, max_items=2)
    assert report["status"] == "HALTED"
    assert report["coverage"]["remaining_count"] == 1
    assert "private provider text" not in str(report)
    assert len(client.calls) == 1
    written[-1]["selection_checksum"] = "0" * 64
    with pytest.raises(ValueError, match="binding"):
        service.run(plan, written[-1], max_items=2)
    assert len(client.calls) == 1
    db.close()


def test_opt_in_retry_recovers_rate_limit_before_new_series(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    error = APIError("private provider text")
    error.__cause__ = YFRateLimitError()
    writes = []
    first = WeeklyCandleRefreshService(
        client=Client(failure=error), repository=repo,
        checkpoint_writer=writes.append, clock=lambda: END,
    ).run(plan, max_items=2)
    assert first["status"] == "HALTED"
    checkpoint_before_retry = writes[-1]

    recovered = Client()
    service = WeeklyCandleRefreshService(
        client=recovered, repository=repo,
        checkpoint_writer=writes.append, clock=lambda: END,
    )
    report = service.run(
        plan, checkpoint_before_retry, max_items=2, retry_rate_limited=True,
    )
    assert report["schema_version"] == 2
    assert report["status"] == "COMPLETE"
    assert report["budget"] == {"max_items": 2, "retry_rate_limited": True}
    assert report["coverage"]["current_run_attempted_count"] == 2
    assert report["coverage"]["current_run_retry_count"] == 1
    assert report["coverage"]["current_run_new_count"] == 1
    assert report["coverage"]["completed_count"] == 2
    assert report["failure_categories"] == []
    assert len(recovered.calls) == 2
    assert recovered.calls[0]["symbol"] == plan.items[0][0]
    assert writes[-1]["schema_version"] == 1
    assert all(repo.count(symbol, "D") == 2 for symbol, _ in plan.items)
    assert all(symbol not in str(report) for symbol, _ in plan.items)
    with pytest.raises(ValueError, match="No checkpointed rate limit"):
        service.run(plan, writes[-1], max_items=1, retry_rate_limited=True)
    assert len(recovered.calls) == 2
    db.close()


def test_repeated_rate_limit_retries_only_same_series_and_preserves_checkpoint(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    error = APIError("private provider text")
    error.__cause__ = YFRateLimitError()
    client = Client(failure=error)
    writes = []
    service = WeeklyCandleRefreshService(
        client=client, repository=repo,
        checkpoint_writer=writes.append, clock=lambda: END,
    )
    service.run(plan, max_items=2)
    previous = writes[-1]
    report = service.run(plan, previous, max_items=2, retry_rate_limited=True)
    assert report["status"] == "HALTED"
    assert report["schema_version"] == 2
    assert report["coverage"]["current_run_attempted_count"] == 1
    assert report["coverage"]["current_run_retry_count"] == 1
    assert report["coverage"]["current_run_new_count"] == 0
    assert report["coverage"]["completed_count"] == 1
    assert report["coverage"]["remaining_count"] == 1
    assert writes[-1] == previous
    assert len(client.calls) == 2
    assert all(call["symbol"] == plan.items[0][0] for call in client.calls)
    assert "private provider text" not in str(report)
    ordinary_client = Client()
    ordinary = WeeklyCandleRefreshService(
        client=ordinary_client, repository=repo,
        checkpoint_writer=lambda payload: None, clock=lambda: END,
    ).run(plan, previous, max_items=1)
    assert ordinary["schema_version"] == 1
    assert ordinary["coverage"]["current_run_attempted_count"] == 1
    assert ordinary["failure_categories"] == [
        {"category": "RATE_LIMITED", "count": 1}
    ]
    assert ordinary_client.calls[0]["symbol"] == plan.items[1][0]
    db.close()


def test_retry_checkpoint_write_failure_can_repeat_idempotently(tmp_path):
    value, checksum, sources = plan_and_sources(excluded=True)
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    symbol = plan.items[0][0]
    repo.save(candle(symbol, LAST))
    error = APIError("private provider text")
    error.__cause__ = YFRateLimitError()
    writes = []
    WeeklyCandleRefreshService(
        client=Client(failure=error), repository=repo,
        checkpoint_writer=writes.append, clock=lambda: END,
    ).run(plan, max_items=1)
    original = writes[-1]

    def fail_write(payload):
        raise RuntimeError("checkpoint write failed")

    with pytest.raises(RuntimeError, match="checkpoint write failed"):
        WeeklyCandleRefreshService(
            client=Client(), repository=repo,
            checkpoint_writer=fail_write, clock=lambda: END,
        ).run(plan, original, max_items=1, retry_rate_limited=True)
    assert repo.count(symbol, "D") == 2
    assert original["outcomes"][symbol]["category"] == "RATE_LIMITED"

    report = WeeklyCandleRefreshService(
        client=Client(), repository=repo,
        checkpoint_writer=writes.append, clock=lambda: END,
    ).run(plan, original, max_items=1, retry_rate_limited=True)
    assert report["status"] == "COMPLETE"
    assert report["coverage"]["current_run_retry_count"] == 1
    assert report["coverage"]["inserted_total"] == 0
    assert report["coverage"]["duplicate_total"] == 2
    assert repo.count(symbol, "D") == 2
    db.close()


def test_cli_writes_private_checkpoint_and_redacted_report(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    manifest_path = tmp_path / "manifest.json"
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    for index, source in sources.items():
        (source_directory / f"batch_{index:04d}.json").write_text(
            json.dumps(source), encoding="utf-8"
        )
    database_path = tmp_path / "candles.db"
    db = Database(database_path)
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    db.close()
    checkpoint_path = tmp_path / "weekly.json"
    report_path = tmp_path / "report.json"
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_directory),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(database_path), "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(report_path), "--end", END.isoformat(),
        "--max-items", "2",
    ]
    client = Client()
    assert main(args, client=client, clock=lambda: END) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "COMPLETE"
    assert report["coverage"]["inserted_total"] == 2
    assert all(symbol not in str(report) for symbol, _ in plan.items)
    assert set(json.loads(checkpoint_path.read_text(encoding="utf-8"))["outcomes"]) == {
        symbol for symbol, _ in plan.items
    }
    assert main(args, client=client, clock=lambda: END) == 0
    assert len(client.calls) == 2


def test_cli_preflight_does_not_create_missing_database(tmp_path):
    report = tmp_path / "report.json"
    result = main([
        "--manifest", str(tmp_path / "missing.json"),
        "--manifest-checksum", "a" * 64,
        "--source-checkpoint-directory", str(tmp_path / "source"),
        "--weekly-checkpoint", str(tmp_path / "weekly.json"),
        "--database", str(tmp_path / "missing.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(report), "--end", END.isoformat(),
        "--max-items", "1",
    ], clock=lambda: END)
    assert result == 1
    assert not (tmp_path / "missing.db").exists()
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "FAILED"


def test_cli_opt_in_retry_versions_report_and_keeps_checkpoint_schema(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    manifest_path = tmp_path / "manifest.json"
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    for index, source in sources.items():
        (source_directory / f"batch_{index:04d}.json").write_text(
            json.dumps(source), encoding="utf-8"
        )
    database_path = tmp_path / "candles.db"
    db = Database(database_path)
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    db.close()
    checkpoint_path = tmp_path / "weekly.json"
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_directory),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(database_path),
        "--cache-directory", str(tmp_path / "cache"),
        "--end", END.isoformat(), "--max-items", "1",
    ]
    error = APIError("private provider text")
    error.__cause__ = YFRateLimitError()
    first_report = tmp_path / "first.json"
    assert main(args + ["--report-output", str(first_report)],
                client=Client(failure=error), clock=lambda: END) == 1
    assert json.loads(first_report.read_text(encoding="utf-8"))["status"] == "HALTED"
    retry_report = tmp_path / "retry.json"
    client = Client()
    assert main(args + [
        "--report-output", str(retry_report), "--retry-rate-limited",
    ], client=client, clock=lambda: END) == 0
    report = json.loads(retry_report.read_text(encoding="utf-8"))
    assert report["schema_version"] == 2
    assert report["status"] == "BUDGET_EXHAUSTED"
    assert report["coverage"]["completed_count"] == 1
    assert report["coverage"]["current_run_retry_count"] == 1
    assert report["coverage"]["current_run_new_count"] == 0
    assert json.loads(checkpoint_path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert len(client.calls) == 1
    assert client.calls[0]["symbol"] == plan.items[0][0]
    failed_report = tmp_path / "no-rate-limit.json"
    assert main(args + [
        "--report-output", str(failed_report), "--retry-rate-limited",
    ], client=client, clock=lambda: END) == 1
    failed = json.loads(failed_report.read_text(encoding="utf-8"))
    assert failed["schema_version"] == 2
    assert failed["status"] == "FAILED"
    assert failed["coverage"] is None
    assert len(client.calls) == 1


def test_per_series_provider_failure_continues_but_persistence_failure_stops(tmp_path):
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    db = Database(tmp_path / "candles.db")
    db.initialize()
    repo = CandleRepository(db)
    for symbol, _ in plan.items:
        repo.save(candle(symbol, LAST))
    client = Client(failure=RuntimeError("private"))
    written = []
    service = WeeklyCandleRefreshService(
        client=client, repository=repo,
        checkpoint_writer=written.append, clock=lambda: END,
    )
    report = service.run(plan, max_items=2)
    assert report["status"] == "COMPLETE_WITH_FAILURES"
    assert len(client.calls) == 2
    assert len(written) == 2
    assert "private" not in str(report)

    class BrokenRepository:
        def get_latest(self, symbol, resolution):
            return candle(symbol, LAST)

        def get_range(self, symbol, resolution, start, end):
            return [candle(symbol, LAST)]

        def save_many(self, candles):
            raise RuntimeError("private storage failure")

    client = Client()
    writes = []
    service = WeeklyCandleRefreshService(
        client=client, repository=BrokenRepository(),
        checkpoint_writer=writes.append, clock=lambda: END,
    )
    with pytest.raises(Exception, match="Candle persistence failed"):
        service.run(plan, max_items=2)
    assert len(client.calls) == 1 and writes == []
    db.close()
