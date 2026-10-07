from dataclasses import replace
from functools import partial
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
import pytest

from investment_terminal.cli.portfolio_split_collect import main, plan_candidates
from investment_terminal.cli.yahoo_corporate_actions import main as collect
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_position_reconstruction import WORLD, EM, ledger, trade
from tests.test_split_adjustment import at, cli_case


class Client:
    def __init__(self, splits=2, currency="EUR", error=False):
        self.calls = []
        self.splits, self.currency, self.error = splits, currency, error

    def get_action_history(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise RuntimeError("SECRET provider detail")
        frame = pd.DataFrame({"Dividends": [0.0, 0.0], "Stock Splits": [0.0, self.splits]},
                             index=pd.DatetimeIndex([at(1), at(5)]))
        return frame, {"symbol": kwargs["symbol"], "currency": self.currency,
                       "exchangeTimezoneName": "UTC", "instrumentType": "ETF"}


def case(tmp_path, name="report.json"):
    root = tmp_path / "data"
    root.mkdir(exist_ok=True)
    _, source, _, _, _ = cli_case(root)
    directory, report = root / "collected", tmp_path / "reports" / name
    args = ["--transactions-directory", str(root), "--snapshot-directory", str(directory),
            "--report-output", str(report), "--cache-directory", str(tmp_path / "cache"),
            "--end", "2026-08-20"]
    return args, source, directory, report


def run(args, client=None, **kwargs):
    return main(args, collector=partial(collect, client=client or Client()),
                clock=lambda: at(22), **kwargs)


def test_collection_and_offline_repeat_preserve_source_and_redact(tmp_path, capsys):
    args, source, directory, report = case(tmp_path)
    original = source.read_bytes()
    client = Client()
    assert run(args, client) == 0
    evidence = json.loads(report.read_bytes())
    assert evidence["status"] == "COLLECTED"
    assert evidence["counts"]["SPLITS_OBSERVED"] == 1
    private = next(directory.glob("*-selection.json"))
    payload = json.loads(private.read_bytes())
    assert evidence["private_output_sha256"] == sha256(private.read_bytes()).hexdigest()
    assert payload["items"][0]["instrument"]["isin"] == WORLD.isin
    assert payload["identity_assurance"] == "UNVERIFIED_PROVIDER_MAPPING"
    saved = {p.name: p.read_bytes() for p in directory.glob("*-actions.json")}
    args[args.index("--report-output") + 1] = str(report.with_name("repeat.json"))
    assert run(args, client) == 0
    assert len(client.calls) == 1
    assert saved == {p.name: p.read_bytes() for p in directory.glob("*-actions.json")}
    assert source.read_bytes() == original
    assert not list(tmp_path.rglob("*.lock"))
    output = capsys.readouterr()
    for value in ("WORLD", WORLD.isin, "SECRET", "100.0", str(source)):
        assert value not in report.read_text() + output.out + output.err


@pytest.mark.parametrize("client,status,count", [
    (Client(splits=0), "COLLECTED", "NO_SPLITS_OBSERVED"),
    (Client(currency="USD"), "COMPLETE_WITH_BLOCKERS", "BLOCKED"),
    (Client(error=True), "STOPPED", "FAILED"),
])
def test_zero_mismatch_and_failure_are_distinct(tmp_path, client, status, count):
    args, _, _, report = case(tmp_path)
    assert run(args, client) == (1 if status == "STOPPED" else 0)
    data = json.loads(report.read_bytes())
    assert data["status"] == status and data["counts"][count] == 1
    assert data["adjustment_performed"] is False
    if count == "FAILED": assert data["category_counts"] == {"PROVIDER_REQUEST": 1}
    if count == "BLOCKED": assert data["category_counts"] == {"METADATA_MISMATCH": 1}


@pytest.mark.parametrize("mutation,category", [
    ("changed", "IDENTITY_CHANGED"), ("type", "UNSUPPORTED_TYPE"),
    ("symbol", "UNSUPPORTED_SYMBOL"), ("window", "TRADE_WINDOW"),
    ("ambiguous", "AMBIGUOUS_SYMBOL"),
])
def test_planning_blockers_prevent_guessed_requests(mutation, category):
    instrument = WORLD
    values = [trade("b", "BUY", 2, 1, 100)]
    if mutation == "changed": values.append(trade("b2", "BUY", 3, 1, 100, instrument=replace(WORLD, name="Changed")))
    if mutation == "type": instrument = replace(WORLD, instrument_type="BOND")
    if mutation == "symbol": instrument = replace(WORLD, symbol="WORLD/OTHER")
    if mutation in ("type", "symbol"): values = [trade("b", "BUY", 2, 1, 100, instrument=instrument)]
    if mutation == "window": values = [trade("b", "BUY", 20, 1, 100)]
    if mutation == "ambiguous": values.append(trade("b2", "BUY", 3, 1, 100, instrument=replace(EM, symbol="WORLD")))
    items = plan_candidates(ledger(*values), at(20), 10)
    assert all(item["status"] == "BLOCKED" and item["category"] == category for item in items)


def test_budget_not_silent_truncation_and_deterministic_order():
    source = ledger(trade("b", "BUY", 2, 1, 100), trade("em", "BUY", 3, 1, 100, instrument=EM))
    with pytest.raises(ValueError):
        plan_candidates(source, at(20), 1)
    items = plan_candidates(source, at(20), 2)
    assert [i["instrument"]["instrument_key"] for i in items] == sorted([WORLD.instrument_key, EM.instrument_key])


@pytest.mark.parametrize("failure", ["ambiguous_csv", "no_csv", "large_csv", "budget", "future", "existing_report", "lock", "overlap", "bad_age"])
def test_preflight_never_contacts_provider(tmp_path, failure):
    args, source, directory, report = case(tmp_path)
    client = Client()
    if failure == "ambiguous_csv": source.with_name("copy.csv").write_bytes(source.read_bytes())
    if failure == "no_csv": source.unlink()
    if failure == "large_csv": source.write_bytes(b"x" * 4_000_001)
    if failure == "budget": args += ["--max-instruments", "0"]
    if failure == "future": args[args.index("--end") + 1] = "2026-08-30"
    if failure == "existing_report":
        report.parent.mkdir()
        report.write_bytes(b"KEEP")
    if failure == "lock":
        directory.mkdir()
        (directory / ".portfolio-actions.lock").write_bytes(b"KEEP")
    if failure == "overlap": args[args.index("--report-output") + 1] = str(source.parent / "report.json")
    if failure == "bad_age": args += ["--maximum-age-days", "0"]
    assert run(args, client) == 1 and not client.calls
    if failure == "existing_report": assert report.read_bytes() == b"KEEP"
    if failure == "lock": assert (directory / ".portfolio-actions.lock").read_bytes() == b"KEEP"


@pytest.mark.parametrize("failure", ["private_write", "report_write", "private_readback", "report_readback", "source_change", "snapshot_change"])
def test_output_failure_never_claims_completion(tmp_path, capsys, failure):
    args, source, directory, report = case(tmp_path)

    def writer(path, payload):
        if (failure == "private_write" and path != report) or (failure == "report_write" and path == report):
            raise OSError("SECRET failure")
        write_json_atomic(path, payload)
        if failure == "private_readback" and path != report: path.write_bytes(b"{}")
        if failure == "report_readback" and path == report: path.write_bytes(b"{}")
        if failure == "source_change": source.write_bytes(source.read_bytes() + b"\n")
        if failure == "snapshot_change" and path == report: next(directory.glob("*-actions.json")).write_bytes(b"{}")

    assert run(args, writer=writer) == 1
    output = capsys.readouterr()
    assert "RESULT:" not in output.out and "SECRET" not in output.err
    assert list(directory.glob("*-actions.json"))


def test_corrupt_existing_snapshot_no_network_or_overwrite(tmp_path):
    args, _, directory, report = case(tmp_path)
    assert run(args) == 0
    snapshot = next(directory.glob("*-actions.json"))
    snapshot.write_bytes(b"CORRUPT")
    args[args.index("--report-output") + 1] = str(report.with_name("retry.json"))
    client = Client()
    assert run(args, client) == 1 and not client.calls
    assert snapshot.read_bytes() == b"CORRUPT"


def test_failure_stops_remaining_requests(tmp_path):
    args, source, directory, report = case(tmp_path)
    text = source.read_text()
    row = text.splitlines()[1].replace("b,BUY", "b2,BUY").replace("WORLD", "EM").replace(WORLD.isin, EM.isin)
    source.write_text(text + row + "\n")
    client = Client(error=True)
    assert run(args, client) == 1 and len(client.calls) == 1
    evidence = json.loads(report.read_bytes())
    assert evidence["counts"]["FAILED"] == evidence["counts"]["PENDING"] == 1


def test_existing_stale_evidence_is_blocked_without_refetch(tmp_path):
    args, _, _, report = case(tmp_path)
    assert run(args) == 0
    args[args.index("--report-output") + 1] = str(report.with_name("stale.json"))
    client = Client()
    assert main(args, collector=partial(collect, client=client), clock=lambda: at(30)) == 0
    evidence = json.loads(report.with_name("stale.json").read_bytes())
    assert evidence["status"] == "COMPLETE_WITH_BLOCKERS"
    assert evidence["category_counts"] == {"SNAPSHOT_AGE": 1}
    assert not client.calls


def test_private_write_failure_recovers_collection_offline_with_new_report(tmp_path):
    args, _, _, report = case(tmp_path)
    client = Client()

    def fail(path, payload):
        raise OSError("write failed")

    assert run(args, client, writer=fail) == 1
    args[args.index("--report-output") + 1] = str(report.with_name("recover.json"))
    assert run(args, client) == 0
    assert len(client.calls) == 1


def test_duplicate_transaction_ids_fail_before_provider(tmp_path):
    args, source, _, _ = case(tmp_path)
    text = source.read_text()
    source.write_text(text + text.splitlines()[1] + "\n")
    client = Client()
    assert run(args, client) == 1 and not client.calls


def test_stage_success_without_matching_evidence_is_rejected(tmp_path, capsys):
    args, _, _, _ = case(tmp_path)

    def forged(args, **kwargs):
        assert collect(args, client=Client(), **kwargs) == 0
        path = Path(args[args.index("--report-output") + 1])
        payload = json.loads(path.read_bytes())
        payload["snapshot_sha256"] = "0" * 64
        write_json_atomic(path, payload)
        return 0

    assert main(args, collector=forged, clock=lambda: at(22)) == 1
    assert "RESULT:" not in capsys.readouterr().out
