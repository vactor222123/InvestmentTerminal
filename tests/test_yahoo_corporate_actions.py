"""Normalized action collection, immutable snapshots and failure recovery."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

import pandas as pd
import pytest

from investment_terminal.cli.yahoo_corporate_actions import main
from investment_terminal.clients.yahoo_corporate_actions_client import YahooCorporateActionsClient
from investment_terminal.market.corporate_actions import CorporateActionSnapshot, canonical_bytes
from investment_terminal.operations.yahoo_corporate_actions import (
    ActionValidationError, build_report, build_snapshot, load_snapshot,
)
from investment_terminal.operations.yahoo_price_basis_qualification import PriceBasisRequest
from investment_terminal.utils.atomic_write import write_json_atomic


START = datetime(2020, 8, 1, tzinfo=timezone.utc)
END = datetime(2020, 9, 2, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)
REQUEST = PriceBasisRequest("AAPL", START, END)


def history():
    return pd.DataFrame({
        "Dividends": [0.0, 0.205, 0.0],
        "Stock Splits": [0.0, 0.0, 4.0],
        "Capital Gains": [0.0, 0.1, 0.0],
        # Action collection does not depend on valid OHLCV or fabricate prices.
        "Close": [float("nan"), 110.0, 129.0],
    }, index=pd.DatetimeIndex([
        "2020-08-03", "2020-08-07", "2020-08-31",
    ], tz="America/New_York"))


def metadata():
    return {"symbol": "AAPL", "currency": "USD",
            "exchangeTimezoneName": "America/New_York", "instrumentType": "EQUITY"}


def snapshot(frame=None, meta=None):
    return build_snapshot(REQUEST, history() if frame is None else frame,
                          metadata() if meta is None else meta,
                          fetched_at=NOW, adapter_version="1.6.0")


class Client:
    def __init__(self, frame=None, meta=None, error=None):
        self.frame = history() if frame is None else frame
        self.meta = metadata() if meta is None else meta
        self.error = error
        self.calls = []

    def get_action_history(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.frame, self.meta


def arguments(tmp_path, report="report.json"):
    return ["--symbol", "AAPL", "--start", "2020-08-01", "--end", "2020-09-02",
            "--snapshot-output", str(tmp_path / "snapshot.json"),
            "--report-output", str(tmp_path / report)]


def test_adapter_uses_bounded_history_and_metadata_on_same_ticker():
    calls = []

    class Ticker:
        def history(self, **kwargs):
            calls.append(kwargs)
            return history()

        def get_history_metadata(self):
            calls.append("metadata")
            return metadata()

    def factory(symbol):
        calls.append(symbol)
        return Ticker()

    client = YahooCorporateActionsClient(ticker_factory=factory)
    frame, meta = client.get_action_history(symbol="AAPL", start=START, end=END)
    assert len(frame) == 3 and meta == metadata()
    assert calls == ["AAPL", {
        "start": START, "end": END, "interval": "1d", "actions": True,
        "auto_adjust": False, "back_adjust": False, "repair": False,
        "keepna": True, "rounding": False, "timeout": 20, "raise_errors": True,
    }, "metadata"]


def test_snapshot_roundtrip_order_provenance_and_no_price_or_currency_invention():
    value = snapshot()
    payload = value.to_dict()
    assert CorporateActionSnapshot.from_dict(payload) == value
    assert [event.kind for event in value.events] == ["CAPITAL_GAIN", "DIVIDEND", "SPLIT"]
    assert value.events[1].timestamp.isoformat() == "2020-08-07T04:00:00+00:00"
    assert value.events[1].session_date == "2020-08-07"
    assert value.events[2].value == 4.0
    assert payload["content"]["events"][2]["unit"] == "NEW_SHARES_PER_OLD_SHARE"
    assert all(event["currency"] is None for event in payload["content"]["events"])
    assert payload["action_completeness"] == "UNKNOWN"
    assert "Close" not in json.dumps(payload)
    assert payload["content_sha256"] == sha256(canonical_bytes(payload["content"])).hexdigest()


def test_no_events_is_observed_zero_not_complete_no_actions():
    frame = history().drop(columns="Capital Gains")
    frame["Dividends"] = 0.0
    frame["Stock Splits"] = 0.0
    value = snapshot(frame)
    assert value.events == ()
    report = build_report(value)
    assert report["event_counts"] == {"CAPITAL_GAIN": 0, "DIVIDEND": 0, "SPLIT": 0}
    assert report["capital_gains_field_present"] is False
    assert report["action_completeness"] == "UNKNOWN"


def test_reverse_split_and_case_sensitive_quote_units():
    frame = history()
    frame["Stock Splits"] = [0.0, 0.0, 0.1]
    meta = metadata()
    meta["currency"] = "GBp"
    value = snapshot(frame, meta)
    assert value.quote_currency == "GBp"
    assert value.events[-1].value == 0.1


def test_dst_and_exchange_local_date_preserved():
    frame = history().iloc[:2].copy()
    frame.index = pd.DatetimeIndex(["2020-03-06", "2020-03-09"], tz="America/New_York")
    frame["Dividends"] = [0.1, 0.2]
    request = PriceBasisRequest("AAPL", datetime(2020, 3, 1, tzinfo=timezone.utc), END)
    value = build_snapshot(request, frame, metadata(), fetched_at=NOW, adapter_version="1.6.0")
    dividends = [event for event in value.events if event.kind == "DIVIDEND"]
    assert [event.timestamp.hour for event in dividends] == [5, 4]
    assert [event.session_date for event in dividends] == ["2020-03-06", "2020-03-09"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.2, True, "0.2", None])
@pytest.mark.parametrize("field", ["Dividends", "Stock Splits", "Capital Gains"])
def test_invalid_action_values_are_not_silently_dropped(value, field):
    frame = history()
    frame[field] = pd.Series([value, 0, 0], index=frame.index, dtype=object)
    with pytest.raises(ActionValidationError, match="ACTION_VALUE"):
        snapshot(frame)


@pytest.mark.parametrize("mutation,category", [
    (lambda f: f.drop(columns="Dividends"), "MISSING_ACTION_FIELDS"),
    (lambda f: f.drop(columns="Stock Splits"), "MISSING_ACTION_FIELDS"),
    (lambda f: f.assign(**{"Stock Splits": [0, 1, 0]}), "ACTION_VALUE"),
    (lambda f: f.iloc[::-1], "TIMESTAMP_INDEX"),
    (lambda f: f.set_axis([f.index[0]] * 3), "TIMESTAMP_INDEX"),
    (lambda f: f.set_axis(f.index.tz_localize(None)), "TIMESTAMP_INDEX"),
    (lambda f: f.set_axis(pd.DatetimeIndex([START, START.replace(hour=1), END])), "TIMESTAMP_WINDOW"),
    (lambda f: f.set_axis(pd.DatetimeIndex(["2020-08-03T04:00Z", "2020-08-03T05:00Z", "2020-08-04T04:00Z"])), "DUPLICATE_SESSION_DATE"),
    (lambda f: f.set_axis(["Dividends"] * 4, axis=1), "COLUMN_SHAPE"),
    (lambda f: f.iloc[:0], "EMPTY_HISTORY"),
    (lambda f: pd.concat([f] * 1400), "ROW_LIMIT"),
])
def test_malformed_frame_guard(mutation, category):
    with pytest.raises(ActionValidationError, match=category):
        snapshot(mutation(history()))


@pytest.mark.parametrize("change", [
    {"symbol": "OTHER"}, {"currency": None}, {"currency": "USD secret"},
    {"exchangeTimezoneName": "Not/AZone"}, {"instrumentType": "FUTURE"},
])
def test_bad_metadata_never_produces_snapshot(change):
    with pytest.raises(ActionValidationError):
        snapshot(meta={**metadata(), **change})


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(schema_version=True),
    lambda p: p.update(content_sha256="0" * 64),
    lambda p: p.update(raw_source_presence="VERIFIED"),
    lambda p: p["content"].update(row_count=True),
    lambda p: p["content"].update(extra="unexpected"),
    lambda p: p["content"]["events"][0].update(currency="USD"),
    lambda p: p["content"]["events"][0].update(unit="USD"),
    lambda p: p["content"]["events"][0].update(session_date="2020-08-08"),
    lambda p: p["content"]["events"].reverse(),
])
def test_stored_contract_tampering_rejected(mutate):
    payload = snapshot().to_dict()
    mutate(payload)
    with pytest.raises(ValueError):
        CorporateActionSnapshot.from_dict(payload)


def test_cli_saves_snapshot_and_exact_repeat_is_offline(tmp_path, capsys):
    client = Client()
    assert main(arguments(tmp_path), client=client, clock=lambda: NOW) == 0
    saved = (tmp_path / "snapshot.json").read_bytes()
    first = json.loads((tmp_path / "report.json").read_text())
    assert first["snapshot_sha256"] == sha256(saved).hexdigest()
    assert first["event_counts"] == {"CAPITAL_GAIN": 1, "DIVIDEND": 1, "SPLIT": 1}
    assert first["snapshot_persisted"] is True
    assert first["reused_snapshot"] is False
    assert main(arguments(tmp_path, "repeat.json"), client=client, clock=lambda: NOW) == 0
    assert len(client.calls) == 1
    assert (tmp_path / "snapshot.json").read_bytes() == saved
    repeat = json.loads((tmp_path / "repeat.json").read_text())
    assert repeat["reused_snapshot"] is True
    assert repeat["snapshot_sha256"] == first["snapshot_sha256"]
    rendered = capsys.readouterr().out + json.dumps(first) + json.dumps(repeat)
    for private in ("AAPL", "USD", "0.205", "2020-08-07", str(tmp_path)):
        assert private not in rendered
    assert not list(tmp_path.glob("*.lock"))


def test_provider_error_and_empty_history_have_durable_redacted_failure(tmp_path, capsys):
    client = Client(error=RuntimeError("SECRET AAPL 123.45"))
    assert main(arguments(tmp_path), client=client, clock=lambda: NOW) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["failure_category"] == "PROVIDER_REQUEST"
    assert report["snapshot_persisted"] is False
    assert report["event_counts"] is None
    assert not (tmp_path / "snapshot.json").exists()
    assert "SECRET" not in capsys.readouterr().out
    assert main(arguments(tmp_path, "empty.json"), client=Client(frame=pd.DataFrame()), clock=lambda: NOW) == 1
    assert json.loads((tmp_path / "empty.json").read_text())["failure_category"] == "EMPTY_HISTORY"


def test_invalid_response_writes_no_snapshot(tmp_path):
    assert main(arguments(tmp_path), client=Client(meta={}), clock=lambda: NOW) == 1
    assert not (tmp_path / "snapshot.json").exists()
    assert json.loads((tmp_path / "report.json").read_text())["failure_category"] == "SYMBOL_MISMATCH"


def test_report_write_failure_retains_snapshot_and_recovers_offline(tmp_path):
    client = Client()

    def writer(path, value):
        if path.name == "report.json":
            raise OSError("SECRET path")
        return write_json_atomic(path, value)

    assert main(arguments(tmp_path), client=client, clock=lambda: NOW, writer=writer) == 1
    data = (tmp_path / "snapshot.json").read_bytes()
    assert not (tmp_path / "report.json").exists()
    assert main(arguments(tmp_path), client=client, clock=lambda: NOW) == 0
    assert len(client.calls) == 1
    assert (tmp_path / "snapshot.json").read_bytes() == data


def test_atomic_replace_failure_leaves_no_snapshot(tmp_path, monkeypatch):
    import investment_terminal.utils.atomic_write as atomic
    original = atomic.os.replace

    def replace(source, target):
        if target.name == "snapshot.json":
            raise OSError("write failure")
        return original(source, target)

    monkeypatch.setattr(atomic.os, "replace", replace)
    assert main(arguments(tmp_path), client=Client(), clock=lambda: NOW) == 1
    assert not (tmp_path / "snapshot.json").exists()
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["failure_category"] == "SNAPSHOT_WRITE_OR_VERIFY"
    assert report["snapshot_persisted"] is False
    assert not list(tmp_path.glob("*.tmp"))


def test_post_replace_failure_is_visible_and_recoverable(tmp_path):
    def writer(path, value):
        write_json_atomic(path, value)
        if path.name == "snapshot.json":
            raise OSError("post-replace failure")

    client = Client()
    assert main(arguments(tmp_path), client=client, clock=lambda: NOW, writer=writer) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "FAILED" and report["snapshot_persisted"] is True
    assert main(arguments(tmp_path, "recovered.json"), client=client, clock=lambda: NOW) == 0
    assert len(client.calls) == 1


@pytest.mark.parametrize("existing", ["corrupt", '{"schema_version":1,"schema_version":1}', "NaN"])
def test_corrupt_existing_snapshot_never_overwritten_or_refetched(tmp_path, existing):
    path = tmp_path / "snapshot.json"
    path.write_text(existing, encoding="utf-8")
    client = Client()
    assert main(arguments(tmp_path), client=client, clock=lambda: NOW) == 1
    assert not client.calls and path.read_text() == existing
    assert json.loads((tmp_path / "report.json").read_text())["failure_category"] == "EXISTING_SNAPSHOT_INVALID"


def test_request_mismatch_does_not_reuse_snapshot(tmp_path):
    write_json_atomic(tmp_path / "snapshot.json", snapshot().to_dict())
    args = arguments(tmp_path)
    args[1] = "MSFT"
    client = Client()
    assert main(args, client=client, clock=lambda: NOW) == 1
    assert not client.calls


@pytest.mark.parametrize("case", ["alias", "cache", "existing_report", "lock", "future", "symbol"])
def test_preflight_blocks_provider(tmp_path, case):
    args = arguments(tmp_path)
    if case == "alias":
        args[-1] = args[-3]
    elif case == "cache":
        args += ["--cache-directory", str(tmp_path)]
    elif case == "existing_report":
        (tmp_path / "report.json").write_text("original")
    elif case == "lock":
        (tmp_path / "snapshot.json.lock").write_text("other process")
    elif case == "future":
        args[5] = "2027-09-02"
    else:
        args[1] = "../../secret"
    client = Client()
    assert main(args, client=client, clock=lambda: NOW) == 1
    assert not client.calls
    if case == "lock":
        assert (tmp_path / "snapshot.json.lock").read_text() == "other process"
    if case == "existing_report":
        assert (tmp_path / "report.json").read_text() == "original"


def test_new_refresh_snapshot_retains_old_evidence_and_exposes_revision(tmp_path):
    client = Client()
    assert main(arguments(tmp_path), client=client, clock=lambda: NOW) == 0
    old = (tmp_path / "snapshot.json").read_bytes()
    client.frame["Dividends"] = [0.0, 0.21, 0.0]
    args = arguments(tmp_path, "refresh-report.json")
    args[-3] = str(tmp_path / "refresh-snapshot.json")
    assert main(args, client=client, clock=lambda: NOW) == 0
    assert len(client.calls) == 2
    refreshed, _ = load_snapshot(tmp_path / "refresh-snapshot.json")
    original, _ = load_snapshot(tmp_path / "snapshot.json")
    assert refreshed.to_dict()["content_sha256"] != original.to_dict()["content_sha256"]
    assert (tmp_path / "snapshot.json").read_bytes() == old


def test_content_checksum_ignores_acquisition_time_but_snapshot_preserves_it():
    first = snapshot().to_dict()
    later = deepcopy(first)
    later["fetched_at_utc"] = "2026-10-06T00:00:00+00:00"
    second = CorporateActionSnapshot.from_dict(later)
    assert second.to_dict()["content_sha256"] == first["content_sha256"]
