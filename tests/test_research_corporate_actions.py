"""Schema-2 research context integration and backward-compatible verification."""

from copy import deepcopy
from datetime import timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from investment_terminal.cli.instrument_research_export import main as export_main
from investment_terminal.cli.instrument_research_run import main as run_main
from investment_terminal.cli.instrument_research_verify import main as verify_main
from investment_terminal.market.corporate_actions import (
    CorporateAction, CorporateActionSnapshot, canonical_bytes,
)
from investment_terminal.operations.instrument_research_verification import verify_instrument_research_export
from investment_terminal.operations.research_corporate_actions import (
    ResearchActionPolicy, attach_action_context, project_action_context,
)
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_instrument_research_export import _cli_args
from tests.test_instrument_research_run import _setup
from tests.test_weekly_candle_refresh import END


START = END - timedelta(days=30)
FETCHED = END + timedelta(hours=6)
AS_OF = END + timedelta(days=1)


def _snapshot(symbol, **changes):
    first = END - timedelta(days=2)
    last = END - timedelta(days=1)
    arguments = dict(
        symbol=symbol, start=START, end=END, fetched_at=FETCHED,
        adapter_version="1.6.0", quote_currency="USD", exchange_timezone="UTC",
        instrument_type="EQUITY", row_count=2, first_row_at=first, last_row_at=last,
        capital_gains_present=False,
        events=(CorporateAction(first, first.date().isoformat(), "DIVIDEND", 0.4),
                CorporateAction(last, last.date().isoformat(), "SPLIT", 2.0)),
    )
    arguments.update(changes)
    return CorporateActionSnapshot(**arguments)


def _action_args(tmp_path, symbol, *, as_of=AS_OF, **changes):
    path = tmp_path / "actions.json"
    write_json_atomic(path, _snapshot(symbol, **changes).to_dict())
    return ["--schema-version", "2", "--actions-as-of", as_of.isoformat(),
            "--actions-maximum-age-days", "7", "--actions-snapshot", str(path),
            "--actions-sha256", sha256(path.read_bytes()).hexdigest()]


def _option(args, flag, value):
    args = args.copy()
    args[args.index(flag) + 1] = str(value)
    return args


def _read_pair(private, report):
    return json.loads(private.read_bytes()), json.loads(report.read_bytes())


def _schema2_pair(tmp_path, **changes):
    args, private, report, _ = _cli_args(tmp_path)
    symbol = args[args.index("--symbol") + 1]
    args += _action_args(tmp_path, symbol, **changes)
    assert export_main(args) == 0
    return args, private, report, symbol


def test_available_context_is_bound_read_only_and_verifiable_without_provider(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No provider call allowed")

    monkeypatch.setattr("yfinance.Ticker", forbidden)
    args, private_path, report_path, _ = _cli_args(tmp_path)
    symbol = args[args.index("--symbol") + 1]
    args += _action_args(tmp_path, symbol)
    database = tmp_path / "candles.db"
    actions_path = tmp_path / "actions.json"
    original_db, original_actions = database.read_bytes(), actions_path.read_bytes()
    assert export_main(args) == 0
    private, report = _read_pair(private_path, report_path)
    assert private["schema_version"] == report["schema_version"] == 2
    context = private["corporate_actions"]
    summary = report["corporate_actions"]
    assert summary["availability"] == "AVAILABLE"
    assert summary["event_counts"] == {"CAPITAL_GAIN": 0, "DIVIDEND": 1, "SPLIT": 1}
    assert summary["capital_gains_field_present"] is False
    assert summary["source_snapshot_sha256"] == sha256(original_actions).hexdigest()
    assert summary["snapshot_document_sha256"] == sha256(canonical_bytes(context["snapshot"])).hexdigest()
    assert "snapshot" not in summary
    assert context["snapshot"]["content"]["symbol"] == symbol
    assert private["price_basis"] == "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT"
    assert summary["action_completeness"] == "UNKNOWN"
    assert database.read_bytes() == original_db and actions_path.read_bytes() == original_actions
    verify_instrument_research_export(private, report, expected_symbol=symbol)
    for secret in (symbol, "USD", "value", "timestamp_utc", str(tmp_path)):
        assert secret not in json.dumps(summary)


@pytest.mark.parametrize("offset,expected", [
    (timedelta(days=7), "AVAILABLE"),
    (timedelta(days=7, microseconds=1), "STALE"),
    (timedelta(days=30), "STALE"),
])
def test_freshness_is_explicit_and_boundary_is_inclusive(tmp_path, offset, expected):
    _, private_path, report_path, symbol = _schema2_pair(tmp_path, as_of=FETCHED + offset)
    private, report = _read_pair(private_path, report_path)
    assert private["status"] == report["status"] == "COMPLETE"
    assert report["corporate_actions"]["availability"] == expected
    assert private["corporate_actions"]["snapshot"] is not None
    verify_instrument_research_export(private, report, expected_symbol=symbol)


def test_missing_actions_are_not_zero_events_and_do_not_block_raw_export(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)
    args += ["--schema-version", "2", "--actions-as-of", AS_OF.isoformat(),
             "--actions-maximum-age-days", "7"]
    assert export_main(args) == 0
    private, report = _read_pair(private_path, report_path)
    summary = report["corporate_actions"]
    assert summary["availability"] == "MISSING"
    assert summary["event_counts"] is None and summary["source_snapshot_sha256"] is None
    assert summary["capital_gains_field_present"] is None
    assert private["corporate_actions"]["snapshot"] is None
    verify_instrument_research_export(private, report, expected_symbol=private["symbol"])


def test_available_zero_events_differ_from_missing(tmp_path):
    _, private_path, report_path, _ = _schema2_pair(tmp_path, events=())
    _, report = _read_pair(private_path, report_path)
    assert report["corporate_actions"]["availability"] == "AVAILABLE"
    assert set(report["corporate_actions"]["event_counts"].values()) == {0}
    assert report["corporate_actions"]["action_completeness"] == "UNKNOWN"


def test_schema1_default_and_explicit_output_bytes_remain_identical(tmp_path):
    args, private1, report1, _ = _cli_args(tmp_path)
    assert export_main(args) == 0
    private2, report2 = tmp_path / "private2.json", tmp_path / "report2.json"
    args = _option(_option(args, "--private-output", private2), "--report-output", report2)
    assert export_main([*args, "--schema-version", "1"]) == 0
    assert private1.read_bytes() == private2.read_bytes()
    assert report1.read_bytes() == report2.read_bytes()
    assert "corporate_actions" not in json.loads(report2.read_bytes())


def test_context_attachment_never_mutates_legacy_pair_or_shares_nested_state(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)
    assert export_main(args) == 0
    private, report = _read_pair(private_path, report_path)
    original = deepcopy((private, report))
    upgraded, redacted = attach_action_context(
        private, report, policy=ResearchActionPolicy(AS_OF, 7),
        snapshot=_snapshot(private["symbol"]), source_sha256="a" * 64,
    )
    upgraded["candles"][0]["close_price"] = 1
    upgraded["corporate_actions"]["limitations"].append("private")
    assert (private, report) == original
    assert "private" not in redacted["corporate_actions"]["limitations"]


@pytest.mark.parametrize("change", [
    "checksum", "missing_file", "corrupt_file", "different_symbol", "currency",
    "short_window", "long_window", "future_snapshot", "future_window", "duplicate_key",
])
def test_supplied_invalid_evidence_fails_not_missing_and_preserves_sources(tmp_path, change):
    args, private, report, _ = _cli_args(tmp_path)
    symbol = args[args.index("--symbol") + 1]
    changes = {}
    if change == "currency":
        changes["quote_currency"] = "EUR"
    elif change == "short_window":
        changes["start"] = START + timedelta(days=1)
    elif change == "long_window":
        changes["start"] = START - timedelta(days=1)
    elif change == "future_snapshot":
        changes["fetched_at"] = AS_OF + timedelta(microseconds=1)
    action_args = _action_args(tmp_path, "WRONG" if change == "different_symbol" else symbol, **changes)
    path = tmp_path / "actions.json"
    if change == "checksum":
        action_args[-1] = "b" * 64
    elif change == "missing_file":
        action_args = _option(action_args, "--actions-snapshot", tmp_path / "absent.json")
    elif change == "corrupt_file":
        path.write_text("{", encoding="utf-8")
        action_args[-1] = sha256(path.read_bytes()).hexdigest()
    elif change == "duplicate_key":
        text = path.read_text(encoding="utf-8").replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1)
        path.write_text(text, encoding="utf-8")
        action_args[-1] = sha256(path.read_bytes()).hexdigest()
    elif change == "future_window":
        action_args = _option(action_args, "--actions-as-of", START.isoformat())
    original = path.read_bytes()
    database_bytes = (tmp_path / "candles.db").read_bytes()
    assert export_main([*args, *action_args]) == 1
    assert not private.exists()
    failure = json.loads(report.read_bytes())
    assert failure["schema_version"] == 2 and failure["status"] == "FAILED"
    assert failure["corporate_actions"] is None
    assert symbol not in json.dumps(failure)
    assert path.read_bytes() == original
    assert (tmp_path / "candles.db").read_bytes() == database_bytes


def test_checksum_failure_occurs_before_database_open(tmp_path, monkeypatch):
    args, private, report, _ = _cli_args(tmp_path)
    action_args = _action_args(tmp_path, args[args.index("--symbol") + 1])
    action_args[-1] = "0" * 64
    calls = []

    def database(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Must fail before database open")

    monkeypatch.setattr("investment_terminal.cli.instrument_research_export.sqlite3.connect", database)
    assert export_main([*args, *action_args]) == 1
    assert not calls and not private.exists()


@pytest.mark.parametrize("extra", [
    ["--schema-version", "2"],
    ["--actions-as-of", AS_OF.isoformat()],
    ["--schema-version", "2", "--actions-as-of", AS_OF.isoformat(), "--actions-maximum-age-days", "0"],
    ["--schema-version", "2", "--actions-as-of", AS_OF.isoformat(), "--actions-maximum-age-days", "366"],
    ["--schema-version", "2", "--actions-as-of", "2026-09-23", "--actions-maximum-age-days", "7"],
    ["--schema-version", "2", "--actions-as-of", AS_OF.isoformat(), "--actions-maximum-age-days", "7", "--actions-sha256", "0" * 64],
])
def test_incomplete_or_implicit_policy_is_rejected_before_output(tmp_path, extra):
    args, private, report, _ = _cli_args(tmp_path)
    with pytest.raises(SystemExit, match="action options"):
        export_main([*args, *extra])
    assert not private.exists() and not report.exists()


@pytest.mark.parametrize("change", [
    "count", "availability", "unit", "currency", "event", "fetched_at", "snapshot_hash",
    "policy", "extra", "schema", "completeness", "price_basis", "drop_snapshot", "count_bool",
])
def test_verifier_rejects_changed_private_or_report_context(tmp_path, change):
    _, private_path, report_path, symbol = _schema2_pair(tmp_path)
    private, report = _read_pair(private_path, report_path)
    context, summary = private["corporate_actions"], report["corporate_actions"]
    if change == "count":
        summary["event_counts"]["DIVIDEND"] += 1
    elif change == "count_bool":
        summary["event_counts"]["DIVIDEND"] = True
    elif change == "availability":
        context["availability"] = "MISSING"
    elif change in ("unit", "currency", "event"):
        event = context["snapshot"]["content"]["events"][0]
        event[{"unit": "unit", "currency": "currency", "event": "value"}[change]] = (
            "USD" if change in ("unit", "currency") else 1.0)
    elif change == "fetched_at":
        context["snapshot"]["fetched_at_utc"] = AS_OF.isoformat()
    elif change == "snapshot_hash":
        context["source_snapshot_sha256"] = "0" * 64
    elif change == "policy":
        summary["maximum_age_days"] = 8
    elif change == "extra":
        context["extra"] = "untrusted"
    elif change == "schema":
        report["schema_version"] = 1
    elif change == "completeness":
        summary["action_completeness"] = "COMPLETE"
    elif change == "price_basis":
        private["price_basis"] = report["price_basis"] = "ADJUSTED"
    elif change == "drop_snapshot":
        context["snapshot"] = None
    with pytest.raises(ValueError):
        verify_instrument_research_export(private, report, expected_symbol=symbol)


def test_recomputed_snapshot_content_hash_does_not_bypass_pinned_report(tmp_path):
    _, private_path, report_path, symbol = _schema2_pair(tmp_path)
    private, report = _read_pair(private_path, report_path)
    payload = private["corporate_actions"]["snapshot"]
    payload["content"]["events"][0]["value"] = 1.1
    payload["content_sha256"] = sha256(canonical_bytes(payload["content"])).hexdigest()
    with pytest.raises(ValueError, match="corporate-action"):
        verify_instrument_research_export(private, report, expected_symbol=symbol)


def test_profile_command_forwards_schema2_and_local_verifier_accepts(tmp_path, capsys):
    args, _, profile, private, report, _ = _setup(tmp_path)
    symbol = args[args.index("--symbol") + 1]
    action_args = _action_args(tmp_path, symbol)
    before = Path(profile["database"]).read_bytes()
    assert run_main([*args, *action_args]) == 0
    assert json.loads(report.read_bytes())["corporate_actions"]["availability"] == "AVAILABLE"
    checksum = sha256(report.read_bytes()).hexdigest()
    assert verify_main(["--private-export", str(private), "--report", str(report),
                        "--report-sha256", checksum, "--symbol", symbol]) == 0
    output = capsys.readouterr().out
    assert "VERIFIED:" in output and "SEND:" in output
    assert symbol not in output and str(private) not in output
    assert Path(profile["database"]).read_bytes() == before


def test_profile_command_rejects_snapshot_in_report_directory(tmp_path):
    args, _, _, private, report, _ = _setup(tmp_path)
    report.parent.mkdir()
    extra = _action_args(report.parent, args[args.index("--symbol") + 1])
    assert run_main([*args, *extra]) == 1
    assert not private.exists() and not report.exists()


@pytest.mark.parametrize("destination", ["private", "report"])
def test_schema2_write_failure_cleans_only_new_exports_not_action_input(tmp_path, destination):
    args, private, report, _ = _cli_args(tmp_path)
    args += _action_args(tmp_path, args[args.index("--symbol") + 1])
    original = (tmp_path / "actions.json").read_bytes()

    def writer(path, payload):
        write_json_atomic(path, payload)
        if payload["status"] == "COMPLETE" and path == (private if destination == "private" else report):
            raise OSError("private failure detail")

    assert export_main(args, writer=writer) == 1
    assert not private.exists()
    result = json.loads(report.read_bytes())
    assert result["schema_version"] == 2 and result["status"] == "FAILED"
    assert "private failure detail" not in str(result)
    assert (tmp_path / "actions.json").read_bytes() == original


def test_action_input_cannot_alias_output(tmp_path):
    args, private, report, _ = _cli_args(tmp_path)
    args += _action_args(tmp_path, args[args.index("--symbol") + 1])
    args = _option(args, "--private-output", tmp_path / "actions.json")
    original = (tmp_path / "actions.json").read_bytes()
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        export_main(args)
    assert not report.exists() and (tmp_path / "actions.json").read_bytes() == original


@pytest.mark.parametrize("value", [True, 0, 366, 1.5])
def test_policy_rejects_non_integer_or_unbounded_age(value):
    with pytest.raises(ValueError):
        ResearchActionPolicy(AS_OF, value)


def test_policy_rejects_non_utc_time_and_context_rejects_orphan_checksum():
    with pytest.raises(ValueError):
        ResearchActionPolicy(AS_OF.replace(tzinfo=timezone(timedelta(hours=1))), 7)
    with pytest.raises(ValueError):
        project_action_context(symbol="AAA", currency="USD", start=START, end=END,
                               policy=ResearchActionPolicy(AS_OF, 7), source_sha256="a" * 64)
