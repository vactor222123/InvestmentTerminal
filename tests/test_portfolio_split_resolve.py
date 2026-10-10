import csv
from functools import partial
from hashlib import sha256
import io
import json

import pytest
from yfinance.exceptions import YFRateLimitError, YFTzMissingError

from investment_terminal.cli.portfolio_split_collect import main as batch_main
from investment_terminal.cli.portfolio_split_diagnose import main as diagnose
from investment_terminal.cli.portfolio_split_resolve import main, SearchProbe
from investment_terminal.cli.yahoo_corporate_actions import main as collect
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_portfolio_split_collect import Client, case
from tests.test_position_reconstruction import WORLD
from tests.test_split_adjustment import at


class Search:
    def __init__(self, rows=None):
        self.rows = [{"symbol": "WORLD.DE", "quoteType": "ETF", "currency": "EUR", "exchange": "GER"}] if rows is None else rows
        self.calls = []

    def search_isin(self, isin):
        self.calls.append(isin)
        if isinstance(self.rows, Exception): raise self.rows
        return self.rows


def setup_case(tmp_path, ticker="WORLD.DE", missing_isin=False):
    args, source, directory, original = case(tmp_path)
    rows = list(csv.DictReader(io.StringIO(source.read_text())))
    rows[0]["exchange_ticker"] = ticker
    if missing_isin:
        rows[0]["isin"], rows[0]["instrument_type"] = "", "STOCK"
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    source.write_text(stream.getvalue())
    assert batch_main(args, collector=partial(collect, client=Client(error=True)), clock=lambda: at(22)) == 1

    class Missing:
        def get_action_history(self, **kwargs): raise YFTzMissingError("SECRET")

    diagnostic = original.with_name("diagnostic.json")
    diag = ["--collection-report", str(original), "--collection-report-sha256", sha256(original.read_bytes()).hexdigest(),
            "--snapshot-directory", str(directory), "--cache-directory", str(tmp_path / "cache"),
            "--report-output", str(diagnostic)]
    assert diagnose(diag, client_factory=Missing, clock=lambda: at(22)) == 1
    output = original.with_name("resolution.json")
    args = ["--diagnostic-report", str(diagnostic), "--diagnostic-report-sha256", sha256(diagnostic.read_bytes()).hexdigest(),
            "--collection-report", str(original), "--snapshot-directory", str(directory),
            "--cache-directory", str(tmp_path / "cache"), "--report-output", str(output)]
    return args, source, directory, diagnostic, output


def run(args, search=None, actions=None, **kwargs):
    search = search or Search()
    actions = actions or Client()
    return main(args, search_factory=lambda: search, action_factory=lambda: actions, clock=lambda: at(22), **kwargs)


def test_exact_existing_ticker_from_isin_search_collects_without_source_mutation(tmp_path, capsys):
    args, source, directory, diagnostic, output = setup_case(tmp_path)
    capsys.readouterr()
    prior = {p: p.read_bytes() for p in [source, diagnostic, *directory.glob("*.json")]}
    search, actions = Search(), Client()
    assert run(args, search, actions) == 0
    assert search.calls == [WORLD.isin]
    assert len(actions.calls) == 1 and actions.calls[0]["symbol"] == "WORLD.DE"
    result = json.loads(output.read_bytes())
    assert result["status"] == "RESOLVED_CANDIDATE" and result["provider_symbol_changed"] is True
    assert result["action_invocation_count"] == result["search_invocation_count"] == 1
    assert result["identity_assurance"] == "UNVERIFIED_BROKER_MAPPING"
    private = next(directory.glob("*-resolution.json"))
    snapshot = next(directory.glob("*-resolved-actions.json"))
    assert sha256(private.read_bytes()).hexdigest() == result["private_output_sha256"]
    assert sha256(snapshot.read_bytes()).hexdigest() == result["snapshot_sha256"]
    assert all(p.read_bytes() == data for p, data in prior.items())
    captured = capsys.readouterr()
    for value in ("SECRET", "WORLD", WORLD.isin, str(source)):
        assert value not in output.read_text() + captured.out + captured.err
    assert run(args, search, actions) == 1 and len(search.calls) == len(actions.calls) == 1


@pytest.mark.parametrize("change,category", [
    ("empty", "NO_SEARCH_CANDIDATES"), ("missing_ticker", "MISSING_EXISTING_TICKER"),
    ("no_match", "EXISTING_TICKER_NOT_FOUND"), ("ambiguous", "AMBIGUOUS_EXISTING_TICKER"),
    ("type", "QUOTE_TYPE_MISMATCH"), ("currency", "SEARCH_CURRENCY_MISMATCH"),
    ("malformed", "SEARCH_FAILED"), ("too_many", "SEARCH_FAILED"),
    ("rate", "SEARCH_FAILED"), ("missing_isin", "MISSING_ISIN"),
])
def test_blockers_never_guess_or_request_action_history(tmp_path, change, category):
    args, _, _, _, output = setup_case(tmp_path, ticker="" if change == "missing_ticker" else "WORLD.DE", missing_isin=change == "missing_isin")
    search, actions = Search(), Client()
    if change == "empty": search.rows = []
    if change == "no_match": search.rows[0]["symbol"] = "OTHER.DE"
    if change == "ambiguous": search.rows.append({**search.rows[0], "exchange": "OTHER"})
    if change == "type": search.rows[0]["quoteType"] = "EQUITY"
    if change == "currency": search.rows[0]["currency"] = "USD"
    if change == "malformed": search.rows = [{}]
    if change == "too_many": search.rows *= 26
    if change == "rate": search.rows = YFRateLimitError()
    assert run(args, search, actions) == 1
    result = json.loads(output.read_bytes())
    assert result["failure_category"] == category
    assert not actions.calls and len(search.calls) == (0 if change == "missing_isin" else 1)
    if change == "rate": assert result["search_failure_category"] == "RATE_LIMIT"
    if change == "malformed": assert result["candidate_count"] is None


@pytest.mark.parametrize("currency", ["USD", "GBp"])
def test_action_currency_is_checked_independently_of_search_normalization(tmp_path, currency):
    args, _, directory, _, output = setup_case(tmp_path)
    assert run(args, actions=Client(currency=currency)) == 1
    result = json.loads(output.read_bytes())
    assert result["status"] == "BLOCKED" and result["failure_category"] == "ACTION_METADATA_MISMATCH"
    assert result["snapshot_sha256"] and list(directory.glob("*-resolved-actions.json"))


def test_missing_search_currency_is_not_invented_and_action_metadata_is_required(tmp_path):
    args, _, _, _, output = setup_case(tmp_path)
    search = Search()
    search.rows[0].pop("currency")
    assert run(args, search=search) == 0
    assert json.loads(output.read_bytes())["status"] == "RESOLVED_CANDIDATE"


def test_typed_action_failure_is_preserved_without_retry(tmp_path):
    args, _, _, _, output = setup_case(tmp_path)

    class Missing:
        def __init__(self): self.calls = 0
        def get_action_history(self, **kwargs):
            self.calls += 1
            raise YFTzMissingError("SECRET")

    actions = Missing()
    assert run(args, actions=actions) == 1 and actions.calls == 1
    assert json.loads(output.read_bytes())["failure_category"] == "TIMEZONE_MISSING"


@pytest.mark.parametrize("failure", ["pin", "csv", "wrong_diagnostic", "binding", "lock", "output", "overlap"])
def test_preflight_failures_prevent_all_provider_work(tmp_path, failure):
    args, source, directory, diagnostic, output = setup_case(tmp_path)
    if failure == "pin": args[args.index("--diagnostic-report-sha256") + 1] = "0" * 64
    if failure == "csv": source.write_bytes(source.read_bytes() + b"\n")
    if failure in ("wrong_diagnostic", "binding"):
        value = json.loads(diagnostic.read_bytes())
        value["failure_category" if failure == "wrong_diagnostic" else "private_selection_sha256"] = "TIMEOUT" if failure == "wrong_diagnostic" else "0" * 64
        write_json_atomic(diagnostic, value)
        args[args.index("--diagnostic-report-sha256") + 1] = sha256(diagnostic.read_bytes()).hexdigest()
    if failure == "lock": (directory / ".portfolio-actions.lock").write_text("KEEP")
    if failure == "output": output.write_text("KEEP")
    if failure == "overlap": args[args.index("--report-output") + 1] = str(directory / "bad.json")
    search, actions = Search(), Client()
    assert run(args, search, actions) == 1 and not search.calls and not actions.calls
    if failure == "output": assert output.read_text() == "KEEP"
    if failure == "lock": assert (directory / ".portfolio-actions.lock").read_text() == "KEEP"


@pytest.mark.parametrize("failure", ["private_write", "report_write", "readback", "source_change", "snapshot_change"])
def test_late_failures_retain_evidence_and_never_claim_completion(tmp_path, capsys, failure):
    args, source, directory, _, output = setup_case(tmp_path)
    capsys.readouterr()

    def writer(path, value):
        if failure == "private_write" and path != output: raise OSError("SECRET")
        if failure == "report_write" and path == output: raise OSError("SECRET")
        write_json_atomic(path, value)
        if failure == "readback": path.write_bytes(b"{}")
        if failure == "source_change": source.write_bytes(source.read_bytes() + b"\n")
        if failure == "snapshot_change" and path == output: next(directory.glob("*-resolved-actions.json")).write_bytes(b"{}")

    assert run(args, writer=writer) == 1
    captured = capsys.readouterr()
    assert "RESULT:" not in captured.out and "SECRET" not in captured.err
    assert list(directory.glob("*-resolved-actions.json"))


def test_search_probe_refuses_second_call():
    client = Search()
    probe = SearchProbe(lambda: client)
    probe.search_isin(WORLD.isin)
    with pytest.raises(RuntimeError): probe.search_isin(WORLD.isin)
    assert probe.calls == len(client.calls) == 1
