"""
Read-only command-line interface for historical recommendation outcomes.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_aggregation import (
    HistoricalOutcomeAggregator,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)
from investment_terminal.history.historical_outcome_observation_service import (
    HistoricalOutcomeObservationService,
)
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
)
from investment_terminal.history.historical_recommendation_history_service import (
    HistoricalRecommendationHistoryService,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


DEFAULT_HISTORY_DATABASE = (
    Path("data")
    / "history"
    / "history.db"
)
DEFAULT_MARKET_DATABASE = Path(
    Settings.DATABASE_PATH
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Observe historical recommendation outcomes from local "
            "History and exact persisted candle evidence."
        )
    )
    parser.add_argument(
        "--history-database",
        type=Path,
        default=DEFAULT_HISTORY_DATABASE,
        help="History SQLite database. Default: %(default)s.",
    )
    parser.add_argument(
        "--market-database",
        type=Path,
        default=DEFAULT_MARKET_DATABASE,
        help="Local market SQLite database. Default: %(default)s.",
    )
    parser.add_argument(
        "--recommendation-key",
        required=True,
        help="Stable historical recommendation key.",
    )
    parser.add_argument(
        "--window-days",
        type=_positive_int,
        required=True,
        help="Observation window as absolute elapsed 24-hour days.",
    )
    parser.add_argument(
        "--as-of",
        type=_parse_datetime,
        required=True,
        help="Observation cutoff as timezone-aware ISO-8601.",
    )
    parser.add_argument(
        "--resolution",
        default="D",
        help="Exact local candle resolution. Default: %(default)s.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print complete JSON output.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(
        argv
    )

    if not options.history_database.is_file():
        parser.error(
            "History database does not exist: "
            f"{options.history_database}"
        )
    if not options.market_database.is_file():
        parser.error(
            "Market database does not exist: "
            f"{options.market_database}"
        )

    market_database: Database | None = None

    try:
        history_store = HistoricalSQLiteStore(
            options.history_database
        )
        history_service = HistoricalRecommendationHistoryService(
            snapshot_repository=HistoricalSnapshotRepository(
                history_store
            ),
            recommendations_repository=HistoricalRecommendationsRepository(
                history_store
            ),
        )

        market_database = _open_market_database(
            options.market_database
        )
        observation_service = HistoricalOutcomeObservationService(
            window_policy=HistoricalObservationWindowPolicy(),
            price_provider=HistoricalOutcomePriceEvidenceProvider(
                CandleRepository(
                    market_database
                )
            ),
            calculator=HistoricalRecommendationOutcomeCalculator(),
        )

        window = HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=options.window_days,
        )
        states = history_service.states_for(
            options.recommendation_key
        )
        results = tuple(
            observation_service.observe(
                state=state,
                window=window,
                as_of=options.as_of,
                resolution=options.resolution,
            )
            for state in states
        )
        summary = HistoricalOutcomeAggregator().summarize(
            results
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(
            str(
                exc
            )
        )
    finally:
        if market_database is not None:
            market_database.close()

    report = {
        "command": "historical_outcomes",
        "recommendation_key": options.recommendation_key,
        "window": window.to_dict(),
        "as_of": options.as_of.astimezone(
            timezone.utc
        ).isoformat(),
        "resolution": str(
            options.resolution
        ).strip().upper(),
        "count": len(
            results
        ),
        "observations": [
            result.to_dict()
            for result in results
        ],
        "summary": summary.to_dict(),
    }

    if options.json:
        print(
            json.dumps(
                report,
                indent=2,
                allow_nan=False,
            )
        )
        return

    _print_human(
        report
    )


def _open_market_database(
    path: Path,
) -> Database:
    """
    Open the legacy market Database at an explicit path without retaining a
    global Settings mutation after construction.
    """
    previous = Settings.DATABASE_PATH
    Settings.DATABASE_PATH = path
    try:
        return Database()
    finally:
        Settings.DATABASE_PATH = previous


def _print_human(
    report: dict[str, Any],
) -> None:
    print(
        "Historical recommendation outcomes"
    )
    print(
        f"Recommendation: {report['recommendation_key']}"
    )
    print(
        "Window        : "
        f"{report['window']['value']} elapsed day(s)"
    )
    print(
        f"As of         : {report['as_of']}"
    )
    print(
        f"Resolution    : {report['resolution']}"
    )
    print(
        f"Observations  : {report['count']}"
    )

    summary = report[
        "summary"
    ]
    print(
        "Coverage      : "
        f"{summary['complete_count']}/{summary['total_count']} COMPLETE"
    )
    print(
        "Statuses      : "
        f"partial {summary['partial_count']}, "
        f"unavailable {summary['unavailable_count']}, "
        f"not mature {summary['not_mature_count']}"
    )

    if summary[
        "mean_price_change_fraction"
    ] is None:
        print(
            "Raw movement : unavailable"
        )
    else:
        print(
            "Raw movement : "
            f"mean {summary['mean_price_change_fraction']:.6g}, "
            f"median {summary['median_price_change_fraction']:.6g}"
        )

    print(
        "Note          : raw close-price movement only; "
        "not portfolio performance or evidence of causality"
    )

    for item in report[
        "observations"
    ]:
        observation = item[
            "observation"
        ]
        outcome = item[
            "outcome"
        ]
        movement = (
            "-"
            if outcome is None
            else f"{outcome['price_change_fraction']:.6g}"
        )
        print(
            f"{observation['origin_at']}  "
            f"{observation['status']}  "
            f"{observation['action'] or '-'}  "
            f"{observation['symbol'] or '-'}  "
            f"{movement}"
        )


def _parse_datetime(
    value: str,
) -> datetime:
    normalized = (
        value[:-1]
        + "+00:00"
        if value.endswith(
            "Z"
        )
        else value
    )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "datetime must be valid ISO-8601"
        ) from exc

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise argparse.ArgumentTypeError(
            "datetime must include a timezone offset"
        )

    return parsed


def _positive_int(
    value: str,
) -> int:
    try:
        parsed = int(
            value
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        ) from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


if __name__ == "__main__":
    main()
