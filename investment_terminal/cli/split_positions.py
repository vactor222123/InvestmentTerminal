"""Offline split-aware projection from original CSV and pinned action evidence."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from investment_terminal.market.corporate_actions import canonical_bytes
from investment_terminal.market.split_adjustment import SplitPlan, checksum
from investment_terminal.operations.yahoo_corporate_actions import load_snapshot
from investment_terminal.portfolio.split_projection import project_split_positions
from investment_terminal.portfolio.transaction_csv_parser import PortfolioTransactionCsvParser
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransactionLedger
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("transactions", "actions-snapshot", "private-output", "report-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("transactions-sha256", "actions-sha256", "instrument-key"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--trade-basis", choices=("AS_TRADED",), required=True)
    parser.add_argument("--actions-maximum-age-days", type=int, required=True)
    options = parser.parse_args(argv)
    stage = "PREFLIGHT"
    try:
        originals = (options.transactions, options.actions_snapshot)
        destinations = (options.private_output, options.report_output)
        paths = (*originals, *destinations)
        if any(not p.is_absolute() or p.is_symlink() for p in paths):
            raise ValueError("Absolute non-symlink paths required")
        paths = tuple(p.resolve() for p in paths)
        source, actions, private, report = paths
        if (len(set(paths)) != 4 or any(a != b and a.is_relative_to(b) for a in paths for b in paths)
                or private.parent == report.parent or private.is_relative_to(report.parent)
                or source.is_relative_to(report.parent) or actions.is_relative_to(report.parent)
                or any(not p.is_file() for p in (source, actions))
                or any(p.exists() for p in (private, report))):
            raise ValueError("Invalid or overlapping source/output paths")
        pins = (checksum(options.transactions_sha256), checksum(options.actions_sha256))

        def check_sources():
            if tuple(sha256(p.read_bytes()).hexdigest() for p in (source, actions)) != pins:
                raise ValueError("Input checksum changed")

        check_sources()
        with ExitStack() as locks:
            for target in sorted((private, report)):
                target.parent.mkdir(parents=True, exist_ok=True)
                lock = target.with_name(target.name + ".lock")
                with lock.open("x", encoding="ascii"):
                    pass
                locks.callback(lock.unlink)
            if private.exists() or report.exists():
                raise ValueError("Output appeared")
            stage = "PROJECTION"
            snapshot, snapshot_hash = load_snapshot(actions)
            if snapshot_hash != pins[1]:
                raise ValueError("Snapshot changed")
            now = clock() if clock else datetime.now(timezone.utc)
            plan = SplitPlan(snapshot, snapshot_hash, now, options.actions_maximum_age_days)
            batch = PortfolioTransactionCsvParser.load(source, imported_at=now)
            ledger = PortfolioTransactionLedger(
                "split-projection", "Selected instrument projection", snapshot.quote_currency,
                tuple(sorted(batch.transactions, key=lambda t: (t.occurred_at, t.transaction_id))),
            )
            result = project_split_positions(ledger, plan, instrument_key=options.instrument_key,
                                             trade_basis=options.trade_basis)
            payload = result.to_dict()
            payload["source_csv_sha256"] = pins[0]
            check_sources()
            stage = "PRIVATE_WRITE"
            writer(private, payload)
            if canonical_bytes(json.loads(private.read_bytes())) != canonical_bytes(payload):
                raise ValueError("Private readback mismatch")
            private_hash = sha256(private.read_bytes()).hexdigest()
            evidence = {
                "schema_version": 1,
                "operation_identity": "SPLIT_PORTFOLIO_PROJECTION_REPORT",
                "status": "PROJECTED_WITH_LIMITATIONS",
                "source_csv_sha256": pins[0],
                "private_output_sha256": private_hash,
                "split_evidence": plan.to_dict(),
                "selected_trade_count": result.trade_count,
                "changed_trade_count": result.changed_trade_count,
                "open_position_count": int(result.position is not None),
                "market_price_adjustment": "NOT_PERFORMED_UNVERIFIED_STORED_BASIS",
                "limitations": payload["limitations"],
            }
            stage = "REPORT_WRITE"
            writer(report, evidence)
            if canonical_bytes(json.loads(report.read_bytes())) != canonical_bytes(evidence):
                raise ValueError("Report readback mismatch")
            check_sources()
            if sha256(private.read_bytes()).hexdigest() != private_hash:
                raise ValueError("Private output changed")
        print("COMPLETE: conditional split position projection")
        print("SEND: " + str(report))
        print("REPORT_SHA256: " + sha256(report.read_bytes()).hexdigest())
    except Exception:
        print("Split projection failed at " + stage + "; preserve outputs; do not rerun blindly", file=sys.stderr)
        return 1
    finally:
        print("DO NOT SEND: transaction CSV, action snapshot, private projection or database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
