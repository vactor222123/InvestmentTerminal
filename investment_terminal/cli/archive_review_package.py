"""
Archive one completed investment review package into historical storage.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_service import (
    HistoricalSnapshotService,
)


DEFAULT_REVIEW_PACKAGE = (
    Path("output")
    / "investment_review_package.json"
)
DEFAULT_HISTORY_ROOT = (
    Path("data")
    / "history"
)
DEFAULT_MANIFEST_NAME = "manifest.jsonl"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Archive one investment review package "
            "into immutable historical storage."
        )
    )
    parser.add_argument(
        "--review-package",
        type=Path,
        default=DEFAULT_REVIEW_PACKAGE,
        help=(
            "Path to the completed investment review package. "
            f"Default: {DEFAULT_REVIEW_PACKAGE}"
        ),
    )
    parser.add_argument(
        "--history-root",
        type=Path,
        default=DEFAULT_HISTORY_ROOT,
        help=(
            "Root directory for immutable historical snapshots. "
            f"Default: {DEFAULT_HISTORY_ROOT}"
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Path to the snapshot manifest. "
            "Default: <history-root>/manifest.jsonl"
        ),
    )
    parser.add_argument(
        "--product-version",
        default=None,
        help=(
            "Optional Investment Terminal version recorded "
            "in snapshot metadata."
        ),
    )
    parser.add_argument(
        "--package-id",
        default=None,
        help=(
            "Optional explicit package identifier. "
            "Overrides package metadata when provided."
        ),
    )
    parser.add_argument(
        "--supersedes",
        default=None,
        help=(
            "Optional snapshot UUID corrected or superseded "
            "by this snapshot."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print archived snapshot metadata as JSON."
        ),
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

    service = HistoricalSnapshotService(
        archive=HistoricalSnapshotArchive(
            options.history_root
        ),
        manifest=HistoricalSnapshotManifest(
            manifest_path
        ),
    )

    try:
        snapshot = service.preserve(
            options.review_package,
            product_version=(
                options.product_version
            ),
            package_id=options.package_id,
            supersedes=options.supersedes,
        )
    except (
        FileNotFoundError,
        FileExistsError,
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
                snapshot.to_dict(),
                indent=2,
                allow_nan=False,
            )
        )
        return

    print(
        "Historical snapshot archived"
    )
    print(
        f"Snapshot ID : {snapshot.snapshot_id}"
    )
    print(
        f"Generated at: {snapshot.generated_at.isoformat()}"
    )
    print(
        f"Archived at : {snapshot.archived_at.isoformat()}"
    )
    print(
        f"Archive file: "
        f"{options.history_root / snapshot.relative_path}"
    )
    print(
        f"Manifest    : {manifest_path}"
    )
    print(
        f"SHA-256     : {snapshot.checksum_sha256}"
    )


if __name__ == "__main__":
    main()
