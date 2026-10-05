"""One-public-ETF EODHD demo field-shape qualification CLI."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from investment_terminal.clients.eodhd_demo_price_client import EodhdDemoPriceClient
from investment_terminal.operations.eodhd_demo_price_qualification import (
    DemoPriceRequest,
    EodhdDemoPriceQualification,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def _date(value: str) -> date:
    try:
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD date") from exc


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Qualify one public VTI.US EODHD demo response without storing prices.")
    parser.add_argument("--start", type=_date, required=True)
    parser.add_argument("--end", type=_date, required=True, help="Exclusive date")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None, *, client=None) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)
    try:
        request = DemoPriceRequest(options.start, options.end)
    except ValueError as exc:
        parser.error(str(exc))
    if options.output.exists():
        parser.error("output already exists; choose a new report path")
    report = EodhdDemoPriceQualification(
        client if client is not None else EodhdDemoPriceClient()
    ).qualify(request)
    write_json_atomic(options.output, report)
    print(json.dumps(report, indent=2, allow_nan=False))
    if report["status"] != "QUALIFIED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
