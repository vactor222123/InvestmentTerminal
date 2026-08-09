"""
Read-only command-line inspection for the Knowledge Domain.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from investment_terminal.knowledge.comparison import (
    KnowledgeTemporalComparisonService,
)
from investment_terminal.knowledge.query_service import (
    KnowledgeQueryService,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


DEFAULT_DATABASE = (
    Path("data")
    / "knowledge"
    / "knowledge.db"
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect versioned Knowledge records without mutating Knowledge."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Knowledge SQLite database. Default: %(default)s.",
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

    subparsers.add_parser(
        "list",
        help="List all Knowledge records.",
    )

    show = subparsers.add_parser(
        "show",
        help="Show one exact Knowledge version.",
    )
    show.add_argument(
        "--knowledge-id",
        required=True,
    )
    show.add_argument(
        "--version",
        type=_positive_int,
        required=True,
    )

    subject = subparsers.add_parser(
        "subject",
        help="List all Knowledge records for one subject.",
    )
    subject.add_argument(
        "--subject",
        required=True,
    )

    valid = subparsers.add_parser(
        "valid",
        help="List Knowledge records valid at an exact instant.",
    )
    valid.add_argument(
        "--subject",
        required=True,
    )
    valid.add_argument(
        "--at",
        type=_parse_datetime,
        required=True,
    )

    latest = subparsers.add_parser(
        "latest",
        help="Show the deterministic latest Knowledge record for a subject.",
    )
    latest.add_argument(
        "--subject",
        required=True,
    )

    compare = subparsers.add_parser(
        "compare",
        help="Compare two versions of the same knowledge identity.",
    )
    compare.add_argument(
        "--knowledge-id",
        required=True,
    )
    compare.add_argument(
        "--first-version",
        type=_positive_int,
        required=True,
    )
    compare.add_argument(
        "--second-version",
        type=_positive_int,
        required=True,
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
            f"Knowledge database does not exist: {options.database}"
        )

    repository = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            options.database
        )
    )
    query = KnowledgeQueryService(
        repository=repository
    )
    comparison = KnowledgeTemporalComparisonService()

    try:
        report = _build_report(
            options,
            query=query,
            comparison=comparison,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(
            str(exc)
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


def _build_report(
    options: argparse.Namespace,
    *,
    query: KnowledgeQueryService,
    comparison: KnowledgeTemporalComparisonService,
) -> dict[str, Any]:
    if options.command == "list":
        items = query.list_all()
        return {
            "command": "list",
            "count": len(items),
            "records": [
                item.to_dict()
                for item in items
            ],
        }

    if options.command == "show":
        item = query.require(
            options.knowledge_id,
            options.version,
        )
        return {
            "command": "show",
            "record": item.to_dict(),
        }

    if options.command == "subject":
        items = query.find_by_subject(
            options.subject
        )
        return {
            "command": "subject",
            "subject": options.subject,
            "count": len(items),
            "records": [
                item.to_dict()
                for item in items
            ],
        }

    if options.command == "valid":
        items = query.find_valid_at(
            options.subject,
            at=options.at,
        )
        return {
            "command": "valid",
            "subject": options.subject,
            "at": options.at.isoformat(),
            "count": len(items),
            "records": [
                item.to_dict()
                for item in items
            ],
        }

    if options.command == "latest":
        item = query.latest_for_subject(
            options.subject
        )
        return {
            "command": "latest",
            "subject": options.subject,
            "record": (
                None
                if item is None
                else item.to_dict()
            ),
        }

    if options.command == "compare":
        first = query.require(
            options.knowledge_id,
            options.first_version,
        )
        second = query.require(
            options.knowledge_id,
            options.second_version,
        )
        result = comparison.compare(
            first.record,
            second.record,
        )
        return {
            "command": "compare",
            "knowledge_id": options.knowledge_id,
            "first": first.to_dict(),
            "second": second.to_dict(),
            "comparison": result.to_dict(),
        }

    raise RuntimeError(
        f"Unhandled knowledge command: {options.command}"
    )


def _print_human(
    command: str,
    report: dict[str, Any],
) -> None:
    print("Knowledge")

    if command in {
        "list",
        "subject",
        "valid",
    }:
        if command == "subject":
            print(
                f"Subject      : {report['subject']}"
            )
        elif command == "valid":
            print(
                f"Subject      : {report['subject']}"
            )
            print(
                f"Valid at     : {report['at']}"
            )

        print(
            f"Records      : {report['count']}"
        )
        for item in report["records"]:
            _print_envelope(
                item
            )
        return

    if command == "show":
        _print_envelope(
            report["record"]
        )
        return

    if command == "latest":
        print(
            f"Subject      : {report['subject']}"
        )
        if report["record"] is None:
            print("Record       : none")
            return
        _print_envelope(
            report["record"]
        )
        return

    if command == "compare":
        comparison = report["comparison"]
        print(
            f"Knowledge ID : {report['knowledge_id']}"
        )
        print(
            "Earlier      : "
            f"{comparison['earlier_identity']}"
        )
        print(
            "Later        : "
            f"{comparison['later_identity']}"
        )
        print(
            "Changed      : "
            f"{comparison['any_change']}"
        )
        print(
            "Statement    : "
            f"{comparison['statement_changed']}"
        )
        print(
            "Status       : "
            f"{comparison['status_changed']}"
        )
        print(
            "Validity     : "
            f"{comparison['validity_changed']}"
        )
        print(
            "Evidence +   : "
            f"{len(comparison['evidence_added'])}"
        )
        print(
            "Evidence -   : "
            f"{len(comparison['evidence_removed'])}"
        )
        return

    raise RuntimeError(
        f"Unhandled human output command: {command}"
    )


def _print_envelope(
    envelope: dict[str, Any],
) -> None:
    record = envelope["record"]
    provenance = envelope["provenance"]
    print(
        "  "
        f"{envelope['identity_key']} "
        f"[{record['status']}] "
        f"subject={record['subject_key']} "
        f"provenance={provenance['status']}"
    )
    print(
        "    "
        f"valid={record['valid_from']} -> "
        f"{record['valid_to'] or 'open'}"
    )
    print(
        "    "
        f"statement={record['statement']}"
    )


def _parse_datetime(
    value: str,
) -> datetime:
    try:
        parsed = datetime.fromisoformat(
            value
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "datetime must be valid ISO-8601"
        ) from exc

    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(
            "datetime must include a timezone"
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
