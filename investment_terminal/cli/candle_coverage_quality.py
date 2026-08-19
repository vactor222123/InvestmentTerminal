"""Evaluate persisted daily candles against explicit calendar evidence."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.cli.methodology_outcome_history import (
    _load_session_calendar,
)
from investment_terminal.cli.outcome_history import _parse_datetime
from investment_terminal.database.database import Database
from investment_terminal.history.candle_coverage_quality import (
    CandleCoverageQualityService,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.atomic_write import write_json_atomic


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure local daily candles against explicit sessions."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--session-calendar", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--resolution", default="D", choices=("D",))
    parser.add_argument("--start", required=True, type=_parse_datetime)
    parser.add_argument("--end", required=True, type=_parse_datetime)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    options = build_argument_parser().parse_args(argv)
    if not options.database.is_file():
        raise ValueError(f"Database does not exist: {options.database}")
    calendar = _load_session_calendar(options.session_calendar)
    database = Database(options.database)
    try:
        candles = CandleRepository(database).get_range(
            options.symbol,
            options.resolution,
            options.start,
            options.end,
        )
        result = CandleCoverageQualityService().evaluate(
            symbol=options.symbol,
            resolution=options.resolution,
            start_at=options.start,
            end_at=options.end,
            candles=candles,
            calendar=calendar,
        )
        write_json_atomic(options.output, result.to_dict())
    finally:
        database.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
