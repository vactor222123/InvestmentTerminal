"""One-symbol Yahoo price-basis field qualification CLI."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

from investment_terminal.clients.yahoo_price_basis_client import YahooPriceBasisClient
from investment_terminal.operations.yahoo_price_basis_qualification import (
    PriceBasisQualification,
    PriceBasisRequest,
)
from investment_terminal.operations.yahoo_price_basis_provenance_report import (
    to_schema2_report,
    validate_yfinance_version,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def _utc_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD UTC date") from exc


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Qualify one Yahoo price-basis field shape without storing candles.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", type=_utc_date, required=True)
    parser.add_argument("--end", type=_utc_date, required=True, help="Exclusive UTC date")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, help="Explicit writable yfinance cache directory")
    parser.add_argument("--schema-version", type=int, choices=(1, 2), default=1)
    return parser


def main(argv: Sequence[str] | None = None, *, client=None) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)
    try:
        request = PriceBasisRequest(options.symbol, options.start, options.end)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    if client is None and options.cache_directory is None:
        parser.error("--cache-directory is required for a live Yahoo request")
    if options.output.exists():
        parser.error("output already exists; choose a new report path")
    version = None
    if options.schema_version == 2:
        try:
            version = validate_yfinance_version(yf.__version__)
        except ValueError as exc:
            parser.error(str(exc))
    schema1_result = PriceBasisQualification(
        client if client is not None else YahooPriceBasisClient(cache_directory=options.cache_directory)
    ).qualify(request)
    result = (
        to_schema2_report(schema1_result, yfinance_version=version)
        if options.schema_version == 2
        else schema1_result
    )
    write_json_atomic(options.output, result)
    print(json.dumps(result, indent=2, allow_nan=False))
    if result["status"] != "QUALIFIED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
