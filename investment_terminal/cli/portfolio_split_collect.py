"""Bounded candidate action collection from one automatically discovered CSV.

Collection is not broker identity verification or permission to adjust holdings.
"""

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys

from investment_terminal.cli.yahoo_corporate_actions import main as collect_actions
from investment_terminal.market.corporate_actions import canonical_bytes
from investment_terminal.operations.yahoo_corporate_actions import load_snapshot
from investment_terminal.portfolio.transaction_csv_parser import PortfolioTransactionCsvParser
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransactionLedger
from investment_terminal.utils.atomic_write import write_json_atomic
from investment_terminal.utils.validation import validate_aware_datetime


class PreflightError(ValueError):
    """Fixed local diagnosis; never includes file names or parser messages."""

    def __init__(self, category, **counts):
        super().__init__(category)
        self.category = category
        self.counts = counts


def print_preflight(status, category=None, **counts):
    print("PREFLIGHT_RESULT: " + json.dumps({
        "schema_version": 1, "operation_identity": "PORTFOLIO_SPLIT_PREFLIGHT",
        "status": status, "failure_category": category, "counts": counts,
        "collection_started": False,
    }, sort_keys=True, allow_nan=False))


def discover_transactions(directory, now):
    """Never pick a CSV by filename, modification time or first match."""
    candidates = []
    seen = 0
    invalid = 0
    for path in sorted(directory.rglob("*.csv")):
        seen += 1
        if seen > 100:
            raise PreflightError("CSV_FILE_LIMIT", csv_seen_count=seen, maximum_csv_count=100)
        if path.is_symlink():
            raise PreflightError("CSV_SYMLINK")
        try:
            if path.stat().st_size > 4_000_000:
                raise PreflightError("CSV_SIZE_LIMIT", maximum_bytes=4_000_000)
            data = path.read_bytes()
        except OSError:
            raise PreflightError("CSV_READ_ERROR") from None
        try:
            batch = PortfolioTransactionCsvParser.load(path, imported_at=now)
        except (ValueError, TypeError, UnicodeError):
            invalid += 1
            continue
        except OSError:
            raise PreflightError("CSV_READ_ERROR") from None
        try:
            if path.read_bytes() != data:
                raise PreflightError("CSV_CHANGED")
        except OSError:
            raise PreflightError("CSV_READ_ERROR") from None
        ids = [t.transaction_id for t in batch.transactions]
        if len(set(ids)) != len(ids):
            raise PreflightError("DUPLICATE_TRANSACTION_IDS", duplicate_id_count=len(ids) - len(set(ids)))
        try:
            ledger = PortfolioTransactionLedger(
                "action-candidates", "Private action candidates", "USD",
                tuple(sorted(batch.transactions, key=lambda t: (t.occurred_at, t.transaction_id))),
            )
        except (TypeError, ValueError):
            raise PreflightError("LEDGER_INVALID") from None
        candidates.append((path, sha256(data).hexdigest(), ledger))
    if len(candidates) != 1:
        raise PreflightError("CSV_NOT_FOUND" if not candidates else "CSV_AMBIGUOUS",
                             csv_seen_count=seen, valid_csv_count=len(candidates), invalid_csv_count=invalid)
    return (*candidates[0], invalid)


def plan_candidates(ledger, end, limit):
    groups = {}
    for trade in ledger.transactions:
        if trade.transaction_type in ("BUY", "SELL"):
            groups.setdefault(trade.instrument.instrument_key, []).append(trade)
    if not groups:
        raise PreflightError("NO_TRADE_INSTRUMENTS", instrument_count=0)
    if len(groups) > limit:
        raise PreflightError("INSTRUMENT_BUDGET", instrument_count=len(groups), maximum_instruments=limit)
    items = []
    for key, trades in sorted(groups.items()):
        instrument = trades[0].instrument
        start = min(t.occurred_at for t in trades).astimezone(timezone.utc)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=2)
        category = None
        if any(t.instrument != instrument for t in trades):
            category = "IDENTITY_CHANGED"
        elif instrument.instrument_type not in ("STOCK", "ETF"):
            category = "UNSUPPORTED_TYPE"
        elif re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=_-]{0,63}", instrument.symbol) is None:
            category = "UNSUPPORTED_SYMBOL"
        elif not start < end <= start + timedelta(days=3660) or any(t.occurred_at >= end for t in trades):
            category = "TRADE_WINDOW"
        items.append({"instrument": instrument.to_dict(), "start": start.isoformat(),
                      "end": end.isoformat(), "status": "BLOCKED" if category else "PENDING",
                      "category": category, "snapshot_sha256": None,
                      "split_count": None, "snapshot_path": None})
    symbols = [item["instrument"]["symbol"] for item in items]
    for item in items:
        if symbols.count(item["instrument"]["symbol"]) > 1:
            item.update(status="BLOCKED", category="AMBIGUOUS_SYMBOL")
    return items


def main(argv=None, *, collector=collect_actions, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("transactions-directory", "snapshot-directory", "report-output", "cache-directory"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--end", required=True, help="Exclusive UTC YYYY-MM-DD")
    parser.add_argument("--max-instruments", type=int, default=10)
    parser.add_argument("--maximum-age-days", type=int, default=7)
    parser.add_argument("--preflight-only", action="store_true",
                        help="Read-only checks; no collector, locks, directories or output writes")
    options = parser.parse_args(argv)
    stage = "PREFLIGHT"
    try:
        raw = (options.transactions_directory, options.snapshot_directory,
               options.report_output, options.cache_directory)
        if any(not p.is_absolute() or p.is_symlink() for p in raw):
            raise PreflightError("PATH_NOT_ABSOLUTE_OR_SYMLINK")
        root, directory, report, cache = (p.resolve() for p in raw)
        if not root.is_dir():
            raise PreflightError("INPUT_DIRECTORY_MISSING")
        if report.exists():
            raise PreflightError("REPORT_EXISTS")
        if directory == root:
            raise PreflightError("SNAPSHOT_INPUT_OVERLAP")
        if not 1 <= options.max_instruments <= 50:
            raise PreflightError("INVALID_INSTRUMENT_LIMIT")
        if not 1 <= options.maximum_age_days <= 365:
            raise PreflightError("INVALID_AGE_LIMIT")
        if any(p.exists() and not p.is_dir() for p in (directory, cache, report.parent)):
            raise PreflightError("OUTPUT_DIRECTORY_INVALID")
        for value in (root, directory, cache):
            if value.is_relative_to(report.parent) or report.parent.is_relative_to(value):
                raise PreflightError("REPORT_PRIVATE_OVERLAP")
        if directory.is_relative_to(cache) or cache.is_relative_to(directory):
            raise PreflightError("CACHE_SNAPSHOT_OVERLAP")
        try:
            now = validate_aware_datetime(clock() if clock else datetime.now(timezone.utc),
                                          field_name="clock").astimezone(timezone.utc)
        except (TypeError, ValueError):
            raise PreflightError("INVALID_CLOCK") from None
        try:
            end = datetime.strptime(options.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise PreflightError("INVALID_END_DATE") from None
        if end > now.replace(hour=0, minute=0, second=0, microsecond=0):
            raise PreflightError("FUTURE_END_DATE")
        source, source_hash, ledger, invalid_csv = discover_transactions(root, now)
        items = plan_candidates(ledger, end, options.max_instruments)
        token = sha256(str(report).encode("utf-8")).hexdigest()[:24]
        private = directory / (token + "-selection.json")
        if private.exists():
            raise PreflightError("PRIVATE_SELECTION_EXISTS")
        lock_paths = (directory / ".portfolio-actions.lock", report.with_name(report.name + ".lock"))
        if any(path.exists() or path.is_symlink() for path in lock_paths):
            raise PreflightError("OUTPUT_LOCK_EXISTS")

        if options.preflight_only:
            if sha256(source.read_bytes()).hexdigest() != source_hash:
                raise PreflightError("CSV_CHANGED")
            blocked = sum(item["status"] == "BLOCKED" for item in items)
            print_preflight("READY_WITH_BLOCKERS" if blocked else "READY",
                            valid_csv_count=1, invalid_csv_count=invalid_csv,
                            instrument_count=len(items), maximum_instruments=options.max_instruments,
                            blocked_instrument_count=blocked, pending_instrument_count=len(items) - blocked)
            return 0

        def verify_source():
            if sha256(source.read_bytes()).hexdigest() != source_hash:
                raise ValueError("Source changed")

        with ExitStack() as locks:
            directory.mkdir(parents=True, exist_ok=True)
            report.parent.mkdir(parents=True, exist_ok=True)
            for lock in sorted(lock_paths):
                with lock.open("x", encoding="ascii"):
                    pass
                locks.callback(lock.unlink)
            if private.exists() or report.exists():
                raise ValueError("Output appeared")
            stopped = False
            for index, item in enumerate(items):
                if item["status"] == "BLOCKED":
                    continue
                stage = "COLLECTION"
                verify_source()
                identity = item["instrument"]
                binding = {"instrument": identity, "start": item["start"], "end": item["end"]}
                name = sha256(canonical_bytes(binding)).hexdigest()
                snapshot_path = directory / (name + "-actions.json")
                item["snapshot_path"] = str(snapshot_path)
                stage_report = directory / (token + "-" + str(index) + "-collection.json")
                if stage_report.exists() or snapshot_path.is_symlink():
                    raise ValueError("Unsafe stage output")
                args = ["--symbol", identity["symbol"], "--start", item["start"][:10],
                        "--end", options.end, "--snapshot-output", str(snapshot_path),
                        "--report-output", str(stage_report), "--cache-directory", str(cache)]
                # Provider/stage console messages are not the shareable report.
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = collector(args, clock=clock)
                verify_source()
                if code != 0:
                    category = "COLLECTION_FAILED"
                    if stage_report.is_file():
                        failure = json.loads(stage_report.read_bytes()).get("failure_category")
                        if failure in ("PROVIDER_REQUEST", "EMPTY_HISTORY", "SYMBOL_MISMATCH",
                                       "EXISTING_SNAPSHOT_INVALID", "SNAPSHOT_WRITE_OR_VERIFY"):
                            category = failure
                    item.update(status="FAILED", category=category)
                    stopped = True
                    break  # No retries or subsequent provider work after failure.
                snapshot, digest = load_snapshot(snapshot_path)
                collected = json.loads(stage_report.read_bytes())
                if (collected.get("status") != "STORED" or collected.get("snapshot_sha256") != digest
                        or (snapshot.symbol, snapshot.start.isoformat(), snapshot.end.isoformat()) !=
                        (identity["symbol"], item["start"], item["end"])):
                    raise ValueError("Stage evidence mismatch")
                item["snapshot_sha256"] = digest
                evaluated = validate_aware_datetime(clock() if clock else datetime.now(timezone.utc),
                                                     field_name="clock").astimezone(timezone.utc)
                if not snapshot.fetched_at <= evaluated <= snapshot.fetched_at + timedelta(days=options.maximum_age_days):
                    item.update(status="BLOCKED", category="SNAPSHOT_AGE")
                elif (snapshot.quote_currency, snapshot.instrument_type.replace("EQUITY", "STOCK")) != (
                        identity["currency"], identity["instrument_type"]):
                    item.update(status="BLOCKED", category="METADATA_MISMATCH")
                else:
                    item["split_count"] = sum(e.kind == "SPLIT" for e in snapshot.events)
                    item["status"] = "SPLITS_OBSERVED" if item["split_count"] else "NO_SPLITS_OBSERVED"
            stage = "OUTPUT"
            verify_source()
            payload = {"schema_version": 1, "operation_identity": "PORTFOLIO_SPLIT_CANDIDATES",
                       "source_csv_path": str(source), "source_csv_sha256": source_hash,
                       "end_exclusive": end.isoformat(), "items": items,
                       "identity_assurance": "UNVERIFIED_PROVIDER_MAPPING",
                       "adjustment_performed": False}
            writer(private, payload)
            if canonical_bytes(json.loads(private.read_bytes())) != canonical_bytes(payload):
                raise ValueError("Private readback mismatch")
            private_hash = sha256(private.read_bytes()).hexdigest()
            counts = {status: sum(i["status"] == status for i in items) for status in (
                "BLOCKED", "FAILED", "PENDING", "SPLITS_OBSERVED", "NO_SPLITS_OBSERVED")}
            evidence = {"schema_version": 1, "operation_identity": "PORTFOLIO_SPLIT_COLLECTION_REPORT",
                        "status": "STOPPED" if stopped else "COMPLETE_WITH_BLOCKERS" if counts["BLOCKED"] else "COLLECTED",
                        "source_csv_sha256": source_hash, "private_output_sha256": private_hash,
                        "instrument_count": len(items), "counts": counts, "invalid_csv_count": invalid_csv,
                        "category_counts": {category: sum(i["category"] == category for i in items)
                                            for category in sorted({i["category"] for i in items if i["category"]})},
                        "maximum_age_days": options.maximum_age_days,
                        "identity_assurance": "UNVERIFIED_PROVIDER_MAPPING",
                        "action_completeness": "UNKNOWN", "adjustment_performed": False}
            writer(report, evidence)
            if canonical_bytes(json.loads(report.read_bytes())) != canonical_bytes(evidence):
                raise ValueError("Report readback mismatch")
            verify_source()
            if sha256(private.read_bytes()).hexdigest() != private_hash:
                raise ValueError("Private result changed")
            for item in items:
                if item["snapshot_sha256"] and sha256(Path(item["snapshot_path"]).read_bytes()).hexdigest() != item["snapshot_sha256"]:
                    raise ValueError("Snapshot changed")
        print("RESULT: " + evidence["status"])
        print("SEND: " + str(report))
        print("REPORT_SHA256: " + sha256(report.read_bytes()).hexdigest())
        return 1 if stopped else 0
    except PreflightError as exc:
        print_preflight("FAILED", exc.category, **exc.counts)
        return 1
    except Exception:
        if stage == "PREFLIGHT":
            print_preflight("FAILED", "PREFLIGHT_UNEXPECTED")
        print("Portfolio action collection failed at " + stage + "; preserve outputs", file=sys.stderr)
        return 1
    finally:
        print("DO NOT SEND: CSV, private selection, snapshots, cache or database")


if __name__ == "__main__":
    raise SystemExit(main())
