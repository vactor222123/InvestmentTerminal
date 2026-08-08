"""
Controlled SQLite schema migration primitives for structured history.
"""

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalSchemaMigration:
    """One deterministic forward-only History schema migration."""

    from_version: int
    to_version: int
    name: str
    statements: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "from_version",
            "to_version",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise ValueError(
                    f"{field_name} must be a positive integer"
                )

        if self.to_version != self.from_version + 1:
            raise ValueError(
                "to_version must be exactly one greater than from_version"
            )

        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                self.name,
                field_name="name",
            ),
        )

        if not isinstance(
            self.statements,
            tuple,
        ):
            raise TypeError(
                "statements must be a tuple of SQL strings"
            )

        normalized_statements = tuple(
            normalize_required_text(
                statement,
                field_name="migration statement",
            )
            for statement in self.statements
        )

        if not normalized_statements:
            raise ValueError(
                "statements must contain at least one SQL statement"
            )

        object.__setattr__(
            self,
            "statements",
            normalized_statements,
        )

    def apply(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        """Apply this migration using a caller-owned transaction."""
        if not isinstance(
            connection,
            sqlite3.Connection,
        ):
            raise TypeError(
                "connection must be a sqlite3.Connection"
            )

        for statement in self.statements:
            connection.execute(
                statement
            )


class HistoricalSchemaMigrator:
    """
    Upgrade an initialized History database through ordered migrations.

    The migrator never bootstraps a missing database. The store owns initial
    schema creation; this component owns only forward evolution of an existing
    schema and records each resulting schema version atomically.
    """

    def __init__(
        self,
        *,
        store: HistoricalSQLiteStore,
        migrations: Iterable[HistoricalSchemaMigration],
        target_version: int,
    ) -> None:
        if not isinstance(
            store,
            HistoricalSQLiteStore,
        ):
            raise TypeError(
                "store must be a HistoricalSQLiteStore"
            )

        if (
            not isinstance(target_version, int)
            or isinstance(target_version, bool)
            or target_version <= 0
        ):
            raise ValueError(
                "target_version must be a positive integer"
            )

        items = tuple(
            migrations
        )
        if any(
            not isinstance(
                migration,
                HistoricalSchemaMigration,
            )
            for migration in items
        ):
            raise TypeError(
                "migrations must contain only HistoricalSchemaMigration values"
            )

        by_from_version: dict[
            int,
            HistoricalSchemaMigration,
        ] = {}
        for migration in items:
            if migration.from_version in by_from_version:
                raise ValueError(
                    "migrations must not contain duplicate from_version values"
                )
            by_from_version[
                migration.from_version
            ] = migration

        self.store = store
        self.target_version = target_version
        self._migrations = by_from_version

    def migrate(
        self,
    ) -> int:
        """
        Upgrade the initialized database to target_version atomically.

        All required migration steps and schema-version updates share one
        transaction. A failure or interruption rolls back the complete upgrade.
        """
        connection = self.store.connect()

        try:
            connection.execute(
                "BEGIN"
            )
            current_version = self._read_schema_version(
                connection
            )

            if current_version is None:
                raise RuntimeError(
                    "History schema must be initialized before migration"
                )

            if current_version > self.target_version:
                raise RuntimeError(
                    "History database schema version "
                    f"{current_version} is newer than supported "
                    f"target version {self.target_version}"
                )

            while current_version < self.target_version:
                migration = self._migrations.get(
                    current_version
                )
                if migration is None:
                    raise RuntimeError(
                        "No History schema migration is registered from "
                        f"version {current_version}"
                    )

                migration.apply(
                    connection
                )
                current_version = migration.to_version
                connection.execute(
                    """
                    UPDATE schema_metadata
                    SET value = ?
                    WHERE key = 'schema_version'
                    """,
                    (
                        str(
                            current_version
                        ),
                    ),
                )

            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

        return current_version

    @staticmethod
    def _read_schema_version(
        connection: sqlite3.Connection,
    ) -> int | None:
        try:
            row = connection.execute(
                """
                SELECT value
                FROM schema_metadata
                WHERE key = 'schema_version'
                """
            ).fetchone()
        except sqlite3.OperationalError:
            return None

        if row is None:
            return None

        try:
            version = int(
                row["value"]
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise RuntimeError(
                "History schema version metadata is invalid"
            ) from exc

        if version <= 0:
            raise RuntimeError(
                "History schema version metadata is invalid"
            )

        return version
