"""
Ingest verified History snapshot metadata into the Knowledge SQLite projection.

This command is the cross-domain composition boundary. History and Knowledge
remain independent domains; the CLI composes their repositories and delegates
all translation, ordering, idempotency, and projection semantics to existing
services.
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
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.knowledge.ingestion import (
    HistoricalSnapshotKnowledgeIngestionService,
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

        items = tuple(
            HistoricalSnapshotKnowledgeBatchItem(
                snapshot=snapshot,
                import_state=state_repository.require(
                    snapshot.snapshot_id
                ),
            )
            for snapshot in snapshot_repository.list_all()
        )

        knowledge_store = KnowledgeSQLiteStore(
            options.knowledge_database
        )
        knowledge_repository = SQLiteKnowledgeRecordRepository(
            knowledge_store
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

    print("History → Knowledge ingestion completed")
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
