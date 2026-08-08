"""
Synchronize historical snapshot metadata and import archived Review Packages.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


DEFAULT_HISTORY_ROOT = (
    Path("data")
    / "history"
)
DEFAULT_MANIFEST_NAME = "manifest.jsonl"
DEFAULT_DATABASE_NAME = "history.db"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize the historical manifest with SQLite and "
            "import archived Review Packages."
        )
    )
    parser.add_argument(
        "--history-root",
        type=Path,
        default=DEFAULT_HISTORY_ROOT,
        help=(
            "Root directory containing archived Review Packages. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Optional manifest path. "
            "Default: <history-root>/manifest.jsonl."
        ),
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Optional SQLite database path. "
            "Default: <history-root>/history.db."
        ),
    )
    parser.add_argument(
        "--snapshot-id",
        default=None,
        help=(
            "Import only one snapshot UUID after manifest synchronization."
        ),
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help=(
            "Synchronize manifest metadata without importing "
            "Review Package details."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the import report as JSON.",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(
        argv
    )

    manifest_path = (
        options.manifest
        if options.manifest is not None
        else (
            options.history_root
            / DEFAULT_MANIFEST_NAME
        )
    )
    database_path = (
        options.database
        if options.database is not None
        else (
            options.history_root
            / DEFAULT_DATABASE_NAME
        )
    )

    manifest = HistoricalSnapshotManifest(
        manifest_path
    )
    store = HistoricalSQLiteStore(
        database_path
    )
    repository = HistoricalSnapshotRepository(
        store
    )
    manifest_importer = HistoricalManifestImportService(
        manifest=manifest,
        repository=repository,
    )

    try:
        manifest_result = manifest_importer.synchronize()

        imported_results = []

        if not options.metadata_only:
            pipeline = HistoricalImportPipeline(
                store=store,
                loader=HistoricalReviewPackageLoader(
                    options.history_root
                ),
            )

            snapshots = (
                (
                    repository.require(
                        options.snapshot_id
                    ),
                )
                if options.snapshot_id is not None
                else repository.list_all()
            )

            for snapshot in snapshots:
                if repository.has_detail_import(
                    snapshot.snapshot_id
                ):
                    continue

                imported_results.append(
                    pipeline.import_snapshot(
                        snapshot
                    )
                )
    except (
        FileNotFoundError,
        FileExistsError,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(
            str(exc)
        )

    report = {
        "manifest": manifest_result.to_dict(),
        "snapshots_imported": len(
            imported_results
        ),
        "imports": [
            result.to_dict()
            for result in imported_results
        ],
        "database": str(
            database_path
        ),
        "manifest_path": str(
            manifest_path
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

    print(
        "Historical import completed"
    )
    print(
        f"Manifest records : "
        f"{manifest_result.manifest_records}"
    )
    print(
        f"Metadata imported: "
        f"{manifest_result.imported_records}"
    )
    print(
        f"Metadata skipped : "
        f"{manifest_result.skipped_records}"
    )
    print(
        f"Packages imported: "
        f"{len(imported_results)}"
    )
    print(
        f"Database         : "
        f"{database_path}"
    )


if __name__ == "__main__":
    main()
