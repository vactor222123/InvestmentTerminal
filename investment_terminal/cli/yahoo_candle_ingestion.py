"""Bounded Yahoo historical-candle ingestion command."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)
from investment_terminal.services.historical_market_service import (
    HistoricalMarketService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must be timezone-aware")
    return parsed


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist one explicit bounded Yahoo candle request.",
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument(
        "--resolution",
        required=True,
        choices=("D", "W", "M"),
    )
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--start", required=True, type=_aware_datetime)
    parser.add_argument("--end", required=True, type=_aware_datetime)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--cache-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def _payload(options: argparse.Namespace) -> dict[str, object]:
    request = {
        "symbol": options.symbol.strip().upper(),
        "resolution": options.resolution,
        "currency": options.currency.strip().upper(),
        "start": options.start.isoformat(),
        "end": options.end.isoformat(),
    }
    database = None
    try:
        if options.start >= options.end:
            raise ValueError("start must be earlier than end")
        database = Database(options.database)
        database.initialize()
        result = HistoricalMarketService(
            client=YahooFinanceClient(
                cache_directory=options.cache_directory,
            ),
            repository=CandleRepository(database),
        ).import_candles(
            symbol=request["symbol"],
            resolution=request["resolution"],
            start=options.start,
            end=options.end,
            currency=request["currency"],
        )
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "status": "SUCCESS" if result.downloaded else "EMPTY",
            "request": request,
            "database": str(options.database.resolve()),
            "downloaded": result.downloaded,
            "inserted": result.inserted,
            "duplicates": result.duplicates,
            "stored_total": result.stored_total,
            "failure": None,
            "limitations": [
                "one bounded ingestion does not establish general provider "
                "reliability",
                "result does not establish approximately 20-year coverage",
                "result does not authorize bulk ingestion, analysis, or "
                "trading",
            ],
        }
    except Exception as exc:
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "request": request,
            "database": str(options.database.resolve()),
            "downloaded": None,
            "inserted": None,
            "duplicates": None,
            "stored_total": None,
            "failure": {"type": type(exc).__name__, "reason": str(exc)},
            "limitations": ["failed ingestion does not authorize downstream use"],
        }
    finally:
        if database is not None:
            database.close()


def main(argv: Sequence[str] | None = None) -> int:
    options = build_argument_parser().parse_args(argv)
    payload = _payload(options)
    write_json_atomic(options.output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if payload["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
