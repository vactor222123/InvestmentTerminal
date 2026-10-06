"""One-command research composition is generic, bounded and fail-closed."""

from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
import pytest

from investment_terminal.cli import instrument_research_collect as command
from investment_terminal.operations.yahoo_corporate_actions import load_snapshot
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_instrument_research_run import _setup, _replace
from tests.test_research_corporate_actions import AS_OF, END, _snapshot
from tests.test_yahoo_corporate_actions import Client


def case(tmp_path):
    base, profile_path, profile, _, _, projection = _setup(tmp_path)
    opts = dict(zip(base[::2], base[1::2]))
    args = [value for key in ("--profile", "--projection", "--projection-sha256",
                              "--symbol", "--history-start", "--end")
            for value in (key, opts[key])]
    args += ["--run-id", "check_001", "--actions-maximum-age-days", "7"]
    outputs = {
        "snapshot": tmp_path / "research_check_001_actions.json",
        "private": tmp_path / "research_check_001.json",
        "actions": tmp_path / "reports" / "research_check_001_actions.json",
        "report": tmp_path / "reports" / "research_check_001.json",
    }
    frame = pd.DataFrame({"Dividends": [0.5, 0.0], "Stock Splits": [0.0, 2.0]},
                         index=pd.DatetimeIndex([END - timedelta(days=2), END - timedelta(days=1)]))
    client = Client(frame=frame, meta={"symbol": opts["--symbol"], "currency": "USD",
                                    "exchangeTimezoneName": "UTC", "instrumentType": "EQUITY"})
    return args, profile_path, profile, projection, outputs, client


def read(path):
    return json.loads(path.read_bytes())


def test_new_collection_exports_and_verifies_generic_symbol_without_source_mutation(tmp_path, capsys):
    args, profile_path, profile, projection, out, client = case(tmp_path)
    sources = [profile_path, projection, Path(profile["database"]), Path(profile["manifest"])]
    originals = {p: p.read_bytes() for p in sources}
    assert command.main(args, client=client, clock=lambda: AS_OF) == 0
    assert len(client.calls) == 1
    private, report, actions = map(read, (out["private"], out["report"], out["actions"]))
    assert private["symbol"] == args[args.index("--symbol") + 1]
    assert report["schema_version"] == 2 and report["status"] == "COMPLETE"
    assert report["corporate_actions"]["availability"] == "AVAILABLE"
    assert report["corporate_actions"]["event_counts"] == {"DIVIDEND": 1, "SPLIT": 1, "CAPITAL_GAIN": 0}
    assert actions["reused_snapshot"] is False
    assert report["corporate_actions"]["source_snapshot_sha256"] == actions["snapshot_sha256"]
    assert all(path.read_bytes() == data for path, data in originals.items())
    assert not list(tmp_path.rglob("*.lock"))
    output = capsys.readouterr()
    assert "COMPLETE: corporate-action research run" in output.out
    assert "SQLite integrity: ok" in output.out
    assert private["symbol"] not in json.dumps(report)
    assert str(out["private"]) not in output.out and not output.err


def reuse(args, out, client, **changes):
    symbol = client.meta["symbol"]
    write_json_atomic(out["snapshot"], _snapshot(symbol, **changes).to_dict())
    return args + ["--actions-snapshot", str(out["snapshot"]),
                   "--actions-sha256", sha256(out["snapshot"].read_bytes()).hexdigest()]


def test_explicit_reuse_is_offline_and_preserves_exact_snapshot(tmp_path):
    args, _, _, _, out, client = case(tmp_path)
    args = reuse(args, out, client)
    original = out["snapshot"].read_bytes()
    client.error = AssertionError("No request allowed")
    assert command.main(args, client=client, clock=lambda: AS_OF) == 0
    assert not client.calls and out["snapshot"].read_bytes() == original
    assert read(out["actions"])["reused_snapshot"] is True


@pytest.mark.parametrize("change", [
    "checksum", "missing_projection", "symbol", "future", "non_midnight", "long_window",
    "run_id", "run_id_long", "age_zero", "age_large", "missing_profile",
    "incomplete_reuse", "bad_projection", "projection_in_reports", "projection_in_sources",
    "private_exists", "report_exists", "snapshot_exists", "action_report_exists",
    "weekly_lock", "export_lock", "action_lock", "checkpoint_invalid",
])
def test_preflight_failures_make_no_provider_request_and_preserve_inputs(tmp_path, change):
    args, profile_path, profile, projection, out, client = case(tmp_path)
    if change == "checksum":
        args = _replace(args, "--projection-sha256", "0" * 64)
    elif change == "missing_projection":
        projection.unlink()
    elif change == "symbol":
        args = _replace(args, "--symbol", "NOT_SELECTED")
    elif change == "future":
        args = _replace(args, "--end", (AS_OF + timedelta(days=1)).isoformat())
    elif change == "non_midnight":
        args = _replace(args, "--history-start", "2026-08-23T00:00:01+00:00")
    elif change == "long_window":
        args = _replace(args, "--history-start", "2000-01-01T00:00:00+00:00")
    elif change.startswith("run_id"):
        args = _replace(args, "--run-id", "../escape" if change == "run_id" else "a" * 49)
    elif change.startswith("age_"):
        args = _replace(args, "--actions-maximum-age-days", "0" if change == "age_zero" else "366")
    elif change == "missing_profile":
        profile_path.unlink()
    elif change == "incomplete_reuse":
        args += ["--actions-sha256", "0" * 64]
    elif change == "bad_projection":
        projection.write_bytes(b"{}")
        args = _replace(args, "--projection-sha256", sha256(projection.read_bytes()).hexdigest())
    elif change.startswith("projection_in_"):
        directory = Path(profile["report_directory"] if change.endswith("reports")
                         else profile["source_checkpoint_directory"])
        directory.mkdir(exist_ok=True)
        moved = directory / "projection.json"
        projection.replace(moved)
        args = _replace(args, "--projection", moved)
    elif change.endswith("_exists"):
        name = {"private_exists": "private", "report_exists": "report", "snapshot_exists": "snapshot",
                "action_report_exists": "actions"}[change]
        out[name].parent.mkdir(exist_ok=True)
        out[name].write_bytes(b"original")
    elif change.endswith("_lock"):
        target = (Path(profile["weekly_checkpoint_directory"]) / "weekly_candle_refresh.lock"
                  if change == "weekly_lock" else Path(str(out["private"] if change == "export_lock"
                                                          else out["snapshot"]) + ".lock"))
        target.write_bytes(b"other process")
    elif change == "checkpoint_invalid":
        next(Path(profile["weekly_checkpoint_directory"]).glob("*.json")).write_bytes(b"{}")
    originals = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert not client.calls
    assert all(path.read_bytes() == data for path, data in originals.items())


@pytest.mark.parametrize("change", ["corrupt", "checksum", "stale", "future", "currency", "symbol", "window"])
def test_reuse_never_silently_refetches_invalid_or_stale_evidence(tmp_path, change):
    args, _, _, _, out, client = case(tmp_path)
    changes = {}
    if change == "stale":
        changes["fetched_at"] = END
    elif change == "future":
        changes["fetched_at"] = AS_OF + timedelta(days=1)
    elif change == "currency":
        changes["quote_currency"] = "EUR"
    elif change == "symbol":
        changes["symbol"] = "OTHER"
    elif change == "window":
        changes["start"] = END - timedelta(days=29)
    # Avoid duplicating the explicit positional symbol in the fixture helper.
    if change == "symbol":
        client.meta["symbol"] = "OTHER"
        changes = {}
    args = reuse(args, out, client, **changes)
    if change == "stale":
        args = _replace(args, "--actions-maximum-age-days", "1")
    if change == "checksum":
        args[-1] = "0" * 64
    if change == "corrupt":
        out["snapshot"].write_bytes(b"{")
        args[-1] = sha256(b"{").hexdigest()
    original = out["snapshot"].read_bytes()
    now = AS_OF + timedelta(seconds=1) if change == "stale" else AS_OF
    assert command.main(args, client=client, clock=lambda: now) == 1
    assert not client.calls and out["snapshot"].read_bytes() == original
    assert not out["private"].exists() and not out["report"].exists()


def test_provider_failure_stops_export_with_durable_redacted_collection_failure(tmp_path, capsys):
    args, _, _, _, out, client = case(tmp_path)
    client.error = RuntimeError("SECRET input")
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert read(out["actions"])["status"] == "FAILED"
    assert not out["private"].exists() and not out["report"].exists()
    captured = capsys.readouterr()
    assert "ACTION_COLLECTION" in captured.err and "SECRET" not in captured.out + captured.err
    assert not list(tmp_path.rglob("*.lock"))


def test_export_failure_preserves_actions_for_explicit_offline_recovery(tmp_path, monkeypatch):
    args, _, _, _, out, client = case(tmp_path)
    original_export = command.export_main
    monkeypatch.setattr(command, "export_main", lambda _: 1)
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    stored = out["snapshot"].read_bytes()
    monkeypatch.setattr(command, "export_main", original_export)
    recovered = _replace(args, "--run-id", "recovered") + [
        "--actions-snapshot", str(out["snapshot"]), "--actions-sha256", sha256(stored).hexdigest(),
    ]
    assert command.main(recovered, client=client, clock=lambda: AS_OF) == 0
    assert len(client.calls) == 1 and out["snapshot"].read_bytes() == stored


@pytest.mark.parametrize("failure", ["verify", "integrity", "source_change", "snapshot_change", "action_report_change"])
def test_late_failures_never_claim_overall_completion(tmp_path, monkeypatch, capsys, failure):
    args, _, profile, _, out, client = case(tmp_path)
    if failure == "verify":
        monkeypatch.setattr(command, "verify_main", lambda _: 1)
    elif failure in ("source_change", "snapshot_change", "action_report_change"):
        def changed(_):
            path = (Path(profile["manifest"]) if failure == "source_change" else
                    out["snapshot"] if failure == "snapshot_change" else out["actions"])
            path.write_bytes(path.read_bytes() + b"\n")
        monkeypatch.setattr(command, "_integrity", changed)
    else:
        def broken(_):
            raise OSError("SECRET database")
        monkeypatch.setattr(command, "_integrity", broken)
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert out["snapshot"].is_file() and out["private"].is_file()
    captured = capsys.readouterr()
    assert "COMPLETE: corporate-action research run" not in captured.out
    assert "SQLite integrity: ok" not in captured.out
    assert "SECRET" not in captured.err
    assert not list(tmp_path.rglob("*.lock"))


def test_integrity_checks_every_row_not_only_first_ok(tmp_path, monkeypatch):
    class FakeConnection:
        def execute(self, sql):
            return self

        def fetchall(self):
            return [("ok",), ("corrupt page",)]

        def close(self):
            pass

    monkeypatch.setattr(command.sqlite3, "connect", lambda *a, **kw: FakeConnection())
    with pytest.raises(ValueError, match="integrity"):
        command._integrity(tmp_path / "database.db")


def test_report_write_failure_keeps_snapshot_and_no_export(tmp_path, monkeypatch):
    from investment_terminal.cli.yahoo_corporate_actions import main as collector
    args, _, _, _, out, client = case(tmp_path)

    def writer(path, value):
        if path == out["actions"]:
            raise OSError("SECRET write error")
        write_json_atomic(path, value)

    monkeypatch.setattr(command, "collect_main", lambda argv, **kw: collector(argv, writer=writer, **kw))
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    load_snapshot(out["snapshot"])
    assert not out["actions"].exists() and not out["private"].exists()


def test_exact_run_repeat_refuses_overwrite_and_network(tmp_path):
    args, _, _, _, out, client = case(tmp_path)
    assert command.main(args, client=client, clock=lambda: AS_OF) == 0
    originals = {p: p.read_bytes() for p in out.values()}
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert len(client.calls) == 1
    assert all(p.read_bytes() == data for p, data in originals.items())


@pytest.mark.parametrize("destination", ["private", "report"])
def test_actual_export_write_failure_preserves_snapshot_and_failed_report(tmp_path, monkeypatch, destination):
    from investment_terminal.cli import instrument_research_run as runner
    from investment_terminal.cli.instrument_research_export import main as exporter
    args, _, _, _, out, client = case(tmp_path)

    def writer(path, payload):
        write_json_atomic(path, payload)
        if path == out[destination] and payload["status"] == "COMPLETE":
            raise OSError("Post-write failure")

    monkeypatch.setattr(runner, "export_main", lambda argv: exporter(argv, writer=writer))
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert read(out["actions"])["status"] == "STORED"
    load_snapshot(out["snapshot"])
    assert not out["private"].exists()
    assert read(out["report"])["status"] == "FAILED"
    assert not list(tmp_path.rglob("*.lock"))


def test_source_change_during_collection_stops_before_export(tmp_path):
    args, profile_path, _, _, out, client = case(tmp_path)
    original_request = client.get_action_history

    def mutate(**kwargs):
        profile_path.write_bytes(profile_path.read_bytes() + b"\n")
        return original_request(**kwargs)

    client.get_action_history = mutate
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert out["snapshot"].exists() and not out["private"].exists()


def test_wrong_provider_currency_is_stored_but_never_exported(tmp_path):
    args, _, _, _, out, client = case(tmp_path)
    client.meta["currency"] = "EUR"
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
    assert read(out["actions"])["status"] == "STORED"
    assert not out["private"].exists() and not out["report"].exists()


def test_independent_verifier_rejects_export_tampering(tmp_path, monkeypatch):
    args, _, _, _, out, client = case(tmp_path)
    original_export = command.export_main

    def tamper(argv):
        result = original_export(argv)
        payload = read(out["private"])
        payload["corporate_actions"]["event_counts"]["DIVIDEND"] += 1
        write_json_atomic(out["private"], payload)
        return result

    monkeypatch.setattr(command, "export_main", tamper)
    assert command.main(args, client=client, clock=lambda: AS_OF) == 1
