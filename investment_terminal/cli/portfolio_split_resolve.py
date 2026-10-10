"""Resolve one failed action candidate through ISIN search and an existing ticker."""

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
import io
from pathlib import Path
import re
import sys

import yfinance as yf

from investment_terminal.cli.portfolio_split_diagnose import prepare_request, read_json, read_pinned, RequestProbe
from investment_terminal.cli.yahoo_corporate_actions import main as collect_actions
from investment_terminal.clients.yahoo_action_failure import classify_action_failure
from investment_terminal.clients.yahoo_corporate_actions_client import YahooCorporateActionsClient
from investment_terminal.clients.yahoo_search_client import YahooSearchClient
from investment_terminal.market.corporate_actions import canonical_bytes
from investment_terminal.operations.yahoo_corporate_actions import load_snapshot
from investment_terminal.operations.yahoo_isin_search_qualification import YahooIsinSearchQualificationService, YahooIsinSearchStatus
from investment_terminal.operations.yahoo_ticker_match_qualification import YahooTickerMatchQualificationService, YahooTickerMatchStatus
from investment_terminal.utils.atomic_write import write_json_atomic


class SearchProbe:
    def __init__(self, factory):
        self.factory = factory
        self.calls = 0
        self.failure = None

    def search_isin(self, isin):
        if self.calls:
            raise RuntimeError("Only one ISIN search allowed")
        self.calls += 1
        try:
            rows = self.factory().search_isin(isin)
            if not isinstance(rows, list) or len(rows) > 25:
                raise ValueError("Invalid search bound")
            return rows
        except Exception as exc:
            # The existing Yahoo search adapter wraps its provider exception once.
            self.failure = classify_action_failure(exc.__cause__ or exc)
            raise


def main(argv=None, *, search_factory=YahooSearchClient, action_factory=None, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("diagnostic-report", "collection-report", "snapshot-directory", "cache-directory", "report-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--diagnostic-report-sha256", required=True)
    options = parser.parse_args(argv)
    stage = "PREFLIGHT"
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        raw = (options.diagnostic_report, options.collection_report, options.snapshot_directory,
               options.cache_directory, options.report_output)
        if any(not p.is_absolute() or p.is_symlink() for p in raw):
            raise ValueError("Absolute non-symlink paths required")
        diagnostic, original, directory, cache, output = (p.resolve() for p in raw)
        if (not directory.is_dir() or output.exists() or len(set(raw)) != 5
                or directory.is_relative_to(cache) or cache.is_relative_to(directory)):
            raise ValueError("Invalid paths")
        for report in (diagnostic, original, output):
            for private in (directory, cache):
                if report.parent.is_relative_to(private) or private.is_relative_to(report.parent):
                    raise ValueError("Report/private overlap")
        evidence = read_json(read_pinned(diagnostic, options.diagnostic_report_sha256))
        if (type(evidence.get("schema_version")) is not int or evidence["schema_version"] != 1
                or evidence.get("operation_identity") != "PORTFOLIO_SPLIT_PROVIDER_DIAGNOSTIC"
                or evidence.get("status") != "FAILED" or evidence.get("adjustment_performed") is not False
                or evidence.get("failure_category") not in ("TIMEZONE_MISSING", "PRICE_DATA_MISSING")
                or evidence.get("failure_phase") != "HISTORY_OR_METADATA"
                or type(evidence.get("provider_invocation_count")) is not int or evidence["provider_invocation_count"] != 1):
            raise ValueError("Expected missing-symbol diagnostic")
        selected, originals = prepare_request(original, evidence["collection_report_sha256"], directory, runtime_clock())
        if (evidence["private_selection_sha256"], evidence["source_csv_sha256"]) != (originals[1][1], originals[2][1]):
            raise ValueError("Diagnostic/source binding mismatch")
        bindings = (*originals, (diagnostic, options.diagnostic_report_sha256))
        source = originals[2][0]
        if source.is_relative_to(output.parent) or source.is_relative_to(cache):
            raise ValueError("Source/output overlap")
        token = sha256(str(output).encode("utf-8")).hexdigest()[:24]
        private_output = directory / (token + "-resolution.json")
        snapshot_path = directory / (token + "-resolved-actions.json")
        stage_report = directory / (token + "-resolved-stage.json")
        targets = (output, private_output, snapshot_path, stage_report)
        if any(p.exists() or p.is_symlink() for p in targets):
            raise ValueError("Output exists")

        def verify_inputs():
            for path, pin in bindings:
                read_pinned(path, pin)

        with ExitStack() as locks:
            output.parent.mkdir(parents=True, exist_ok=True)
            for lock in sorted((directory / ".portfolio-actions.lock", output.with_name(output.name + ".lock"))):
                with lock.open("x", encoding="ascii"):
                    pass
                locks.callback(lock.unlink)
            if any(p.exists() for p in targets):
                raise ValueError("Output appeared")
            verify_inputs()
            instrument = selected["instrument"]
            status, category = "BLOCKED", "MISSING_ISIN"
            search = SearchProbe(search_factory)
            search_result = match = None
            probe = RequestProbe(action_factory or (lambda: YahooCorporateActionsClient(cache_directory=cache)))
            candidate = None
            snapshot_hash = stage_hash = None
            if instrument["isin"]:
                stage = "SEARCH"
                if search_factory is YahooSearchClient:
                    cache.mkdir(parents=True, exist_ok=True)
                    yf.set_tz_cache_location(str(cache))
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    search_result = YahooIsinSearchQualificationService(client=search, clock=runtime_clock).qualify(instrument["isin"])
                verify_inputs()
                if search_result.status is YahooIsinSearchStatus.FAILED:
                    status, category = "FAILED", "SEARCH_FAILED"
                elif search_result.status is YahooIsinSearchStatus.EMPTY:
                    category = "NO_SEARCH_CANDIDATES"
                elif not instrument["exchange_ticker"]:
                    category = "MISSING_EXISTING_TICKER"
                else:
                    match = YahooTickerMatchQualificationService(clock=runtime_clock).qualify(
                        instrument_key=instrument["instrument_key"], exchange_ticker=instrument["exchange_ticker"],
                        candidates=search_result.private_dict()["candidates"])
                    if match.status is not YahooTickerMatchStatus.MATCHED:
                        category = {YahooTickerMatchStatus.NO_MATCH: "EXISTING_TICKER_NOT_FOUND",
                                    YahooTickerMatchStatus.AMBIGUOUS: "AMBIGUOUS_EXISTING_TICKER",
                                    YahooTickerMatchStatus.FAILED: "MATCH_VALIDATION_FAILED"}[match.status]
                    else:
                        candidate = match.private_match["candidate"]
                        if candidate["quote_type"] != instrument["instrument_type"].replace("STOCK", "EQUITY"):
                            category = "QUOTE_TYPE_MISMATCH"
                        elif candidate["currency"] is not None and candidate["currency"] != instrument["currency"]:
                            category = "SEARCH_CURRENCY_MISMATCH"
                        elif re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=_-]{0,63}", candidate["symbol"]) is None:
                            category = "UNSUPPORTED_PROVIDER_SYMBOL"
                        else:
                            stage = "COLLECTION"
                            args = ["--symbol", candidate["symbol"], "--start", selected["start"][:10],
                                    "--end", selected["end"][:10], "--snapshot-output", str(snapshot_path),
                                    "--report-output", str(stage_report)]
                            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                                code = collect_actions(args, client=probe, clock=runtime_clock)
                            verify_inputs()
                            if probe.calls != 1:
                                raise ValueError("Expected one action invocation")
                            stage_bytes = stage_report.read_bytes()
                            stage_payload = read_json(stage_bytes)
                            stage_hash = sha256(stage_bytes).hexdigest()
                            if code:
                                if stage_payload["status"] != "FAILED":
                                    raise ValueError("Stage failure mismatch")
                                status, category = "FAILED", probe.category or "COLLECTION_VALIDATION_OR_STORAGE"
                            else:
                                snapshot, snapshot_hash = load_snapshot(snapshot_path)
                                if (stage_payload["status"] != "STORED" or stage_payload["snapshot_sha256"] != snapshot_hash
                                        or stage_payload["reused_snapshot"] is not False
                                        or (snapshot.symbol, snapshot.start.isoformat(), snapshot.end.isoformat()) !=
                                        (candidate["symbol"], selected["start"], selected["end"])):
                                    raise ValueError("Stage snapshot mismatch")
                                if (snapshot.quote_currency, snapshot.instrument_type.replace("EQUITY", "STOCK")) != (
                                        instrument["currency"], instrument["instrument_type"]):
                                    category = "ACTION_METADATA_MISMATCH"
                                else:
                                    status, category = "RESOLVED_CANDIDATE", None
            stage = "OUTPUT"
            payload = {"schema_version": 1, "operation_identity": "PORTFOLIO_SPLIT_SYMBOL_RESOLUTION",
                       "diagnostic_report_sha256": bindings[3][1], "source_csv_sha256": bindings[2][1],
                       "instrument": instrument, "request": selected, "status": status, "category": category,
                       "search": search_result.private_dict() if search_result else None,
                       "match": match.private_match if match else None,
                       "snapshot_path": str(snapshot_path) if snapshot_hash else None,
                       "snapshot_sha256": snapshot_hash, "adjustment_performed": False}
            verify_inputs()
            writer(private_output, payload)
            if canonical_bytes(read_json(private_output.read_bytes())) != canonical_bytes(payload):
                raise ValueError("Private readback mismatch")
            private_hash = sha256(private_output.read_bytes()).hexdigest()
            result = {"schema_version": 1, "operation_identity": "PORTFOLIO_SPLIT_SYMBOL_RESOLUTION_REPORT",
                      "status": status, "failure_category": category,
                      "diagnostic_report_sha256": bindings[3][1], "collection_report_sha256": bindings[0][1],
                      "private_selection_sha256": bindings[1][1], "source_csv_sha256": bindings[2][1],
                      "private_output_sha256": private_hash, "snapshot_sha256": snapshot_hash,
                      "stage_report_sha256": stage_hash, "search_invocation_count": search.calls,
                      "action_invocation_count": probe.calls, "search_failure_category": search.failure,
                      "candidate_count": len(search_result.candidates) if search_result and search_result.status is not YahooIsinSearchStatus.FAILED else None,
                      "exact_match_count": match.exact_match_count if match else None,
                      "provider_symbol_changed": candidate["symbol"] != instrument["symbol"] if candidate else None,
                      "identity_assurance": "UNVERIFIED_BROKER_MAPPING", "adjustment_performed": False}
            writer(output, result)
            if canonical_bytes(read_json(output.read_bytes())) != canonical_bytes(result):
                raise ValueError("Report readback mismatch")
            verify_inputs()
            read_pinned(private_output, private_hash)
            if snapshot_hash:
                read_pinned(snapshot_path, snapshot_hash)
            if stage_hash:
                read_pinned(stage_report, stage_hash)
        print("RESULT: " + status)
        print("SEND: " + str(output))
        print("REPORT_SHA256: " + sha256(output.read_bytes()).hexdigest())
        return 0 if status == "RESOLVED_CANDIDATE" else 1
    except Exception:
        print("Split symbol resolution failed at " + stage + "; preserve outputs", file=sys.stderr)
        return 1
    finally:
        print("DO NOT SEND: CSV, private selection, candidates, snapshots, cache or database")


if __name__ == "__main__":
    raise SystemExit(main())
