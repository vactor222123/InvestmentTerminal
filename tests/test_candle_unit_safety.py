"""Synthetic A03 boundaries; never contact Yahoo or inspect runtime files."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from investment_terminal.clients.yahoo_chart_metadata_client import YahooChartMetadataClient
from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.market.candle_currency import (
    CandleUnitError, UnverifiedYahooUnitError,
    normalize_candle_currency, require_yahoo_candle_currency,
)
from investment_terminal.operations.market_batch_manifest import MarketBatchManifestService, _manifest_checksum
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem, MarketBatchRequest, ResumableMarketBatchService,
)
from investment_terminal.operations.symbol_currency_qualification import SymbolCurrencyQualificationService, _checksum
from investment_terminal.operations.symbol_currency_drain import SymbolCurrencyDrainService
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, WeeklyCandleRefreshService
from tests.test_candle_time_unit_audit import candle, repository, INSTANT
from tests.test_market_batch_manifest import evidence
from tests.test_yahoo_finance_client import create_history_frame


@pytest.mark.parametrize("label", ["GBp", " GBp ", "ZAc", "USc", "Usd", "gBp", "US", "USDD", "12A", "U\u015eD", "\uff35SD"])
def test_noncanonical_unit_is_not_folded(label):
    with pytest.raises(CandleUnitError):
        normalize_candle_currency(label)


@pytest.mark.parametrize("label,expected", [("USD", "USD"), (" usd ", "USD"), ("EUR", "EUR"), ("cad", "CAD"), ("GBP", "GBP")])
def test_generic_label_control(label, expected):
    assert normalize_candle_currency(label) == expected


@pytest.mark.parametrize("label", ["GBP", "gbp", " GBP ", "GBp"])
def test_yahoo_string_only_path_blocks_collision_family(label):
    with pytest.raises(CandleUnitError):
        require_yahoo_candle_currency(label)


@pytest.mark.parametrize("label", ["GBp", "GBP", "gbp", "ZAc"])
def test_metadata_rejects_before_source_label_is_lost(label):
    factory = Mock(return_value=SimpleNamespace(get_history_metadata=lambda: {"currency": label}))
    with pytest.raises(CandleUnitError):
        YahooChartMetadataClient(ticker_factory=factory).get_currency("PRIVATE")
    factory.assert_called_once_with("PRIVATE")


@pytest.mark.parametrize("method", ["save", "save_many"])
@pytest.mark.parametrize("label", ["GBp", "ZAc", "USc", "Usd"])
def test_repository_rejects_all_before_mutation(repository, method, label):
    original = candle()
    identifier = repository.save(original)
    bad = candle(INSTANT + timedelta(days=2), currency=label)
    with pytest.raises(CandleUnitError):
        if method == "save":
            repository.save(bad)
        else:
            repository.save_many([candle(INSTANT + timedelta(days=1)), bad])
    assert repository.count("SYNTH", "D") == 1
    assert repository.get(identifier) == original
    assert not repository.database.connection.in_transaction
    assert repository.save(original) == identifier


@pytest.mark.parametrize("method", ["get_candles", "get_candle_projection"])
@pytest.mark.parametrize("label", ["GBp", "GBP", "ZAc"])
def test_live_client_rejects_before_ticker_creation(method, label):
    factory = Mock()
    client = YahooFinanceClient(ticker_factory=factory)
    with pytest.raises(CandleUnitError):
        getattr(client, method)("PRIVATE", "D", INSTANT, INSTANT + timedelta(days=1), currency=label)
    factory.assert_not_called()


@pytest.mark.parametrize("empty", [True, False])
def test_strict_projection_checks_unit_even_for_empty_frame(empty):
    frame = pd.DataFrame() if empty else create_history_frame()
    with pytest.raises(CandleUnitError):
        YahooFinanceClient.project_history_frame_strict(frame, symbol="PRIVATE", resolution="D", currency="GBp")


@pytest.mark.parametrize("schema", [1, 2])
@pytest.mark.parametrize("operation", ["slice", "drain"])
def test_old_success_is_not_recertified_or_migrated(schema, operation):
    projection, checksum, checkpoint = evidence(1)
    checkpoint["schema_version"] = schema
    checkpoint["request_checksum"] = _checksum({"schema_version": schema,
        "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION", "projection_checksum": checksum})
    checkpoint["outcomes"]["S000"]["currency"] = "GBP"
    original = deepcopy(checkpoint)
    client = Mock(); writer = Mock()
    service_type = SymbolCurrencyQualificationService if operation == "slice" else SymbolCurrencyDrainService
    service = service_type(client=client, checkpoint_writer=writer, clock=lambda: INSTANT)
    bound = {"max_items": 1} if operation == "slice" else {"max_total_items": 1}
    with pytest.raises(UnverifiedYahooUnitError):
        service.run(projection, checksum, checkpoint, **bound)
    assert checkpoint == original
    writer.assert_not_called()
    client.get_currency.assert_not_called()


def test_injected_client_cannot_publish_ambiguous_success():
    projection, checksum, _ = evidence(1)
    writes = []
    client = Mock(); client.get_currency.return_value = "GBp"
    service = SymbolCurrencyQualificationService(client=client, checkpoint_writer=writes.append, clock=lambda: INSTANT)
    report = service.run(projection, checksum, max_items=1)
    assert report["coverage"]["success_count"] == 0
    assert writes[-1]["outcomes"]["S000"]["currency"] is None
    assert "GBp" not in str(report) and "S000" not in str(report)


def test_old_currency_checkpoint_cannot_build_new_manifest():
    projection, checksum, checkpoint = evidence(1)
    checkpoint["outcomes"]["S000"]["currency"] = "GBP"
    original = deepcopy(checkpoint)
    with pytest.raises(UnverifiedYahooUnitError):
        MarketBatchManifestService(clock=lambda: INSTANT).run(projection, checksum, checkpoint,
            resolution="D", start=INSTANT - timedelta(days=1), end=INSTANT)
    assert checkpoint == original


def test_old_manifest_blocked_before_weekly_checkpoint_read():
    request = MarketBatchRequest("D", INSTANT - timedelta(days=2), INSTANT,
                                 (MarketBatchItem("PRIVATE", "GBP"),))
    manifest = {"schema_version": 1, "manifest_identity": "QUALIFIED_MARKET_BATCH_MANIFEST",
        "projection_checksum": "a" * 64, "currency_request_checksum": "b" * 64,
        "batches": [{"batch_index": 1, "request_checksum": request.checksum,
                     "request": request.canonical_dict()}]}
    original = deepcopy(manifest); reader = Mock()
    with pytest.raises(UnverifiedYahooUnitError):
        WeeklyCandleRefreshPlan.from_manifest(manifest, _manifest_checksum(manifest), reader,
            end=INSTANT.replace(hour=0))
    assert manifest == original
    reader.assert_not_called()


def test_direct_batch_request_cannot_bypass_gate_via_completed_checkpoint():
    request = MarketBatchRequest("D", INSTANT - timedelta(days=1), INSTANT,
        (MarketBatchItem("PRIVATE", "GBP"),))
    checkpoint = {"schema_version": 4, "request_checksum": request.checksum,
        "outcomes": {"PRIVATE": {"status": "SUCCESS", "downloaded": 1,
            "inserted": 1, "duplicates": 0, "omitted_trailing_count": 0,
            "omission_types": [], "failure_type": None}}}
    importer = Mock(); writer = Mock()
    with pytest.raises(UnverifiedYahooUnitError):
        ResumableMarketBatchService(importer=importer, checkpoint_writer=writer,
            clock=lambda: INSTANT).run(request, checkpoint)
    importer.import_candles.assert_not_called(); writer.assert_not_called()


def test_direct_weekly_plan_cannot_bypass_unit_gate():
    plan = WeeklyCandleRefreshPlan("a" * 64, INSTANT, (("PRIVATE", "GBP"),), 0, "b" * 64)
    client = Mock(); repo = Mock(); writer = Mock()
    with pytest.raises(UnverifiedYahooUnitError):
        WeeklyCandleRefreshService(client=client, repository=repo, checkpoint_writer=writer,
            clock=lambda: INSTANT).run(plan, max_items=1)
    assert client.mock_calls == repo.mock_calls == writer.mock_calls == []


def test_ordinary_checkpoint_exact_resume_is_unchanged():
    projection, checksum, checkpoint = evidence(2)
    original = deepcopy(checkpoint); client = Mock(); writer = Mock()
    report = SymbolCurrencyQualificationService(client=client, checkpoint_writer=writer,
        clock=lambda: INSTANT).run(projection, checksum, checkpoint, max_items=1)
    assert report["schema_version"] == 2 and report["status"] == "COMPLETE"
    assert report["coverage"]["attempted_count"] == 0
    assert checkpoint == original
    client.get_currency.assert_not_called(); writer.assert_not_called()


def test_ordinary_request_serialization_checksum_and_values_unchanged():
    from hashlib import sha256
    import json
    payload = {"schema_version": 1, "resolution": "D", "start": INSTANT.isoformat(),
        "end": (INSTANT + timedelta(days=1)).isoformat(),
        "items": [{"symbol": "SYNTH", "currency": "USD"}]}
    request = MarketBatchRequest.from_dict(payload)
    assert request.canonical_dict() == payload
    assert request.checksum == sha256(json.dumps(payload, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    frame = create_history_frame()
    projected = YahooFinanceClient.project_history_frame_strict(frame, symbol="SYNTH", resolution="D", currency="usd")
    assert [(item.close_price, item.volume, item.currency) for item in projected.candles] == [
        (103.0, 1_000_000, "USD"), (106.0, 1_200_000, "USD")]
