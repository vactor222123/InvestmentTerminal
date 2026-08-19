"""CLI for one explicit Yahoo historical-candle qualification run."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.operations.yahoo_candle_qualification import (
    YahooCandleQualificationRequest,
    YahooCandleQualificationService,
    YahooCandleQualificationStatus,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "must be an ISO-8601 datetime"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must be timezone-aware")
    return parsed


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qualify one bounded Yahoo historical-candle request."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--resolution", choices=("D", "W", "M"), required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--start", type=_aware_datetime, required=True)
    parser.add_argument("--end", type=_aware_datetime, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cache-directory",
        type=Path,
        help="Explicit writable runtime directory for yfinance cache files.",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    client=None,
    clock=None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)
    if client is None and options.cache_directory is None:
        parser.error(
            "--cache-directory is required for a live Yahoo request"
        )
    result = YahooCandleQualificationService(
        client=(
            client
            if client is not None
            else YahooFinanceClient(cache_directory=options.cache_directory)
        ),
        clock=clock or (lambda: datetime.now(timezone.utc)),
    ).qualify(
        YahooCandleQualificationRequest(
            symbol=options.symbol,
            resolution=options.resolution,
            currency=options.currency,
            requested_start=options.start,
            requested_end=options.end,
        )
    )
    payload = result.to_dict()
    write_json_atomic(options.output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print("Yahoo Historical Candle Qualification")
        print(f"Status       : {result.status.value}")
        print(f"Symbol       : {result.request.symbol}")
        print(f"Candles      : {result.candle_count}")
        print(f"Duration     : {result.duration_seconds} seconds")
        print(f"Report       : {options.output}")
    if result.status is YahooCandleQualificationStatus.FAILED:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
