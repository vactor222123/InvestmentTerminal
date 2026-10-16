"""A02/A03 acceptance probes; strict xfails are OPEN defects, not fixes.

Synthetic storage and injected metadata only. Remove each xfail when its
contract is implemented; do not change expectations to preserve the defect.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_chart_metadata_client import YahooChartMetadataClient
from investment_terminal.clients.yahoo_finance_client import (
    YahooFinanceClient, YahooCandleInvalidResponseError,
)
from investment_terminal.database.database import Database
from investment_terminal.models.candle import Candle
from investment_terminal.operations.resumable_market_batch import MarketBatchRequest
from investment_terminal.repositories.candle_repository import CandleRepository, CandleConflictError


UTC = timezone.utc
INSTANT = datetime(2026, 1, 2, 12, tzinfo=UTC)


@pytest.fixture
def repository(tmp_path):
    database = Database(tmp_path / "synthetic.db")
    database.initialize()
    try:
        yield CandleRepository(database)
    finally:
        database.close()


def candle(timestamp=INSTANT, currency="USD", close=100):
    return Candle(symbol="SYNTH", resolution="D", timestamp=timestamp,
                  open_price=100, high_price=102, low_price=98,
                  close_price=close, volume=10, currency=currency)


def test_same_instant_replay_has_one_id(repository):
    first = repository.save(candle())
    offset = INSTANT.astimezone(timezone(timedelta(hours=1)))
    assert repository.save(candle(offset)) == first
    assert repository.count("SYNTH", "D") == 1


def test_same_instant_changed_payload_rolls_back_batch(repository):
    repository.save(candle())
    offset = INSTANT.astimezone(timezone(timedelta(hours=1)))
    with pytest.raises(CandleConflictError):
        repository.save_many([candle(INSTANT + timedelta(days=1)), candle(offset, close=101)])
    assert repository.count("SYNTH", "D") == 1


def test_naive_batch_rejected_without_partial_write(repository):
    with pytest.raises(ValueError):
        repository.save_many([candle(), candle(INSTANT.replace(tzinfo=None))])
    assert repository.count("SYNTH", "D") == 0


def test_equivalent_offset_range_includes_utc_row(repository):
    repository.save(candle())
    bound = INSTANT.astimezone(timezone(timedelta(hours=1)))
    assert len(repository.get_range("SYNTH", "D", bound, bound)) == 1


def test_latest_uses_chronological_order(repository):
    earlier = (INSTANT - timedelta(minutes=30)).astimezone(timezone(timedelta(hours=2)))
    repository.save_many([candle(earlier), candle()])
    assert repository.get_latest("SYNTH", "D").timestamp == INSTANT
    assert repository.get_earliest("SYNTH", "D").timestamp == earlier


def test_yahoo_naive_source_is_not_assumed_utc():
    frame = pd.DataFrame({"Open": [100], "High": [102], "Low": [98],
                          "Close": [100], "Volume": [10]},
                         index=pd.DatetimeIndex([INSTANT.replace(tzinfo=None)]))
    with pytest.raises(YahooCandleInvalidResponseError):
        YahooFinanceClient.project_history_frame_strict(
            frame, symbol="SYNTH", resolution="D", currency="USD")


def test_metadata_does_not_silently_relabel_case_sensitive_unit():
    client = YahooChartMetadataClient(ticker_factory=lambda _: SimpleNamespace(
        get_history_metadata=lambda: {"currency": "GBp"}))
    # A future explicit rejection or unit-bearing contract is also safe; this
    # probe chooses rejection while the existing return type is only a string.
    with pytest.raises(ValueError):
        client.get_currency("SYNTH")


def test_unqualified_unit_rejected_before_storage(repository):
    with pytest.raises(ValueError):
        repository.save(candle(currency="GBp"))
    assert repository.count("SYNTH", "D") == 0


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
def test_canonical_storage_replay_control(repository, currency):
    first = repository.save(candle(currency=currency))
    assert repository.save(candle(currency=currency)) == first
    assert repository.get(first).currency == currency
    assert repository.get_range("SYNTH", "D", INSTANT, INSTANT)[0].timestamp == INSTANT


def test_existing_exact_key_conflict_control(repository):
    repository.save(candle())
    with pytest.raises(CandleConflictError):
        repository.save_many([candle(INSTANT + timedelta(days=1)), candle(close=101)])
    assert repository.count("SYNTH", "D") == 1


def test_request_timestamp_spelling_is_checksum_relevant():
    # Compatibility evidence, not a desired new canonicalization rule.
    payload = {"schema_version": 1, "resolution": "D",
               "start": INSTANT.isoformat(),
               "end": (INSTANT + timedelta(days=1)).isoformat(),
               "items": [{"symbol": "SYNTH", "currency": "USD"}]}
    original = MarketBatchRequest.from_dict(payload)
    offset = timezone(timedelta(hours=1))
    shifted = MarketBatchRequest.from_dict({**payload,
        "start": INSTANT.astimezone(offset).isoformat(),
        "end": (INSTANT + timedelta(days=1)).astimezone(offset).isoformat()})
    assert original.start == shifted.start
    assert original.end == shifted.end
    assert original.checksum != shifted.checksum
