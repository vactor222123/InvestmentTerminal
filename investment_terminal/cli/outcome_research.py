"""
Read-only CLI for statistically honest historical outcome research summaries.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import timezone
from pathlib import Path
from typing import Any

from investment_terminal.cli.methodology_outcome_history import (
    ELAPSED_METHODOLOGY,
    SESSION_METHODOLOGY,
    _methodology_window_calendar,
)
from investment_terminal.cli.outcome_history import (
    DEFAULT_HISTORY_DATABASE,
    DEFAULT_MARKET_DATABASE,
    _open_market_database,
    _parse_datetime,
    _positive_int,
)
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
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
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
    HistoricalOutcomeQueryService,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)
from investment_terminal.history.historical_outcome_source_import_quality import (
    HistoricalOutcomeSourceImportQualityService,
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


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize historical recommendation outcomes under an explicit "
            "research protocol with visible provenance, coverage, sample "
            "sufficiency, uncertainty, and descriptive-only claim boundaries."
        )
    )
    parser.add_argument("--history-database", type=Path, default=DEFAULT_HISTORY_DATABASE)
    parser.add_argument("--market-database", type=Path, default=DEFAULT_MARKET_DATABASE)
    parser.add_argument("--recommendation-key", required=True)
    parser.add_argument(
        "--methodology",
        choices=(ELAPSED_METHODOLOGY, SESSION_METHODOLOGY),
        required=True,
    )
    parser.add_argument("--window-value", type=_positive_int, required=True)
    parser.add_argument("--minimum-sample-size", type=_positive_int, required=True)
    parser.add_argument("--session-calendar", type=Path)
    parser.add_argument("--as-of", type=_parse_datetime, required=True)
    parser.add_argument("--resolution", default="D")
    parser.add_argument("--symbol")
    parser.add_argument("--action")
    parser.add_argument("--origin-from", type=_parse_datetime)
    parser.add_argument("--origin-to", type=_parse_datetime)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
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
        query = HistoricalOutcomeQuery(
            recommendation_key=options.recommendation_key,
            symbol=options.symbol,
            action=options.action,
            window_kind=window.kind,
            window_value=window.value,
            methodology_id=methodology.methodology_id,
            methodology_version=methodology.version,
            origin_from=options.origin_from,
            origin_to=options.origin_to,
        )
        protocol = HistoricalOutcomeResearchProtocol.descriptive_v1(
            allowed_methodology_identities=(methodology.identity_key,),
            minimum_complete_sample_size=options.minimum_sample_size,
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))

    market_database = None

    try:
        history_store = HistoricalSQLiteStore(options.history_database)
        history_service = HistoricalRecommendationHistoryService(
            snapshot_repository=HistoricalSnapshotRepository(history_store),
            recommendations_repository=HistoricalRecommendationsRepository(
                history_store
            ),
        )
        import_quality_service = HistoricalOutcomeSourceImportQualityService(
            HistoricalImportStateRepository(history_store)
        )

        market_database = _open_market_database(options.market_database)
        raw_provider = HistoricalOutcomePriceEvidenceProvider(
            CandleRepository(market_database)
        )
        selection_service = HistoricalPriceEvidenceSelectionService(raw_provider)
        methodology_evidence_service = (
            HistoricalMethodologyAwarePriceEvidenceService(selection_service)
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

        states = history_service.states_for(options.recommendation_key)
        produced = tuple(
            observation_service.observe(
                state=state,
                window=window,
                methodology=methodology,
                as_of=options.as_of,
                resolution=options.resolution,
            )
            for state in states
        )
        filtered = HistoricalOutcomeQueryService().filter(
            produced,
            query=query,
        )
        source_import_quality = import_quality_service.assess(
            produced
        )
        research_results = HistoricalOutcomeResearchService().analyze(
            results=filtered,
            protocol=protocol,
            population_query=query,
            source_observation_count=len(produced),
            source_results=produced,
            source_import_quality=source_import_quality,
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
        "command": "historical_outcome_research",
        "protocol": protocol.to_dict(),
        "recommendation_key": str(
            options.recommendation_key
        ).strip().upper(),
        "methodology": methodology.to_dict(),
        "window": window.to_dict(),
        "session_calendar": (
            None
            if options.methodology == ELAPSED_METHODOLOGY
            else calendar.identity.to_dict()
        ),
        "as_of": options.as_of.astimezone(timezone.utc).isoformat(),
        "resolution": str(options.resolution).strip().upper(),
        "query": query.to_dict(),
        "produced_observation_count": len(produced),
        "candidate_count": len(filtered),
        "cohort_count": len(research_results),
        "cohorts": [result.to_dict() for result in research_results],
    }

    if options.json:
        print(json.dumps(report, indent=2, allow_nan=False))
        return

    _print_human(report)


def _print_human(report: dict[str, Any]) -> None:
    print("Historical outcome research")
    print(f"Recommendation : {report['recommendation_key']}")
    print("Protocol       : " f"{report['protocol']['identity_key']}")
    print("Methodology    : " f"{report['methodology']['identity_key']}")
    print(
        "Window         : "
        f"{report['window']['value']} "
        f"{report['window']['kind']}"
    )
    print(f"As of          : {report['as_of']}")
    print(f"Resolution     : {report['resolution']}")
    print(
        "Candidates     : "
        f"{report['candidate_count']} "
        f"(from {report['produced_observation_count']} produced)"
    )
    print(f"Cohorts        : {report['cohort_count']}")

    for index, cohort in enumerate(report["cohorts"], start=1):
        frame = cohort["population_frame"]
        accounting = cohort.get("selection_accounting")
        completeness = cohort.get("population_completeness")
        import_quality = cohort.get("source_import_quality")
        coverage = cohort["coverage"]
        sample = cohort["sample_assessment"]
        claims = cohort["claim_assessment"]
        population = cohort["population"]
        descriptive = cohort["descriptive_summary"]
        uncertainty = cohort["uncertainty"]

        print("")
        print(f"Cohort {index}")
        print(
            "  Identity     : "
            f"{cohort['cohort']['identity_key']}"
        )
        if import_quality is not None:
            fraction = import_quality["imported_fraction"]
            fraction_text = (
                "n/a"
                if fraction is None
                else f"{fraction:.2%}"
            )
            print(
                "  Import       : "
                f"{import_quality['status']} / "
                f"{import_quality['imported_snapshot_count']}/"
                f"{import_quality['unique_snapshot_count']} imported "
                f"({fraction_text})"
            )
            if import_quality["warning"] is not None:
                print(
                    "  I-warning    : "
                    f"{import_quality['warning']}"
                )
        print(
            "  Frame        : "
            f"{frame['selected_candidate_count']}/"
            f"{frame['source_observation_count']} selected "
            f"({frame['selection_fraction']:.2%}); "
            f"excluded={frame['excluded_by_selection_count']}"
        )
        if accounting is not None:
            if accounting["reason_counts"]:
                reasons = ", ".join(
                    f"{item['reason']}={item['count']}"
                    for item in accounting["reason_counts"]
                )
            else:
                reasons = "none"
            print(
                "  Selection    : "
                f"{reasons}; "
                f"reason_failures={accounting['total_reason_failures']}"
            )
        if completeness is not None:
            print(
                "  Completeness : "
                f"{completeness['status']} / "
                f"internal={completeness['internal_continuity_status']}"
            )
            print(
                "  C-warning    : "
                f"{completeness['warning']}"
            )
        print(
            "  Population   : "
            f"{population['selection_basis']}"
            + (" (prefiltered)" if population["prefiltered"] else "")
        )
        print(
            "  Coverage     : "
            f"{coverage['eligible_count']}/"
            f"{coverage['candidate_count']} eligible "
            f"({coverage['coverage_fraction']:.2%})"
        )
        print(
            "  Statuses     : "
            f"COMPLETE={coverage['complete_count']}, "
            f"PARTIAL={coverage['partial_count']}, "
            f"UNAVAILABLE={coverage['unavailable_count']}, "
            f"NOT_MATURE={coverage['not_mature_count']}"
        )
        print(
            "  Sample       : "
            f"{sample['status']} "
            f"({sample['eligible_sample_size']}/"
            f"{sample['minimum_required_sample_size']}, "
            f"shortfall={sample['shortfall']})"
        )

        if descriptive is None:
            print("  Movement     : unavailable")
        else:
            print(
                "  Movement     : "
                f"mean={descriptive['mean_price_change_fraction']:.6g}, "
                f"median={descriptive['median_price_change_fraction']:.6g}, "
                f"n={descriptive['count']}"
            )

        if uncertainty is None:
            print("  Uncertainty  : unavailable")
        else:
            sem = uncertainty["standard_error_of_mean"]
            print(
                "  Uncertainty  : "
                + (
                    "standard error unavailable"
                    if sem is None
                    else f"SEM={sem:.6g}"
                )
            )
            if uncertainty["warning"] is not None:
                print(
                    "  U-warning    : "
                    f"{uncertainty['warning']}"
                )

        print(
            "  Claims       : "
            f"{claims['claim_policy']} / "
            f"{claims['sample_status']}"
        )
        print(
            "  Warning      : "
            f"{claims['warning']}"
        )
        for warning in population["warnings"]:
            print(
                "  Population   : "
                f"{warning}"
            )


if __name__ == "__main__":
    main()
