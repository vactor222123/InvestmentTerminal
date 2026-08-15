"""
Ingest verified History snapshot metadata into the Knowledge SQLite projection.

This command is the cross-domain composition boundary. History and Knowledge
remain independent domains; the CLI composes their repositories and delegates
translation, ordering, idempotency, and projection semantics to existing
services.

Operational guardrails require explicit snapshot scope. A dry run executes the
same projection/ingestion semantics against an in-memory Knowledge repository
without creating or mutating the target Knowledge database.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from investment_terminal.cli.history_knowledge import (
    HistoricalSnapshotKnowledgeBatchIngestionService,
    HistoricalSnapshotKnowledgeBatchItem,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.knowledge.ingestion import (
    HistoricalSnapshotKnowledgeIngestionService,
)
from investment_terminal.knowledge.repository import (
    InMemoryKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


DEFAULT_HISTORY_DATABASE = (
    Path("data")
    / "history"
    / "history.db"
)
DEFAULT_KNOWLEDGE_DATABASE = (
    Path("data")
    / "knowledge"
    / "knowledge.db"
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest verified History snapshots into the rebuildable "
            "Knowledge SQLite projection."
        )
    )
    parser.add_argument(
        "--history-database",
        type=Path,
        default=DEFAULT_HISTORY_DATABASE,
        help="History SQLite database. Default: %(default)s.",
    )
    parser.add_argument(
        "--knowledge-database",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DATABASE,
        help="Knowledge SQLite database. Default: %(default)s.",
    )

    scope = parser.add_mutually_exclusive_group(
        required=True,
    )
    scope.add_argument(
        "--snapshot-id",
        action="append",
        default=None,
        help=(
            "Ingest one snapshot UUID. May be repeated for an explicit batch."
        ),
    )
    scope.add_argument(
        "--all",
        action="store_true",
        help="Explicitly select every History snapshot.",
    )

    parser.add_argument(
        "--subject",
        required=True,
        help="Subject key assigned to projected Knowledge records.",
    )
    parser.add_argument(
        "--generated-at",
        type=_parse_datetime,
        required=True,
        help="Timezone-aware ISO-8601 Knowledge generation timestamp.",
    )
    parser.add_argument(
        "--version",
        type=_positive_int,
        default=1,
        help="Explicit immutable Knowledge version. Default: %(default)s.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate selection and projection without creating or mutating "
            "the target Knowledge database."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the ingestion report as JSON.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    if not options.history_database.is_file():
        parser.error(
            f"History database does not exist: {options.history_database}"
        )

    history_store = HistoricalSQLiteStore(
        options.history_database
    )

    try:
        HistoricalSchemaMigrator(
            store=history_store,
            migrations=HISTORICAL_SCHEMA_MIGRATIONS,
            target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
        ).migrate()

        snapshot_repository = HistoricalSnapshotRepository(
            history_store
        )
        state_repository = HistoricalImportStateRepository(
            history_store
        )

        snapshots = _select_snapshots(
            snapshot_repository,
            snapshot_ids=options.snapshot_id,
            select_all=options.all,
        )
        items = tuple(
            HistoricalSnapshotKnowledgeBatchItem(
                snapshot=snapshot,
                import_state=state_repository.require(
                    snapshot.snapshot_id
                ),
            )
            for snapshot in snapshots
        )

        if options.dry_run:
            knowledge_repository = InMemoryKnowledgeRecordRepository()
        else:
            knowledge_repository = SQLiteKnowledgeRecordRepository(
                KnowledgeSQLiteStore(
                    options.knowledge_database
                )
            )

        ingestion_service = HistoricalSnapshotKnowledgeIngestionService(
            repository=knowledge_repository,
        )
        batch_service = HistoricalSnapshotKnowledgeBatchIngestionService(
            ingestion_service=ingestion_service,
        )

        records = batch_service.ingest(
            items,
            subject_key=options.subject,
            generated_at=options.generated_at,
            version=options.version,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(str(exc))

    report = {
        "history_database": str(options.history_database),
        "knowledge_database": str(options.knowledge_database),
        "dry_run": options.dry_run,
        "scope": (
            "ALL"
            if options.all
            else "EXPLICIT"
        ),
        "selected_snapshot_ids": [
            snapshot.snapshot_id
            for snapshot in snapshots
        ],
        "subject": options.subject,
        "generated_at": options.generated_at.isoformat(),
        "version": options.version,
        "history_snapshots": len(items),
        "knowledge_records": len(records),
        "records": [
            record.to_dict()
            for record in records
        ],
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

    action = (
        "validated"
        if options.dry_run
        else "completed"
    )
    print(
        f"History → Knowledge ingestion {action}"
    )
    print(
        f"Dry run           : {report['dry_run']}"
    )
    print(
        f"Scope             : {report['scope']}"
    )
    print(
        f"History snapshots : {report['history_snapshots']}"
    )
    print(
        f"Knowledge records : {report['knowledge_records']}"
    )
    print(
        f"Subject           : {report['subject']}"
    )
    print(
        f"Version           : {report['version']}"
    )
    print(
        f"History database  : {report['history_database']}"
    )
    print(
        f"Knowledge database: {report['knowledge_database']}"
    )


def _select_snapshots(
    repository: HistoricalSnapshotRepository,
    *,
    snapshot_ids: list[str] | None,
    select_all: bool,
) -> tuple[HistoricalSnapshot, ...]:
    if select_all:
        return repository.list_all()

    if not snapshot_ids:
        raise ValueError(
            "explicit snapshot selection is required"
        )

    if len(snapshot_ids) != len(set(snapshot_ids)):
        raise ValueError(
            "snapshot-id values must be unique"
        )

    return tuple(
        repository.require(snapshot_id)
        for snapshot_id in snapshot_ids
    )


def _parse_datetime(
    value: str,
) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "generated-at must be valid ISO-8601"
        ) from exc

    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(
            "generated-at must include a timezone"
        )

    return parsed


def _positive_int(
    value: str,
) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "version must be a positive integer"
        ) from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "version must be a positive integer"
        )

    return parsed


if __name__ == "__main__":
    main()
