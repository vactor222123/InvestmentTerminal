"""UTC storage/query safety against synthetic legacy and concurrent data."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
import sqlite3
from unittest.mock import Mock

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_finance_client import (
    YahooFinanceClient, YahooCandleInvalidResponseError, YahooCandleFailureCategory,
    classify_yahoo_candle_failure,
)
from investment_terminal.database.database import Database
from investment_terminal.repositories.candle_repository import (
    CandleRepository, CandleConflictError, CandleTimestampCompatibilityError,
)
from investment_terminal.services.historical_market_service import HistoricalMarketService
from investment_terminal.services.projected_historical_market_service import ProjectedHistoricalMarketService
from tests.test_candle_time_unit_audit import INSTANT, candle, repository
from tests.test_yahoo_finance_client import create_history_frame, create_period


def seed_legacy(repository, timestamp, *, symbol="SYNTH", close=100):
    connection = repository.database.connection
    cursor = connection.execute(
        "INSERT INTO candles (symbol,resolution,timestamp,open_price,high_price,"
        "low_price,close_price,volume,currency) VALUES (?, 'D', ?, 100, 102, 98, ?, 10, 'USD')",
        (symbol, timestamp, close),
    )
    connection.commit()
    return cursor.lastrowid


def stored(repository):
    return [tuple(row) for row in repository.database.connection.execute(
        "SELECT * FROM candles ORDER BY id")]


@pytest.mark.parametrize("legacy", [
    "2026-01-02T13:00:00+01:00", "2026-01-02T07:00:00-05:00",
    "2026-01-02T12:00:00", "not-a-date", "2026-02-30T12:00:00+00:00",
    "2026-01-02T12:00:00Z", "2026-01-02 12:00:00+00:00",
    "2026-01-02T12:00:00.000000+00:00", "2026-01-02T12:00:00.1+00:00",
    "2026-01-02T12:00:00.000000001+00:00", b"invalid blob",
])
@pytest.mark.parametrize("operation", ["save", "save_many", "get", "get_latest", "get_earliest", "get_range"])
def test_incompatible_series_blocks_without_rewriting(repository, legacy, operation):
    row_id = seed_legacy(repository, legacy)
    before = stored(repository)
    connection = repository.database.connection
    statements = []
    connection.set_trace_callback(statements.append)
    with pytest.raises(CandleTimestampCompatibilityError) as caught:
        if operation == "save":
            repository.save(candle())
        elif operation == "save_many":
            repository.save_many([replace(candle(), symbol="OTHER"), candle()])
        elif operation == "get":
            repository.get(row_id)
        elif operation == "get_range":
            # Even a query outside the bad row must not hide an unsafe series.
            repository.get_range("SYNTH", "D", INSTANT + timedelta(days=10))
        else:
            getattr(repository, operation)("SYNTH", "D")
    connection.set_trace_callback(None)
    assert str(caught.value) == "Stored candle timestamps require explicit compatibility review"
    assert not any(sql.lstrip().upper().startswith("INSERT") for sql in statements)
    assert stored(repository) == before
    assert not connection.in_transaction


@pytest.mark.parametrize("close", [100, 101])
def test_legacy_equivalent_duplicate_never_auto_merges(repository, close):
    seed_legacy(repository, INSTANT.isoformat())
    seed_legacy(repository, "2026-01-02T13:00:00+01:00", close=close)
    before = stored(repository)
    with pytest.raises(CandleTimestampCompatibilityError):
        repository.save(candle())
    assert stored(repository) == before


def test_compatible_legacy_replay_keeps_id_bytes_and_input(repository):
    old_id = seed_legacy(repository, INSTANT.isoformat())
    before = stored(repository)
    offset = INSTANT.astimezone(timezone(timedelta(hours=-7)))
    model = candle(offset)
    assert repository.save(model) == old_id
    assert model.timestamp is offset
    assert stored(repository) == before
    assert repository.get(old_id).timestamp.tzinfo == timezone.utc


def test_incompatible_other_series_does_not_block_target(repository):
    seed_legacy(repository, "naive-or-invalid", symbol="OTHER")
    assert repository.save_many([candle()]) == 1
    assert repository.get_latest("SYNTH", "D").timestamp == INSTANT
    assert repository.count("OTHER", "D") == 1


@pytest.mark.parametrize("micros", [0, 1, 100000, 999999])
def test_fractional_bounds_and_key_identity(repository, micros):
    instant = INSTANT.replace(microsecond=micros)
    earlier = instant - timedelta(microseconds=1)
    later = instant + timedelta(microseconds=1)
    repository.save_many([candle(later), candle(instant), candle(earlier)])
    offset = instant.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert repository.save_many([candle(offset)]) == 0
    assert [x.timestamp for x in repository.get_range("SYNTH", "D")] == [earlier, instant, later]
    assert [x.timestamp for x in repository.get_range("SYNTH", "D", offset, offset)] == [instant]
    assert repository.get_earliest("SYNTH", "D").timestamp == earlier
    assert repository.get_latest("SYNTH", "D").timestamp == later


def test_same_wall_clock_dst_offsets_are_distinct_instants(repository):
    first = datetime(2026, 10, 25, 2, 30, tzinfo=timezone(timedelta(hours=2)))
    second = first.replace(tzinfo=timezone(timedelta(hours=1)))
    assert repository.save_many([candle(first), candle(second)]) == 2
    assert [x.timestamp.hour for x in repository.get_range("SYNTH", "D")] == [0, 1]


class NoOffset(tzinfo):
    def utcoffset(self, dt):
        return None


@pytest.mark.parametrize("timestamp", [INSTANT.replace(tzinfo=None), INSTANT.replace(tzinfo=NoOffset()),
    pd.NaT, pd.Timestamp("2026-01-02T12:00:00.000000001Z"),
    datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))])
def test_unrepresentable_input_rejected_before_writes(repository, timestamp):
    with pytest.raises((ValueError, TypeError)):
        repository.save_many([candle(), candle(timestamp)])
    assert stored(repository) == []
    assert not repository.database.connection.in_transaction


@pytest.mark.parametrize("bound", ["start", "end"])
def test_naive_query_bound_rejected(repository, bound):
    with pytest.raises(ValueError, match="timezone-aware"):
        repository.get_range("SYNTH", "D", **{bound: INSTANT.replace(tzinfo=None)})


def test_read_does_not_commit_or_rollback_caller_work(repository):
    connection = repository.database.connection
    seed_legacy(repository, "bad")
    connection.execute("CREATE TABLE caller_work (value INTEGER)")
    connection.execute("INSERT INTO caller_work VALUES (7)")
    with pytest.raises(CandleTimestampCompatibilityError):
        repository.get_latest("SYNTH", "D")
    assert repository.get_range("EMPTY", "D") == []
    assert connection.in_transaction
    assert connection.execute("SELECT value FROM caller_work").fetchone()[0] == 7
    connection.rollback()
    assert connection.execute("SELECT COUNT(*) FROM caller_work").fetchone()[0] == 0


def test_write_guard_is_inside_immediate_transaction_once_per_series(repository):
    repository.save(candle())
    statements = []
    repository.database.connection.set_trace_callback(statements.append)
    repository.save_many([candle(INSTANT + timedelta(days=i)) for i in range(100)])
    repository.database.connection.set_trace_callback(None)
    scans = [i for i, sql in enumerate(statements) if sql.startswith("SELECT timestamp FROM candles")]
    assert len(scans) == 1
    assert statements.index("BEGIN IMMEDIATE") < scans[0]
    assert statements[-1] == "COMMIT"
    plan = repository.database.connection.execute(
        "EXPLAIN QUERY PLAN SELECT timestamp FROM candles WHERE symbol = ? AND resolution = ?",
        ("SYNTH", "D"),
    ).fetchall()
    assert any("SEARCH" in row[3] and "INDEX" in row[3] for row in plan)


def test_read_snapshot_and_next_operation_revalidate_external_commit(repository, monkeypatch):
    connection = repository.database.connection
    connection.execute("PRAGMA journal_mode=WAL")
    repository.save(candle())
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    other = sqlite3.connect(path)
    original = repository._validate_stored_timestamps
    def concurrent_change(symbol, resolution):
        original(symbol, resolution)
        other.execute("UPDATE candles SET timestamp = 'bad'")
        other.commit()
    try:
        monkeypatch.setattr(repository, "_validate_stored_timestamps", concurrent_change)
        assert repository.get_latest("SYNTH", "D").timestamp == INSTANT
        monkeypatch.setattr(repository, "_validate_stored_timestamps", original)
        with pytest.raises(CandleTimestampCompatibilityError):
            repository.get_latest("SYNTH", "D")
        with pytest.raises(CandleTimestampCompatibilityError):
            repository.save(candle(INSTANT + timedelta(days=1)))
    finally:
        other.close()


def test_reopen_does_not_assume_prior_validation(repository):
    repository.save(candle())
    path = repository.database.connection.execute("PRAGMA database_list").fetchone()[2]
    seed_legacy(repository, "bad")
    reopened = Database(path)
    try:
        with pytest.raises(CandleTimestampCompatibilityError):
            CandleRepository(reopened).save(candle())
    finally:
        reopened.close()


@pytest.mark.parametrize("timestamp", [pd.NaT, datetime(2026, 7, 1),
    INSTANT.replace(tzinfo=NoOffset()), pd.Timestamp("2026-07-01T00:00:00.000000001Z"),
    datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))])
@pytest.mark.parametrize("allow_omission", [False, True])
def test_provider_timestamp_defect_is_typed_and_never_omitted(timestamp, allow_omission):
    frame = create_history_frame()
    frame.index = pd.Index([frame.index[0], timestamp], dtype=object)
    frame.iloc[-1, frame.columns.get_loc("Close")] = float("nan")
    client = YahooFinanceClient(ticker_factory=lambda _: Mock(history=lambda **_: frame))
    with pytest.raises(YahooCandleInvalidResponseError) as caught:
        client.get_candle_projection("SYNTH", "D", *create_period(),
                                    allow_trailing_incomplete=allow_omission)
    assert classify_yahoo_candle_failure(caught.value) == YahooCandleFailureCategory.RESPONSE_TIMESTAMP
    assert YahooFinanceClient.assess_trailing_incomplete_frame(
        frame, resolution="D").rejection_reason == "TIMESTAMP_NOT_NORMALIZABLE"


@pytest.mark.parametrize("service_type", [HistoricalMarketService, ProjectedHistoricalMarketService])
def test_provider_offset_import_replay_and_conflict(repository, service_type):
    frame = create_history_frame()
    frame.index = frame.index.tz_convert("America/New_York")
    client = YahooFinanceClient(ticker_factory=lambda _: Mock(history=lambda **_: frame))
    service = service_type(client, repository)
    args = ("SYNTH", "D", *create_period())
    assert service.import_candles(*args).inserted == 2
    assert service.import_candles(*args).duplicates == 2
    before = stored(repository)
    frame.iloc[0, frame.columns.get_loc("Close")] = 104
    with pytest.raises(CandleConflictError):
        service.import_candles(*args)
    assert stored(repository) == before


def test_weekly_legacy_gate_stops_before_provider_and_checkpoint(repository):
    from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, WeeklyCandleRefreshService
    from tests.test_weekly_candle_refresh import plan_and_sources, END, Client
    value, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(value, checksum, sources.get, end=END)
    seed_legacy(repository, "bad", symbol=plan.items[0][0])
    client, writes = Client(), []
    with pytest.raises(CandleTimestampCompatibilityError):
        WeeklyCandleRefreshService(client=client, repository=repository,
            checkpoint_writer=writes.append, clock=lambda: END).run(plan, max_items=2)
    assert client.calls == [] and writes == []
