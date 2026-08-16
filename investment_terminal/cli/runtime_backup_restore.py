"""Operator CLI for runtime SQLite backup and restore workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_terminal.persistence.runtime_backup_service import (
    RuntimeSQLiteBackupService,
    RuntimeSQLiteBackupSources,
)
from investment_terminal.persistence.runtime_restore_activation import (
    RuntimeSQLiteRestoreTargets,
    activate_runtime_sqlite_restore,
)
from investment_terminal.persistence.runtime_restore_validation import (
    validate_runtime_sqlite_restore_candidate,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, validate, and activate runtime SQLite backup sets."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    backup = subparsers.add_parser(
        "backup",
        help="Create a complete runtime SQLite backup set.",
    )
    _add_runtime_database_arguments(backup)
    backup.add_argument(
        "--backup-root",
        type=Path,
        required=True,
    )

    validate = subparsers.add_parser(
        "validate",
        help="Validate a backup set without mutating live databases.",
    )
    validate.add_argument(
        "--backup-set",
        type=Path,
        required=True,
    )

    restore = subparsers.add_parser(
        "restore",
        help="Validate and activate a backup set for an offline runtime.",
    )
    _add_runtime_database_arguments(restore)
    restore.add_argument(
        "--backup-set",
        type=Path,
        required=True,
    )
    restore.add_argument(
        "--confirm-offline",
        action="store_true",
        help=(
            "Required acknowledgement that the production runtime is stopped "
            "and no process is using the target SQLite databases."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    try:
        report = _build_report(options)
    except (
        FileExistsError,
        FileNotFoundError,
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        parser.error(str(exc))

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


def _add_runtime_database_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--knowledge-database",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--usage-cost-ledger-database",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--grounded-generation-database",
        type=Path,
        required=True,
    )


def _sources(options: argparse.Namespace) -> RuntimeSQLiteBackupSources:
    return RuntimeSQLiteBackupSources(
        knowledge_database=options.knowledge_database,
        usage_cost_ledger_database=options.usage_cost_ledger_database,
        grounded_generation_database=options.grounded_generation_database,
    )


def _targets(options: argparse.Namespace) -> RuntimeSQLiteRestoreTargets:
    return RuntimeSQLiteRestoreTargets(
        knowledge_database=options.knowledge_database,
        usage_cost_ledger_database=options.usage_cost_ledger_database,
        grounded_generation_database=options.grounded_generation_database,
    )


def _build_report(options: argparse.Namespace) -> dict[str, Any]:
    if options.command == "backup":
        result = RuntimeSQLiteBackupService(
            backup_root=options.backup_root,
            sources=_sources(options),
            clock=lambda: datetime.now(timezone.utc),
        ).create_backup_set()
        return {
            "command": "backup",
            "backup_set_id": result.backup_set_id,
            "directory": str(result.directory),
            "metadata_path": str(result.metadata_path),
            "databases": [
                {
                    "boundary_identity": item.boundary_identity,
                    "path": str(item.destination_path),
                    "size_bytes": item.size_bytes,
                }
                for item in result.backups
            ],
        }

    if options.command == "validate":
        candidate = validate_runtime_sqlite_restore_candidate(
            options.backup_set
        )
        return {
            "command": "validate",
            "backup_set_id": candidate.backup_set_id,
            "directory": str(candidate.directory),
            "created_at": candidate.created_at.isoformat(),
            "databases": [
                {
                    "boundary_identity": item.boundary_identity,
                    "path": str(item.backup_path),
                    "schema_version": item.schema_version,
                    "size_bytes": item.size_bytes,
                }
                for item in candidate.databases
            ],
        }

    if options.command == "restore":
        if not options.confirm_offline:
            raise ValueError(
                "restore requires --confirm-offline"
            )

        result = activate_runtime_sqlite_restore(
            backup_set_directory=options.backup_set,
            targets=_targets(options),
        )
        return {
            "command": "restore",
            "backup_set_id": result.backup_set_id,
            "restored_paths": [
                str(path)
                for path in result.restored_paths
            ],
        }

    raise RuntimeError(
        f"Unhandled runtime backup/restore command: {options.command}"
    )


def _print_human(report: dict[str, Any]) -> None:
    command = report["command"]

    if command == "backup":
        print("Runtime SQLite Backup")
        print(f"Backup set : {report['backup_set_id']}")
        print(f"Directory  : {report['directory']}")
        for item in report["databases"]:
            print(
                "  "
                f"{item['boundary_identity']} "
                f"{item['path']} "
                f"({item['size_bytes']} bytes)"
            )
        return

    if command == "validate":
        print("Runtime SQLite Restore Validation")
        print(f"Backup set : {report['backup_set_id']}")
        print(f"Created at : {report['created_at']}")
        for item in report["databases"]:
            print(
                "  "
                f"{item['boundary_identity']} "
                f"schema={item['schema_version']} "
                f"{item['path']}"
            )
        return

    if command == "restore":
        print("Runtime SQLite Restore")
        print(f"Backup set : {report['backup_set_id']}")
        for path in report["restored_paths"]:
            print(f"  restored: {path}")
        return

    raise RuntimeError(
        f"Unhandled human output command: {command}"
    )


if __name__ == "__main__":
    main()
