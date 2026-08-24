"""Bounded single-instrument market-data refresh command."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.services.historical_market_service import (
    HistoricalMarketService,
)
from investment_terminal.services.market_data_freshness_service import (
    MarketDataFreshnessService,
)
from investment_terminal.services.market_data_refresh_service import (
    MarketDataRefreshService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh one explicit market-data series and report freshness.",
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--resolution", required=True, choices=("D", "W", "M"))
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--checked-at", required=True, type=_aware_datetime)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--cache-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def _payload(
    options: argparse.Namespace,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, object]:
    request = {
        "symbol": options.symbol.strip().upper(),
        "resolution": options.resolution,
        "currency": options.currency.strip().upper(),
        "checked_at": options.checked_at.isoformat(),
    }
    started_at = clock()
    database = None
    try:
        database = Database(options.database)
        database.initialize()
        repository = CandleRepository(database)
        result = MarketDataRefreshService(
            freshness_service=MarketDataFreshnessService(repository=repository),
            historical_market_service=HistoricalMarketService(
                client=YahooFinanceClient(
                    cache_directory=options.cache_directory,
                ),
                repository=repository,
            ),
        ).ensure_fresh(
            symbol=request["symbol"],
            resolution=request["resolution"],
            currency=request["currency"],
            checked_at=options.checked_at,
        )
        completed_at = clock()
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "status": "SUCCESS" if result.is_ready else "NOT_READY",
            "request": request,
            "database": str(options.database.resolve()),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": (completed_at - started_at).total_seconds(),
            "result": result.to_dict(),
            "failure": None,
            "limitations": [
                "one refresh does not establish general provider reliability",
                "result does not authorize scheduling or multi-instrument refresh",
                "result does not authorize analysis or trading",
            ],
        }
    except Exception as exc:
        completed_at = clock()
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "request": request,
            "database": str(options.database.resolve()),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": (completed_at - started_at).total_seconds(),
            "result": None,
            "failure": {"type": type(exc).__name__, "reason": str(exc)},
            "limitations": ["failed refresh does not authorize downstream use"],
        }
    finally:
        if database is not None:
            database.close()


def main(argv: Sequence[str] | None = None) -> int:
    options = build_argument_parser().parse_args(argv)
    payload = _payload(options)
    write_json_atomic(options.output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
