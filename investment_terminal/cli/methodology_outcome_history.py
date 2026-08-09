"""
Read-only methodology-aware CLI for historical recommendation outcomes.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from investment_terminal.cli.outcome_history import (
    DEFAULT_HISTORY_DATABASE,
    DEFAULT_MARKET_DATABASE,
    _open_market_database,
    _parse_datetime,
    _positive_int,
)
from investment_terminal.database.database import Database
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
)
from investment_terminal.history.historical_local_session_calendar import (
    HistoricalLocalSessionCalendar,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
    HistoricalSessionCalendarIdentity,
)
from investment_terminal.history.historical_methodology_aware_aggregation import (
    HistoricalMethodologyOutcomeAggregator,
)
from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationService,
)
from investment_terminal.history.historical_methodology_aware_price_evidence import (
    HistoricalMethodologyAwarePriceEvidenceService,
)
from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
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
from investment_terminal.history.historical_trading_session_window import (
    HistoricalTradingSessionWindowPolicy,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


ELAPSED_METHODOLOGY = "ELAPSED_DAYS_EXACT_CLOSE"
SESSION_METHODOLOGY = "TRADING_SESSIONS_EXACT_CLOSE"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Observe historical recommendation outcomes through an explicit "
            "versioned methodology using only local persisted evidence."
        )
    )
    parser.add_argument(
        "--history-database",
        type=Path,
        default=DEFAULT_HISTORY_DATABASE,
    )
    parser.add_argument(
        "--market-database",
        type=Path,
        default=DEFAULT_MARKET_DATABASE,
    )
    parser.add_argument(
        "--recommendation-key",
        required=True,
    )
    parser.add_argument(
        "--methodology",
        choices=(
            ELAPSED_METHODOLOGY,
            SESSION_METHODOLOGY,
        ),
        required=True,
    )
    parser.add_argument(
        "--window-value",
        type=_positive_int,
        required=True,
        help=(
            "Elapsed days for ELAPSED_DAYS_EXACT_CLOSE or explicit trading "
            "sessions for TRADING_SESSIONS_EXACT_CLOSE."
        ),
    )
    parser.add_argument(
        "--session-calendar",
        type=Path,
        help=(
            "Local JSON session calendar. Required only for "
            "TRADING_SESSIONS_EXACT_CLOSE."
        ),
    )
    parser.add_argument(
        "--as-of",
        type=_parse_datetime,
        required=True,
    )
    parser.add_argument(
        "--resolution",
        default="D",
    )
    parser.add_argument(
        "--json",
        action="store_true",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

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

    try:
        methodology, window, calendar = _methodology_window_calendar(
            methodology_name=options.methodology,
            window_value=options.window_value,
            session_calendar_path=options.session_calendar,
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))

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
        raw_provider = HistoricalOutcomePriceEvidenceProvider(
            CandleRepository(
                market_database
            )
        )
        selection_service = HistoricalPriceEvidenceSelectionService(
            raw_provider
        )
        methodology_evidence_service = (
            HistoricalMethodologyAwarePriceEvidenceService(
                selection_service
            )
        )
        observation_service = HistoricalMethodologyAwareObservationService(
            elapsed_window_policy=HistoricalObservationWindowPolicy(),
            trading_session_window_policy=HistoricalTradingSessionWindowPolicy(
                calendar
            ),
            selection_service=selection_service,
            methodology_evidence_service=methodology_evidence_service,
            calculator=HistoricalRecommendationOutcomeCalculator(),
        )

        states = history_service.states_for(
            options.recommendation_key
        )
        results = tuple(
            observation_service.observe(
                state=state,
                window=window,
                methodology=methodology,
                as_of=options.as_of,
                resolution=options.resolution,
            )
            for state in states
        )
        summary = (
            None
            if not results
            else HistoricalMethodologyOutcomeAggregator().summarize_one(
                results
            )
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(str(exc))
    finally:
        if market_database is not None:
            market_database.close()

    report = {
        "command": "methodology_historical_outcomes",
        "recommendation_key": options.recommendation_key,
        "methodology": methodology.to_dict(),
        "window": window.to_dict(),
        "session_calendar": (
            None
            if options.methodology == ELAPSED_METHODOLOGY
            else calendar.identity.to_dict()
        ),
        "as_of": options.as_of.astimezone(
            timezone.utc
        ).isoformat(),
        "resolution": str(
            options.resolution
        ).strip().upper(),
        "count": len(results),
        "observations": [
            result.to_dict()
            for result in results
        ],
        "summary": (
            None
            if summary is None
            else summary.to_dict()
        ),
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

    _print_human(report)


def _methodology_window_calendar(
    *,
    methodology_name: str,
    window_value: int,
    session_calendar_path: Path | None,
) -> tuple[
    HistoricalOutcomeMethodology,
    HistoricalObservationWindow,
    HistoricalLocalSessionCalendar,
]:
    if methodology_name == ELAPSED_METHODOLOGY:
        if session_calendar_path is not None:
            raise ValueError(
                "--session-calendar is not used by "
                "ELAPSED_DAYS_EXACT_CLOSE"
            )
        methodology = (
            HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
        )
        window = HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=window_value,
        )
        calendar = HistoricalLocalSessionCalendar(
            identity=HistoricalSessionCalendarIdentity(
                calendar_id="UNUSED",
                version=1,
                timezone="UTC",
                source="CLI_UNUSED_SESSION_CALENDAR",
            ),
            sessions=(),
        )
        return methodology, window, calendar

    if methodology_name == SESSION_METHODOLOGY:
        if session_calendar_path is None:
            raise ValueError(
                "--session-calendar is required by "
                "TRADING_SESSIONS_EXACT_CLOSE"
            )
        calendar = _load_session_calendar(
            session_calendar_path
        )
        methodology = HistoricalOutcomeMethodology(
            methodology_id=SESSION_METHODOLOGY,
            version=1,
            window_kind="TRADING_SESSIONS",
            endpoint_policy=HistoricalEndpointPolicy(
                policy_id="TRADING_SESSION_CLOSE",
                version=1,
            ),
            evidence_selection_policy=(
                HistoricalPriceEvidenceSelectionService.session_close_exact_v1()
            ),
        )
        window = HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=window_value,
        )
        return methodology, window, calendar

    raise ValueError(
        f"unsupported methodology: {methodology_name}"
    )


def _load_session_calendar(
    path: Path,
) -> HistoricalLocalSessionCalendar:
    if not path.is_file():
        raise ValueError(
            f"Session calendar does not exist: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(payload, dict):
        raise TypeError(
            "session calendar root must be an object"
        )

    calendar_payload = payload[
        "calendar"
    ]
    sessions_payload = payload[
        "sessions"
    ]
    if not isinstance(calendar_payload, dict):
        raise TypeError(
            "calendar must be an object"
        )
    if not isinstance(sessions_payload, list):
        raise TypeError(
            "sessions must be an array"
        )

    identity = HistoricalSessionCalendarIdentity(
        calendar_id=calendar_payload[
            "calendar_id"
        ],
        version=calendar_payload[
            "version"
        ],
        timezone=calendar_payload[
            "timezone"
        ],
        source=calendar_payload[
            "source"
        ],
    )

    sessions = tuple(
        _parse_session(
            item,
            identity=identity,
        )
        for item in sessions_payload
    )
    return HistoricalLocalSessionCalendar(
        identity=identity,
        sessions=sessions,
    )


def _parse_session(
    payload: object,
    *,
    identity: HistoricalSessionCalendarIdentity,
) -> HistoricalMarketSession:
    if not isinstance(payload, dict):
        raise TypeError(
            "each session must be an object"
        )

    opens_at = _parse_required_datetime(
        payload[
            "opens_at"
        ],
        field_name="opens_at",
    )
    closes_at = _parse_required_datetime(
        payload[
            "closes_at"
        ],
        field_name="closes_at",
    )

    try:
        session_date = date.fromisoformat(
            str(
                payload[
                    "session_date"
                ]
            )
        )
    except ValueError as exc:
        raise ValueError(
            "session_date must be ISO-8601 YYYY-MM-DD"
        ) from exc

    return HistoricalMarketSession(
        session_key=payload[
            "session_key"
        ],
        session_date=session_date,
        opens_at=opens_at,
        closes_at=closes_at,
        calendar=identity,
    )


def _parse_required_datetime(
    value: object,
    *,
    field_name: str,
) -> datetime:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string"
        )
    try:
        return _parse_datetime(
            value
        )
    except argparse.ArgumentTypeError as exc:
        raise ValueError(
            f"{field_name}: {exc}"
        ) from exc


def _print_human(
    report: dict[str, Any],
) -> None:
    methodology = report[
        "methodology"
    ]
    print(
        "Methodology-aware historical outcomes"
    )
    print(
        f"Recommendation : {report['recommendation_key']}"
    )
    print(
        "Methodology    : "
        f"{methodology['identity_key']}"
    )
    print(
        "Window         : "
        f"{report['window']['value']} "
        f"{report['window']['kind']}"
    )
    print(
        "Endpoint policy: "
        f"{methodology['endpoint_policy']['identity_key']}"
    )
    print(
        "Evidence policy: "
        f"{methodology['evidence_selection_policy']['identity_key']}"
    )

    if report[
        "session_calendar"
    ] is not None:
        calendar = report[
            "session_calendar"
        ]
        print(
            "Calendar       : "
            f"{calendar['identity_key']} "
            f"({calendar['source']})"
        )

    print(
        f"As of          : {report['as_of']}"
    )
    print(
        f"Resolution     : {report['resolution']}"
    )
    print(
        f"Observations   : {report['count']}"
    )

    summary = report[
        "summary"
    ]
    if summary is not None:
        print(
            "Coverage       : "
            f"{summary['complete_count']}/"
            f"{summary['total_count']} COMPLETE"
        )
        if summary[
            "mean_price_change_fraction"
        ] is None:
            print(
                "Raw movement  : unavailable"
            )
        else:
            print(
                "Raw movement  : "
                f"mean {summary['mean_price_change_fraction']:.6g}, "
                f"median {summary['median_price_change_fraction']:.6g}"
            )

    print(
        "Note           : raw close-price movement only; "
        "not portfolio performance, recommendation effectiveness, "
        "confidence calibration, or causality"
    )


if __name__ == "__main__":
    main()
