"""
Read-only command-line interface for historical snapshot comparison.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from investment_terminal.history.historical_comparison_facts_repository import (
    HistoricalComparisonFactsRepository,
)
from investment_terminal.history.historical_deployment_repository import (
    HistoricalDeploymentRepository,
)
from investment_terminal.history.historical_holdings_repository import (
    HistoricalHoldingsRepository,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_portfolio_summary_repository import (
    HistoricalPortfolioSummaryRepository,
)
from investment_terminal.history.historical_recommendations_repository import (
    HistoricalRecommendationsRepository,
)
from investment_terminal.history.historical_snapshot_comparison_service import (
    HistoricalSnapshotComparisonService,
)
from investment_terminal.history.historical_snapshot_compatibility import (
    HistoricalSnapshotCompatibilityService,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


DEFAULT_DATABASE = (
    Path("data")
    / "history"
    / "history.db"
)
DEFAULT_SUPPORTED_PACKAGE_SCHEMAS = (
    "1.0",
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two structured historical snapshots "
            "without mutating History."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="History SQLite database. Default: %(default)s.",
    )
    parser.add_argument(
        "--earlier",
        required=True,
        help="Earlier historical snapshot UUID.",
    )
    parser.add_argument(
        "--later",
        required=True,
        help="Later historical snapshot UUID.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete canonical comparison as JSON.",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(
        argv
    )

    if not options.database.is_file():
        parser.error(
            f"History database does not exist: {options.database}"
        )

    store = HistoricalSQLiteStore(
        options.database
    )

    try:
        comparison = _build_service(
            store
        ).compare(
            earlier_snapshot_id=options.earlier,
            later_snapshot_id=options.later,
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

    report = comparison.to_dict()

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


def _build_service(
    store: HistoricalSQLiteStore,
) -> HistoricalSnapshotComparisonService:
    snapshots = HistoricalSnapshotRepository(
        store
    )

    return HistoricalSnapshotComparisonService(
        snapshot_repository=snapshots,
        import_state_repository=HistoricalImportStateRepository(
            store
        ),
        facts_repository=HistoricalComparisonFactsRepository(
            store
        ),
        summary_repository=HistoricalPortfolioSummaryRepository(
            store
        ),
        holdings_repository=HistoricalHoldingsRepository(
            store
        ),
        recommendations_repository=HistoricalRecommendationsRepository(
            store
        ),
        deployment_repository=HistoricalDeploymentRepository(
            store
        ),
        compatibility_service=HistoricalSnapshotCompatibilityService(
            supported_package_schemas=(
                DEFAULT_SUPPORTED_PACKAGE_SCHEMAS
            )
        ),
    )


def _print_human(
    report: dict[str, Any],
) -> None:
    print(
        "Historical snapshot comparison"
    )
    print(
        f"Earlier      : {report['earlier_snapshot_id']}"
    )
    print(
        f"Later        : {report['later_snapshot_id']}"
    )
    print(
        f"Compatibility: {report['compatibility_status']}"
    )

    notes = report[
        "compatibility_notes"
    ]
    if notes:
        print(
            "Compatibility notes:"
        )
        for note in notes:
            print(
                f"- {note}"
            )

    if report[
        "compatibility_status"
    ] == "INCOMPATIBLE":
        print(
            "Comparison details were not produced."
        )
        return

    summary = report[
        "portfolio_summary"
    ]
    if summary is None:
        print(
            "Portfolio summary: unavailable"
        )
    else:
        print(
            "Portfolio summary:"
        )
        _print_scalar(
            "Total value",
            summary[
                "total_value"
            ],
        )
        _print_scalar(
            "Invested value",
            summary[
                "invested_value"
            ],
        )
        _print_scalar(
            "Cash value",
            summary[
                "cash_value"
            ],
        )
        _print_scalar(
            "Monthly contribution",
            summary[
                "monthly_contribution"
            ],
        )
        if (
            summary[
                "source_status_previous"
            ]
            != summary[
                "source_status_current"
            ]
        ):
            print(
                "  Source status: "
                f"{summary['source_status_previous']} -> "
                f"{summary['source_status_current']}"
            )

    _print_change_group(
        "Holdings",
        report[
            "holdings"
        ],
        key_name="holding_key",
    )
    _print_change_group(
        "Recommendations",
        report[
            "recommendations"
        ],
        key_name="recommendation_key",
    )
    _print_change_group(
        "Deployment",
        report[
            "deployment"
        ],
        key_name="deployment_key",
    )


def _print_scalar(
    label: str,
    value: dict[str, Any],
) -> None:
    print(
        f"  {label}: "
        f"{_display_value(value['previous'])} -> "
        f"{_display_value(value['current'])} "
        f"(Δ {_display_value(value['absolute_change'])}, "
        f"{_display_percentage(value['percentage_change'])})"
    )


def _print_change_group(
    label: str,
    items: list[dict[str, Any]],
    *,
    key_name: str,
) -> None:
    counts = {
        "ADDED": 0,
        "REMOVED": 0,
        "CHANGED": 0,
        "UNCHANGED": 0,
    }

    for item in items:
        change_type = item[
            "change_type"
        ]
        if change_type in counts:
            counts[
                change_type
            ] += 1

    print(
        f"{label}: "
        f"added {counts['ADDED']}, "
        f"removed {counts['REMOVED']}, "
        f"changed {counts['CHANGED']}, "
        f"unchanged {counts['UNCHANGED']}"
    )

    for item in items:
        if item[
            "change_type"
        ] == "UNCHANGED":
            continue

        print(
            f"  {item[key_name]}: {item['change_type']}"
        )


def _display_value(
    value: object,
) -> str:
    if value is None:
        return "-"
    if isinstance(
        value,
        float,
    ):
        return f"{value:.6g}"
    return str(
        value
    )


def _display_percentage(
    value: object,
) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}%"


if __name__ == "__main__":
    main()
