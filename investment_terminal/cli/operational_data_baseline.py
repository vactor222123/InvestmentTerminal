"""CLI for the read-only operational data baseline report."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.operations.operational_data_baseline import (
    OperationalDataBaselineInputs,
    OperationalDataBaselineService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect configured and populated operational data read-only."
    )
    parser.add_argument("--market-database", type=Path)
    parser.add_argument("--maintained-universe-database", type=Path)
    parser.add_argument("--current-portfolio", type=Path)
    parser.add_argument("--transaction-database", type=Path)
    parser.add_argument("--valuation-database", type=Path)
    parser.add_argument("--external-context-database", type=Path)
    parser.add_argument("--backup-root", type=Path)
    parser.add_argument("--workflow-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete machine-readable report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    options = build_argument_parser().parse_args(argv)
    report = OperationalDataBaselineService(
        inputs=OperationalDataBaselineInputs(
            market_database=options.market_database,
            maintained_universe_database=options.maintained_universe_database,
            current_portfolio=options.current_portfolio,
            transaction_database=options.transaction_database,
            valuation_database=options.valuation_database,
            external_context_database=options.external_context_database,
            backup_root=options.backup_root,
            workflow_report=options.workflow_report,
        ),
        environment=os.environ,
        clock=lambda: datetime.now(timezone.utc),
    ).build()
    payload = report.to_dict()
    if options.output is not None:
        write_json_atomic(options.output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
        return
    print("Operational Data Baseline")
    print(f"Generated at : {payload['generated_at']}")
    for provider in payload["providers"]:
        print(
            f"Provider     : {provider['provider_identity']} "
            f"{provider['state']}"
        )
    for store in payload["stores"]:
        count = store["record_count"]
        print(
            f"Store        : {store['store_identity']} "
            f"{store['state']} count={count if count is not None else 'unknown'}"
        )


if __name__ == "__main__":
    main()
