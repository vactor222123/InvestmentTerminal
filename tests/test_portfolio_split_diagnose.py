from functools import partial
from hashlib import sha256
import json
from types import SimpleNamespace

from curl_cffi.requests import exceptions as curl
import pytest
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError, YFTzMissingError

from investment_terminal.cli.portfolio_split_diagnose import main, RequestProbe
from investment_terminal.cli.portfolio_split_collect import main as batch_main
from investment_terminal.cli.yahoo_corporate_actions import main as collect
from investment_terminal.clients.yahoo_action_failure import classify_action_failure
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_portfolio_split_collect import Client, case
from tests.test_position_reconstruction import WORLD, EM
from tests.test_split_adjustment import at


@pytest.mark.parametrize("error,category", [
    (YFRateLimitError(), "RATE_LIMIT"), (curl.Timeout("SECRET"), "TIMEOUT"),
    (TimeoutError("SECRET"), "TIMEOUT"), (curl.ConnectTimeout("SECRET"), "TIMEOUT"),
    (YFPricesMissingError("SECRET", "PRIVATE"), "PRICE_DATA_MISSING"),
    (YFTzMissingError("SECRET"), "TIMEZONE_MISSING"),
    (curl.CertificateVerifyError("SECRET"), "TLS_ERROR"),
    (curl.DNSError("SECRET"), "CONNECTION_ERROR"),
    (curl.HTTPError("SECRET", response=SimpleNamespace(status_code=429)), "RATE_LIMIT"),
    (curl.HTTPError("SECRET", response=SimpleNamespace(status_code=403)), "HTTP_ACCESS_DENIED"),
    (curl.HTTPError("SECRET", response=SimpleNamespace(status_code=503)), "HTTP_SERVER_ERROR"),
    (curl.HTTPError("SECRET", response=SimpleNamespace(status_code="429")), "HTTP_ERROR"),
    (curl.RequestException("SECRET"), "TRANSPORT_ERROR"),
    (RuntimeError("429 timeout delisted SECRET"), "UNKNOWN_PROVIDER_ERROR"),
])
def test_typed_classification_never_guesses_from_text(error, category):
    assert classify_action_failure(error) == category


def setup_case(tmp_path):
    args, source, directory, report = case(tmp_path)
    text = source.read_text()
    row = text.splitlines()[1].replace("b,BUY", "b2,BUY").replace("WORLD", "EM").replace(WORLD.isin, EM.isin)
    source.write_text(text + row + "\n")
    assert batch_main(args, collector=partial(collect, client=Client(error=True)), clock=lambda: at(22)) == 1
    output = report.with_name("diagnostic.json")
    diag = ["--collection-report", str(report), "--collection-report-sha256", sha256(report.read_bytes()).hexdigest(),
            "--snapshot-directory", str(directory), "--cache-directory", str(tmp_path / "cache"),
            "--report-output", str(output)]
    return diag, source, directory, report, output


def test_success_only_replays_failed_item_and_retains_new_snapshot(tmp_path, capsys):
    args, source, directory, original, output = setup_case(tmp_path)
    capsys.readouterr()
    protected = {p: p.read_bytes() for p in (source, original, *directory.glob("*.json"))}
    client = Client()
    assert main(args, client_factory=lambda: client, clock=lambda: at(22)) == 0
    assert len(client.calls) == 1
    private = json.loads(next(directory.glob("*-selection.json")).read_bytes())
    failed = next(i for i in private["items"] if i["status"] == "FAILED")
    assert client.calls[0]["symbol"] == failed["instrument"]["symbol"]
    data = json.loads(output.read_bytes())
    assert data["status"] == "COLLECTED" and data["failure_category"] is None
    assert data["snapshot_sha256"] == sha256(next(directory.glob("*-diagnostic-actions.json")).read_bytes()).hexdigest()
    assert data["provider_invocation_count"] == 1 and data["adjustment_performed"] is False
    assert all(p.read_bytes() == raw for p, raw in protected.items())
    rendered = output.read_text() + capsys.readouterr().out
    assert WORLD.isin not in rendered and EM.isin not in rendered and str(source) not in rendered
    before = output.read_bytes()
    assert main(args, client_factory=lambda: client, clock=lambda: at(22)) == 1
    assert len(client.calls) == 1 and output.read_bytes() == before


@pytest.mark.parametrize("setup", [False, True])
def test_typed_failure_phase_and_one_attempt(tmp_path, capsys, setup):
    args, _, directory, _, output = setup_case(tmp_path)
    capsys.readouterr()

    class Broken:
        def get_action_history(self, **kwargs): raise curl.Timeout("SECRET instrument URL")

    def factory():
        if setup: raise PermissionError("SECRET cache path")
        return Broken()

    assert main(args, client_factory=factory, clock=lambda: at(22)) == 1
    data = json.loads(output.read_bytes())
    assert data["failure_category"] == ("UNKNOWN_PROVIDER_ERROR" if setup else "TIMEOUT")
    assert data["failure_phase"] == ("CLIENT_SETUP" if setup else "HISTORY_OR_METADATA")
    assert data["provider_invocation_count"] == 1 and data["snapshot_sha256"] is None
    assert not list(directory.glob("*-diagnostic-actions.json"))
    captured = capsys.readouterr()
    assert "SECRET" not in captured.out + captured.err + output.read_text()


@pytest.mark.parametrize("failure", ["report_pin", "index_pin", "csv_pin", "multiple_failures", "wrong_plan", "not_stopped", "lock", "output", "overlap"])
def test_bad_bindings_and_preflight_never_call_provider(tmp_path, failure):
    args, source, directory, report, output = setup_case(tmp_path)
    index = next(directory.glob("*-selection.json"))
    if failure == "report_pin": args[args.index("--collection-report-sha256") + 1] = "0" * 64
    if failure == "index_pin": index.write_bytes(index.read_bytes() + b"\n")
    if failure == "csv_pin": source.write_bytes(source.read_bytes() + b"\n")
    if failure in ("multiple_failures", "wrong_plan"):
        private = json.loads(index.read_bytes())
        if failure == "multiple_failures": private["items"][1]["status"] = "FAILED"
        else: private["items"][0]["instrument"]["symbol"] = "WRONG"
        write_json_atomic(index, private)
        data = json.loads(report.read_bytes())
        data["private_output_sha256"] = sha256(index.read_bytes()).hexdigest()
        write_json_atomic(report, data)
        args[args.index("--collection-report-sha256") + 1] = sha256(report.read_bytes()).hexdigest()
    if failure == "not_stopped":
        data = json.loads(report.read_bytes())
        data["status"] = "COLLECTED"
        write_json_atomic(report, data)
        args[args.index("--collection-report-sha256") + 1] = sha256(report.read_bytes()).hexdigest()
    if failure == "lock": (directory / ".portfolio-actions.lock").write_text("KEEP")
    if failure == "output": output.write_text("KEEP")
    if failure == "overlap": args[args.index("--report-output") + 1] = str(directory / "report.json")

    def forbidden(): pytest.fail("Provider must not be called")

    assert main(args, client_factory=forbidden, clock=lambda: at(22)) == 1
    if failure == "output": assert output.read_text() == "KEEP"
    if failure == "lock": assert (directory / ".portfolio-actions.lock").read_text() == "KEEP"


@pytest.mark.parametrize("failure", ["write", "readback", "source_change", "snapshot_change"])
def test_late_failure_retains_snapshot_without_false_completion(tmp_path, capsys, failure):
    args, source, directory, _, output = setup_case(tmp_path)
    capsys.readouterr()

    def writer(path, value):
        if failure == "write": raise OSError("SECRET path")
        write_json_atomic(path, value)
        if failure == "readback": path.write_bytes(b"{}")
        if failure == "source_change": source.write_bytes(source.read_bytes() + b"\n")
        if failure == "snapshot_change": next(directory.glob("*-diagnostic-actions.json")).write_bytes(b"{}")

    assert main(args, client_factory=Client, clock=lambda: at(22), writer=writer) == 1
    captured = capsys.readouterr()
    assert "RESULT:" not in captured.out and "SECRET" not in captured.err
    assert list(directory.glob("*-diagnostic-actions.json"))


def test_response_validation_is_not_misclassified_as_provider_error(tmp_path):
    args, _, _, _, output = setup_case(tmp_path)
    assert main(args, client_factory=lambda: Client(splits=-2), clock=lambda: at(22)) == 1
    data = json.loads(output.read_bytes())
    assert data["failure_category"] == "COLLECTION_VALIDATION_OR_STORAGE"
    assert data["failure_phase"] is None


def test_probe_refuses_second_invocation():
    client = Client()
    probe = RequestProbe(lambda: client)
    probe.get_action_history(symbol="WORLD", start=at(1), end=at(20))
    with pytest.raises(RuntimeError):
        probe.get_action_history(symbol="WORLD", start=at(1), end=at(20))
    assert len(client.calls) == probe.calls == 1
