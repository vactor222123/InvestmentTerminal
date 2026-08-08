"""
Read-only command-line inspection for structured historical data.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
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


DEFAULT_DATABASE = (
    Path("data")
    / "history"
    / "history.db"
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect historical snapshots and timeline events "
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
        "--json",
        action="store_true",
        help="Print complete JSON output.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    snapshots = subparsers.add_parser(
        "snapshots",
        help="List historical snapshots.",
    )
    snapshots.add_argument(
        "--package-id",
        default=None,
        help="Filter by package ID.",
    )
    snapshots.add_argument(
        "--start",
        type=_parse_datetime,
        default=None,
        help="Inclusive generated-at lower bound (ISO-8601 with timezone).",
    )
    snapshots.add_argument(
        "--end",
        type=_parse_datetime,
        default=None,
        help="Inclusive generated-at upper bound (ISO-8601 with timezone).",
    )
    snapshots.add_argument(
        "--latest",
        action="store_true",
        help="Return only the latest snapshot.",
    )

    timeline = subparsers.add_parser(
        "timeline",
        help="List historical timeline events.",
    )
    timeline.add_argument(
        "--snapshot-id",
        default=None,
        help="Filter events by snapshot UUID.",
    )
    timeline.add_argument(
        "--event-type",
        default=None,
        help="Filter events by event type.",
    )
    timeline.add_argument(
        "--subject",
        default=None,
        help="Filter events by subject key.",
    )
    timeline.add_argument(
        "--start",
        type=_parse_datetime,
        default=None,
        help="Inclusive occurrence-time lower bound.",
    )
    timeline.add_argument(
        "--end",
        type=_parse_datetime,
        default=None,
        help="Inclusive occurrence-time upper bound.",
    )
    timeline.add_argument(
        "--latest",
        type=_positive_int,
        default=None,
        metavar="N",
        help="Return the latest N events.",
    )

    show = subparsers.add_parser(
        "show",
        help="Show one snapshot, import state, and its timeline.",
    )
    show.add_argument(
        "--snapshot-id",
        required=True,
        help="Snapshot UUID to inspect.",
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
    snapshots = HistoricalSnapshotRepository(
        store
    )
    timeline = HistoricalTimelineRepository(
        store
    )
    states = HistoricalImportStateRepository(
        store
    )

    try:
        if options.command == "snapshots":
            report = _query_snapshots(
                options,
                snapshots,
            )
        elif options.command == "timeline":
            report = _query_timeline(
                options,
                timeline,
            )
        elif options.command == "show":
            report = _show_snapshot(
                options,
                snapshots,
                states,
                timeline,
            )
        else:
            raise RuntimeError(
                f"Unhandled query command: {options.command}"
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
        options.command,
        report,
    )


def _query_snapshots(
    options: argparse.Namespace,
    repository: HistoricalSnapshotRepository,
) -> dict[str, Any]:
    if options.latest:
        if any(
            value is not None
            for value in (
                options.package_id,
                options.start,
                options.end,
            )
        ):
            raise ValueError(
                "--latest cannot be combined with snapshot filters"
            )

        latest = repository.latest()
        items = (
            ()
            if latest is None
            else (
                latest,
            )
        )
    elif options.package_id is not None:
        if options.start is not None or options.end is not None:
            raise ValueError(
                "--package-id cannot be combined with --start or --end"
            )

        items = repository.find_by_package_id(
            options.package_id
        )
    elif options.start is not None or options.end is not None:
        if options.start is None or options.end is None:
            raise ValueError(
                "--start and --end must be provided together"
            )

        items = repository.find_generated_between(
            start=options.start,
            end=options.end,
        )
    else:
        items = repository.list_all()

    return {
        "command": "snapshots",
        "count": len(
            items
        ),
        "snapshots": [
            item.to_dict()
            for item in items
        ],
    }


def _query_timeline(
    options: argparse.Namespace,
    repository: HistoricalTimelineRepository,
) -> dict[str, Any]:
    filters = [
        options.snapshot_id is not None,
        options.event_type is not None,
        options.subject is not None,
        options.start is not None or options.end is not None,
        options.latest is not None,
    ]

    if sum(
        filters
    ) > 1:
        raise ValueError(
            "timeline accepts only one filter mode at a time"
        )

    if options.snapshot_id is not None:
        items = repository.list_for_snapshot(
            options.snapshot_id
        )
    elif options.event_type is not None:
        items = repository.find_by_type(
            options.event_type
        )
    elif options.subject is not None:
        items = repository.find_by_subject(
            options.subject
        )
    elif options.start is not None or options.end is not None:
        if options.start is None or options.end is None:
            raise ValueError(
                "--start and --end must be provided together"
            )

        items = repository.find_between(
            start=options.start,
            end=options.end,
        )
    elif options.latest is not None:
        items = repository.latest(
            options.latest
        )
    else:
        items = repository.latest(
            100
        )

    return {
        "command": "timeline",
        "count": len(
            items
        ),
        "events": [
            item.to_dict()
            for item in items
        ],
    }


def _show_snapshot(
    options: argparse.Namespace,
    snapshots: HistoricalSnapshotRepository,
    states: HistoricalImportStateRepository,
    timeline: HistoricalTimelineRepository,
) -> dict[str, Any]:
    snapshot = snapshots.require(
        options.snapshot_id
    )
    state = states.get(
        snapshot.snapshot_id
    )
    events = timeline.list_for_snapshot(
        snapshot.snapshot_id
    )
    previous = snapshots.previous_before(
        snapshot.snapshot_id
    )
    next_snapshot = snapshots.next_after(
        snapshot.snapshot_id
    )

    return {
        "command": "show",
        "snapshot": snapshot.to_dict(),
        "import_state": (
            None
            if state is None
            else state.to_dict()
        ),
        "previous_snapshot_id": (
            None
            if previous is None
            else previous.snapshot_id
        ),
        "next_snapshot_id": (
            None
            if next_snapshot is None
            else next_snapshot.snapshot_id
        ),
        "timeline_events": [
            event.to_dict()
            for event in events
        ],
    }


def _print_human(
    command: str,
    report: dict[str, Any],
) -> None:
    if command == "snapshots":
        print(
            f"Historical snapshots: {report['count']}"
        )
        for snapshot in report[
            "snapshots"
        ]:
            print(
                f"{snapshot['generated_at']}  "
                f"{snapshot['snapshot_id']}  "
                f"{snapshot['package_id'] or '-'}"
            )
        return

    if command == "timeline":
        print(
            f"Historical timeline events: {report['count']}"
        )
        for event in report[
            "events"
        ]:
            print(
                f"{event['occurred_at']}  "
                f"{event['event_type']}  "
                f"{event['subject_key'] or '-'}  "
                f"{event['snapshot_id']}"
            )
        return

    snapshot = report[
        "snapshot"
    ]
    print(
        f"Snapshot: {snapshot['snapshot_id']}"
    )
    print(
        f"Generated: {snapshot['generated_at']}"
    )
    print(
        f"Package: {snapshot['package_id'] or '-'}"
    )
    state = report[
        "import_state"
    ]
    print(
        "Import state: "
        + (
            "UNAVAILABLE"
            if state is None
            else state[
                "status"
            ]
        )
    )
    print(
        f"Timeline events: {len(report['timeline_events'])}"
    )
    print(
        f"Previous: {report['previous_snapshot_id'] or '-'}"
    )
    print(
        f"Next: {report['next_snapshot_id'] or '-'}"
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
