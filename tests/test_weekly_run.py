"""Fail-closed short weekly-run composition tests."""

import json
from datetime import timedelta

from yfinance.exceptions import YFRateLimitError

from investment_terminal.cli.weekly_run import main
from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.exceptions import APIError
from tests.test_weekly_candle_refresh import END, LAST, Client, candle, plan_and_sources


def _setup(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    root = tmp_path / "private"
    root.mkdir()
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_dir = root / "sources"
    source_dir.mkdir()
    for index, source in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(
            json.dumps(source), encoding="utf-8",
        )
    database_path = root / "candles.db"
    database = Database(database_path)
    database.initialize()
    repository = CandleRepository(database)
    plan = WeeklyCandleRefreshPlan.from_manifest(
        manifest, checksum, sources.get, end=END,
    )
    for symbol, _ in plan.items:
        repository.save(candle(symbol, LAST))
    database.close()
    profile_path = root / "profile.json"
    profile = {
        "schema_version": 1,
        "operation_identity": "WEEKLY_RUN_PROFILE",
        "manifest": str(manifest_path),
        "manifest_checksum": checksum,
        "source_checkpoint_directory": str(source_dir),
        "database": str(database_path),
        "cache_directory": str(root / "cache"),
        "weekly_checkpoint_directory": str(root / "weekly"),
        "report_directory": str(tmp_path / "reports"),
    }
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    return profile_path, profile, plan


def _args(profile_path, *, end=END, slice_id="001", max_items=1):
    return [
        "--profile", str(profile_path), "--end", end.isoformat(),
        "--max-items", str(max_items), "--slice-id", slice_id,
    ]


def test_bounded_slices_resume_and_keep_reports_distinct(tmp_path, capsys):
    profile_path, profile, plan = _setup(tmp_path)
    client = Client()
    assert main(_args(profile_path), client=client, clock=lambda: END) == 0
    first_report = (tmp_path / "reports" / "weekly_candle_refresh_2026-09-22_001.json")
    checkpoint = (tmp_path / "private" / "weekly"
                  / "weekly_candle_refresh_2026-09-22.json")
    first = json.loads(first_report.read_text(encoding="utf-8"))
    assert first["status"] == "BUDGET_EXHAUSTED"
    assert first["coverage"]["completed_count"] == 1
    assert len(json.loads(checkpoint.read_text(encoding="utf-8"))["outcomes"]) == 1
    assert not (checkpoint.parent / "weekly_candle_refresh.lock").exists()
    assert main(_args(profile_path, slice_id="002"),
                client=client, clock=lambda: END) == 0
    second_report = (tmp_path / "reports" / "weekly_candle_refresh_2026-09-22_002.json")
    second = json.loads(second_report.read_text(encoding="utf-8"))
    assert second["status"] == "COMPLETE"
    assert second["coverage"]["completed_count"] == len(plan.items)
    assert len(client.calls) == len(plan.items)
    assert "SEND:" in capsys.readouterr().out
    assert profile["manifest"] not in str(first) + str(second)


def test_report_collision_prevents_provider_and_preserves_bytes(tmp_path):
    profile_path, _, _ = _setup(tmp_path)
    report = tmp_path / "reports" / "weekly_candle_refresh_2026-09-22_001.json"
    report.parent.mkdir()
    report.write_bytes(b"existing report")
    client = Client()
    assert main(_args(profile_path), client=client, clock=lambda: END) == 1
    assert report.read_bytes() == b"existing report"
    assert client.calls == []
    assert not (tmp_path / "private" / "weekly").exists()


def test_wrong_end_checkpoint_fails_before_provider(tmp_path):
    profile_path, _, _ = _setup(tmp_path)
    assert main(_args(profile_path), client=Client(), clock=lambda: END) == 0
    next_end = END + timedelta(days=1)
    checkpoint_dir = tmp_path / "private" / "weekly"
    previous = checkpoint_dir / "weekly_candle_refresh_2026-09-22.json"
    wrong = checkpoint_dir / "weekly_candle_refresh_2026-09-23.json"
    wrong.write_bytes(previous.read_bytes())
    client = Client()
    assert main(_args(profile_path, end=next_end),
                client=client, clock=lambda: next_end) == 1
    assert client.calls == []
    assert not (tmp_path / "reports"
                / "weekly_candle_refresh_2026-09-23_001.json").exists()


def test_invalid_profile_and_slice_fail_without_private_output(tmp_path, capsys):
    profile_path, profile, _ = _setup(tmp_path)
    client = Client()
    for bad in ("../x", "1"):
        assert main(_args(profile_path, slice_id=bad),
                    client=client, clock=lambda: END) == 1
    profile["manifest_checksum"] = "0" * 64
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    assert main(_args(profile_path), client=client, clock=lambda: END) == 1
    profile["manifest_checksum"] = "bad"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    assert main(_args(profile_path), client=client, clock=lambda: END) == 1
    assert client.calls == []
    assert not (tmp_path / "reports").exists()
    assert str(profile_path) not in capsys.readouterr().err


def test_cache_overlap_and_naive_clock_fail_before_provider(tmp_path):
    profile_path, profile, _ = _setup(tmp_path)
    profile["cache_directory"] = profile["source_checkpoint_directory"]
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    client = Client()
    assert main(_args(profile_path), client=client, clock=lambda: END) == 1
    profile["cache_directory"] = str(tmp_path / "private" / "cache")
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    assert main(_args(profile_path), client=client,
                clock=lambda: END.replace(tzinfo=None)) == 1
    assert client.calls == []
    assert not (tmp_path / "reports").exists()


def test_existing_weekly_lock_prevents_concurrent_run(tmp_path):
    profile_path, _, _ = _setup(tmp_path)
    checkpoint_dir = tmp_path / "private" / "weekly"
    checkpoint_dir.mkdir()
    lock = checkpoint_dir / "weekly_candle_refresh.lock"
    lock.write_text("operator-owned", encoding="utf-8")
    client = Client()
    assert main(_args(profile_path), client=client, clock=lambda: END) == 1
    assert lock.read_text(encoding="utf-8") == "operator-owned"
    assert client.calls == []
    assert not (tmp_path / "reports").exists()


def test_rate_limit_keeps_partial_progress_and_nonzero_result(tmp_path):
    profile_path, _, plan = _setup(tmp_path)

    class RateLimitedSecond:
        def __init__(self):
            self.calls = []

        def get_candle_projection(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 2:
                error = APIError("private provider detail")
                error.__cause__ = YFRateLimitError()
                raise error
            symbol = kwargs["symbol"]
            return YahooCandleProjection((
                candle(symbol, LAST), candle(symbol, LAST + timedelta(days=1)),
            ), 0, ())

    client = RateLimitedSecond()
    assert main(_args(profile_path, max_items=2),
                client=client, clock=lambda: END) == 1
    report = json.loads((tmp_path / "reports"
                         / "weekly_candle_refresh_2026-09-22_001.json").read_text(
                             encoding="utf-8"))
    checkpoint = json.loads((tmp_path / "private" / "weekly"
                             / "weekly_candle_refresh_2026-09-22.json").read_text(
                                 encoding="utf-8"))
    assert report["status"] == "HALTED"
    assert report["coverage"]["completed_count"] == 2
    assert report["coverage"]["inserted_total"] == 1
    assert len(checkpoint["outcomes"]) == 2
    assert not (tmp_path / "private" / "weekly"
                / "weekly_candle_refresh.lock").exists()
    assert "private provider detail" not in str(report)
    assert len(client.calls) == len(plan.items)
    retry = Client()
    assert main(_args(profile_path, slice_id="002") + ["--retry-rate-limited"],
                client=retry, clock=lambda: END) == 0
    retry_report = json.loads((tmp_path / "reports"
                               / "weekly_candle_refresh_2026-09-22_002.json").read_text(
                                   encoding="utf-8"))
    assert retry_report["schema_version"] == 2
    assert retry_report["coverage"]["current_run_retry_count"] == 1
    assert retry_report["status"] == "COMPLETE"
    assert len(retry.calls) == 1
