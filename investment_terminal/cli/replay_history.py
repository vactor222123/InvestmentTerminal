"""
Read-only command-line interface for supported historical replay modes.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

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
from investment_terminal.history.historical_replay_models import (
    HistoricalReplayRequest,
)
from investment_terminal.history.historical_replay_service import (
    HistoricalReplayService,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.history.historical_timeline_repository import (
    HistoricalTimelineRepository,
)


DEFAULT_HISTORY_ROOT = (
    Path("data")
    / "history"
)
DEFAULT_DATABASE_NAME = "history.db"

MODE_ALIASES = {
    "exact": "EXACT_ARCHIVED_PACKAGE",
    "normalized": "NORMALIZED_HISTORICAL_VIEW",
}


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay verified archived evidence or a normalized "
            "historical view without recalculating history."
        )
    )
    parser.add_argument(
        "--history-root",
        type=Path,
        default=DEFAULT_HISTORY_ROOT,
        help=(
            "History root containing archived Review Packages. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Optional History SQLite database. "
            "Default: <history-root>/history.db."
        ),
    )
    parser.add_argument(
        "--snapshot-id",
        required=True,
        help="Historical snapshot UUID.",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=tuple(
            MODE_ALIASES
        ),
        help="Replay mode: exact or normalized.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete canonical replay result as JSON.",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(
        argv
    )

    database_path = (
        options.database
        if options.database is not None
        else (
            options.history_root
            / DEFAULT_DATABASE_NAME
        )
    )

    if not database_path.is_file():
        parser.error(
            f"History database does not exist: {database_path}"
        )

    store = HistoricalSQLiteStore(
        database_path
    )

    try:
        request = HistoricalReplayRequest(
            snapshot_id=options.snapshot_id,
            mode=MODE_ALIASES[
                options.mode
            ],
        )
        result = _build_service(
            store=store,
            history_root=options.history_root,
        ).replay(
            request
        )
    except (
        FileNotFoundError,
        KeyError,
        NotImplementedError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(
            str(
                exc
            )
        )

    report = result.to_dict()

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
    *,
    store: HistoricalSQLiteStore,
    history_root: Path,
) -> HistoricalReplayService:
    return HistoricalReplayService(
        snapshot_repository=HistoricalSnapshotRepository(
            store
        ),
        import_state_repository=HistoricalImportStateRepository(
            store
        ),
        portfolio_summary_repository=HistoricalPortfolioSummaryRepository(
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
        timeline_repository=HistoricalTimelineRepository(
            store
        ),
        review_package_loader=HistoricalReviewPackageLoader(
            history_root
        ),
    )


def _print_human(
    report: dict[str, Any],
) -> None:
    print(
        "Historical replay"
    )
    print(
        f"Snapshot : {report['snapshot_id']}"
    )
    print(
        f"Mode     : {report['mode']}"
    )
    print(
        f"Schema   : {report['package_schema_version']}"
    )
    print(
        f"Evidence : {report['evidence_checksum_sha256']}"
    )

    warnings = report[
        "warnings"
    ]
    if warnings:
        print(
            "Warnings:"
        )
        for warning in warnings:
            print(
                f"- {warning}"
            )

    payload = report[
        "payload"
    ]

    if report[
        "exact_archived_evidence"
    ]:
        print(
            "Representation: verified archived Review Package"
        )
        print(
            f"Top-level keys: {', '.join(sorted(payload))}"
        )
        return

    print(
        "Representation: normalized historical SQLite projection"
    )

    state = payload.get(
        "import_state"
    )
    print(
        "Import state: "
        + (
            "-"
            if state is None
            else str(
                state.get(
                    "status",
                    "-",
                )
            )
        )
    )
    print(
        "Portfolio summary: "
        + (
            "present"
            if payload.get(
                "portfolio_summary"
            ) is not None
            else "absent"
        )
    )
    print(
        f"Holdings: {len(payload.get('holdings', []))}"
    )
    print(
        f"Recommendations: {len(payload.get('recommendations', []))}"
    )
    print(
        f"Deployment: {len(payload.get('deployment', []))}"
    )
    print(
        f"Timeline events: {len(payload.get('timeline_events', []))}"
    )


if __name__ == "__main__":
    main()
