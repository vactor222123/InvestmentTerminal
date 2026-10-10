"""One checksum-bound replay of a failed portfolio action request, no batch resume."""

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

from investment_terminal.cli.portfolio_split_collect import plan_candidates
from investment_terminal.cli.yahoo_corporate_actions import main as collect_actions
from investment_terminal.clients.yahoo_action_failure import classify_action_failure
from investment_terminal.clients.yahoo_corporate_actions_client import YahooCorporateActionsClient
from investment_terminal.market.corporate_actions import canonical_bytes
from investment_terminal.market.split_adjustment import checksum
from investment_terminal.operations.yahoo_corporate_actions import _unique_object, load_snapshot
from investment_terminal.portfolio.transaction_csv_parser import PortfolioTransactionCsvParser
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransactionLedger
from investment_terminal.utils.atomic_write import write_json_atomic


def read_pinned(path, pin):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("Unsafe evidence path")
    with path.open("rb") as stream:
        data = stream.read(4_000_001)
    if len(data) > 4_000_000 or sha256(data).hexdigest() != checksum(pin):
        raise ValueError("Evidence mismatch")
    return data


def read_json(data):
    return json.loads(data, object_pairs_hook=_unique_object)


def prepare_request(report, pin, directory, now):
    evidence = read_json(read_pinned(report, pin))
    if (type(evidence.get("schema_version")) is not int or evidence["schema_version"] != 1
            or evidence.get("operation_identity") != "PORTFOLIO_SPLIT_COLLECTION_REPORT"
            or evidence.get("status") != "STOPPED" or evidence.get("adjustment_performed") is not False):
        raise ValueError("Expected stopped collection")
    token = sha256(str(report).encode("utf-8")).hexdigest()[:24]
    private = directory / (token + "-selection.json")
    payload = read_json(read_pinned(private, evidence["private_output_sha256"]))
    if (type(payload.get("schema_version")) is not int or payload["schema_version"] != 1
            or payload.get("operation_identity") != "PORTFOLIO_SPLIT_CANDIDATES"
            or payload.get("adjustment_performed") is not False
            or payload["source_csv_sha256"] != evidence["source_csv_sha256"]):
        raise ValueError("Invalid private evidence")
    source = Path(payload["source_csv_path"])
    read_pinned(source, evidence["source_csv_sha256"])
    batch = PortfolioTransactionCsvParser.load(source, imported_at=now)
    ledger = PortfolioTransactionLedger("diagnostic", "Private diagnostic", "USD",
        tuple(sorted(batch.transactions, key=lambda t: (t.occurred_at, t.transaction_id))))
    end = datetime.fromisoformat(payload["end_exclusive"])
    if end.utcoffset() != timezone.utc.utcoffset(end) or end.time() != datetime.min.time() or end > now:
        raise ValueError("Invalid original end")
    plan = plan_candidates(ledger, end, 50)
    items = payload["items"]
    if not isinstance(items, list) or len(items) != len(plan) or evidence["instrument_count"] != len(plan):
        raise ValueError("Selection count mismatch")
    statuses = ("BLOCKED", "FAILED", "PENDING", "SPLITS_OBSERVED", "NO_SPLITS_OBSERVED")
    for expected, item in zip(plan, items):
        if item["status"] not in statuses:
            raise ValueError("Invalid item status")
        if any(canonical_bytes(item[key]) != canonical_bytes(expected[key]) for key in ("instrument", "start", "end")):
            raise ValueError("Original CSV/selection mismatch")
    counts = {status: sum(i["status"] == status for i in items) for status in statuses}
    categories = {category: sum(i["category"] == category for i in items)
                  for category in {i["category"] for i in items if i["category"]}}
    if canonical_bytes(counts) != canonical_bytes(evidence["counts"]) or categories != evidence["category_counts"]:
        raise ValueError("Report/index mismatch")
    failed = [index for index, item in enumerate(items) if item["status"] == "FAILED"]
    if len(failed) != 1 or items[failed[0]]["category"] != "PROVIDER_REQUEST" or plan[failed[0]]["status"] != "PENDING":
        raise ValueError("Exactly one eligible failed provider request required")
    bindings = ((report, pin), (private, evidence["private_output_sha256"]),
                (source, evidence["source_csv_sha256"]))
    for path, digest in bindings:
        read_pinned(path, digest)
    return plan[failed[0]], bindings


class RequestProbe:
    def __init__(self, factory):
        self.factory = factory
        self.calls = 0
        self.category = None
        self.phase = None

    def get_action_history(self, **kwargs):
        if self.calls:
            raise RuntimeError("Only one diagnostic invocation allowed")
        self.calls += 1
        try:
            self.phase = "CLIENT_SETUP"
            client = self.factory()
            self.phase = "HISTORY_OR_METADATA"
            return client.get_action_history(**kwargs)
        except Exception as exc:
            self.category = classify_action_failure(exc)
            raise


def main(argv=None, *, client_factory=None, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("collection-report", "snapshot-directory", "cache-directory", "report-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--collection-report-sha256", required=True)
    options = parser.parse_args(argv)
    stage = "PREFLIGHT"
    try:
        raw = (options.collection_report, options.snapshot_directory, options.cache_directory, options.report_output)
        if any(not p.is_absolute() or p.is_symlink() for p in raw):
            raise ValueError("Absolute non-symlink paths required")
        original, directory, cache, output = (p.resolve() for p in raw)
        if (not directory.is_dir() or output.exists() or output == original
                or directory.is_relative_to(cache) or cache.is_relative_to(directory)):
            raise ValueError("Invalid diagnostic paths")
        for report in (original, output):
            for private in (directory, cache):
                if report.parent.is_relative_to(private) or private.is_relative_to(report.parent):
                    raise ValueError("Private/report overlap")
        now = clock() if clock else datetime.now(timezone.utc)
        selected, bindings = prepare_request(original, options.collection_report_sha256, directory, now)
        source = bindings[2][0]
        if source.is_relative_to(output.parent) or source.is_relative_to(cache):
            raise ValueError("Source/report/cache overlap")
        token = sha256(str(output).encode("utf-8")).hexdigest()[:24]
        snapshot_path = directory / (token + "-diagnostic-actions.json")
        stage_report = directory / (token + "-diagnostic-stage.json")
        targets = (snapshot_path, stage_report, output)
        if any(p.exists() or p.is_symlink() for p in targets):
            raise ValueError("Diagnostic output exists")
        with ExitStack() as locks:
            output.parent.mkdir(parents=True, exist_ok=True)
            for lock in sorted((directory / ".portfolio-actions.lock", output.with_name(output.name + ".lock"))):
                with lock.open("x", encoding="ascii"):
                    pass
                locks.callback(lock.unlink)
            if any(p.exists() for p in targets):
                raise ValueError("Output appeared")
            for path, pin in bindings:
                read_pinned(path, pin)
            probe = RequestProbe(client_factory or (lambda: YahooCorporateActionsClient(cache_directory=cache)))
            args = ["--symbol", selected["instrument"]["symbol"], "--start", selected["start"][:10],
                    "--end", selected["end"][:10], "--snapshot-output", str(snapshot_path),
                    "--report-output", str(stage_report)]
            stage = "REQUEST"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = collect_actions(args, client=probe, clock=clock)
            if probe.calls != 1:
                raise ValueError("Expected one provider invocation")
            stage_payload = read_json(stage_report.read_bytes())
            if stage_payload["reused_snapshot"] is not False:
                raise ValueError("Unexpected offline reuse")
            snapshot_hash = None
            if code == 0:
                snapshot, snapshot_hash = load_snapshot(snapshot_path)
                if (stage_payload["status"] != "STORED" or stage_payload["snapshot_sha256"] != snapshot_hash
                        or (snapshot.symbol, snapshot.start.isoformat(), snapshot.end.isoformat()) !=
                        (selected["instrument"]["symbol"], selected["start"], selected["end"])):
                    raise ValueError("Snapshot/stage mismatch")
            elif stage_payload["status"] != "FAILED":
                raise ValueError("Failure/stage mismatch")
            for path, pin in bindings:
                read_pinned(path, pin)
            category = probe.category or ("COLLECTION_VALIDATION_OR_STORAGE" if code else None)
            result = {"schema_version": 1, "operation_identity": "PORTFOLIO_SPLIT_PROVIDER_DIAGNOSTIC",
                      "status": "COLLECTED" if code == 0 else "FAILED",
                      "collection_report_sha256": bindings[0][1], "private_selection_sha256": bindings[1][1],
                      "source_csv_sha256": bindings[2][1], "provider_invocation_count": probe.calls,
                      "failure_category": category, "failure_phase": probe.phase if probe.category else None,
                      "stage_report_sha256": sha256(stage_report.read_bytes()).hexdigest(),
                      "snapshot_sha256": snapshot_hash, "adjustment_performed": False,
                      "limitations": ["new observation; not proof of original failure cause",
                                      "one history/metadata invocation may issue multiple HTTP requests",
                                      "no automatic batch resume or verified broker mapping"]}
            stage = "OUTPUT"
            writer(output, result)
            if canonical_bytes(read_json(output.read_bytes())) != canonical_bytes(result):
                raise ValueError("Diagnostic readback mismatch")
            for path, pin in bindings:
                read_pinned(path, pin)
            if sha256(stage_report.read_bytes()).hexdigest() != result["stage_report_sha256"]:
                raise ValueError("Stage report changed")
            if snapshot_hash:
                read_pinned(snapshot_path, snapshot_hash)
        print("RESULT: " + result["status"])
        print("SEND: " + str(output))
        print("REPORT_SHA256: " + sha256(output.read_bytes()).hexdigest())
        return 0 if code == 0 else 1
    except Exception:
        print("Single action diagnosis failed at " + stage + "; preserve outputs", file=sys.stderr)
        return 1
    finally:
        print("DO NOT SEND: CSV, private selection, snapshots, stage report, cache or database")


if __name__ == "__main__":
    raise SystemExit(main())
