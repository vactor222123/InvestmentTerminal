"""
SQLite adapter for the KnowledgeRecordRepository contract.
"""

import sqlite3
from datetime import datetime

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.repository import (
    KnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class SQLiteKnowledgeRecordRepository(
    KnowledgeRecordRepository
):
    """Persist and query KnowledgeRecord values in Knowledge SQLite."""

    def __init__(
        self,
        store: KnowledgeSQLiteStore,
    ) -> None:
        if not isinstance(
            store,
            KnowledgeSQLiteStore,
        ):
            raise TypeError(
                "store must be a KnowledgeSQLiteStore"
            )
        self.store = store

    def add(
        self,
        record: KnowledgeRecord,
    ) -> KnowledgeRecord:
        if not isinstance(
            record,
            KnowledgeRecord,
        ):
            raise TypeError(
                "record must be a KnowledgeRecord"
            )

        self.store.initialize()

        try:
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO knowledge_records (
                        knowledge_id,
                        version,
                        knowledge_type,
                        subject_key,
                        statement,
                        valid_from,
                        valid_to,
                        generated_at,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.knowledge_id,
                        record.version,
                        record.knowledge_type,
                        record.subject_key,
                        record.statement,
                        record.valid_from.isoformat(),
                        (
                            None
                            if record.valid_to is None
                            else record.valid_to.isoformat()
                        ),
                        record.generated_at.isoformat(),
                        record.status,
                    ),
                )

                connection.executemany(
                    """
                    INSERT INTO knowledge_evidence (
                        knowledge_id,
                        version,
                        evidence_order,
                        evidence_type,
                        evidence_id,
                        observed_at,
                        checksum_sha256
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            record.knowledge_id,
                            record.version,
                            index,
                            item.evidence_type,
                            item.evidence_id,
                            item.observed_at.isoformat(),
                            item.checksum_sha256,
                        )
                        for index, item in enumerate(
                            record.evidence
                        )
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Knowledge record identity already exists "
                "or evidence violates repository constraints"
            ) from exc

        return record

    def get(
        self,
        knowledge_id: str,
        version: int,
    ) -> KnowledgeRecord | None:
        normalized_id = normalize_required_text(
            knowledge_id,
            field_name="knowledge_id",
        )
        normalized_version = self._normalize_version(
            version
        )

        self.store.initialize()
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE knowledge_id = ?
                  AND version = ?
                """,
                (
                    normalized_id,
                    normalized_version,
                ),
            ).fetchone()

            if row is None:
                return None

            evidence = self._evidence_for(
                connection,
                normalized_id,
                normalized_version,
            )

        return self._from_row(
            row,
            evidence,
        )

    def list_all(
        self,
    ) -> tuple[KnowledgeRecord, ...]:
        self.store.initialize()
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM knowledge_records
                ORDER BY
                    generated_at,
                    knowledge_id,
                    version
                """
            ).fetchall()
            return tuple(
                self._from_row(
                    row,
                    self._evidence_for(
                        connection,
                        row["knowledge_id"],
                        int(row["version"]),
                    ),
                )
                for row in rows
            )

    def find_by_subject(
        self,
        subject_key: str,
    ) -> tuple[KnowledgeRecord, ...]:
        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )

        self.store.initialize()
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE subject_key = ?
                ORDER BY
                    valid_from,
                    generated_at,
                    knowledge_id,
                    version
                """,
                (
                    normalized_subject,
                ),
            ).fetchall()
            return tuple(
                self._from_row(
                    row,
                    self._evidence_for(
                        connection,
                        row["knowledge_id"],
                        int(row["version"]),
                    ),
                )
                for row in rows
            )

    def find_valid_at(
        self,
        subject_key: str,
        *,
        at: datetime,
    ) -> tuple[KnowledgeRecord, ...]:
        validate_aware_datetime(
            at,
            field_name="at",
        )
        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )
        serialized = at.isoformat()

        self.store.initialize()
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE subject_key = ?
                  AND valid_from <= ?
                  AND (
                        valid_to IS NULL
                        OR valid_to >= ?
                  )
                ORDER BY
                    valid_from,
                    generated_at,
                    knowledge_id,
                    version
                """,
                (
                    normalized_subject,
                    serialized,
                    serialized,
                ),
            ).fetchall()
            return tuple(
                self._from_row(
                    row,
                    self._evidence_for(
                        connection,
                        row["knowledge_id"],
                        int(row["version"]),
                    ),
                )
                for row in rows
            )

    def latest_for_subject(
        self,
        subject_key: str,
    ) -> KnowledgeRecord | None:
        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )

        self.store.initialize()
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE subject_key = ?
                ORDER BY
                    generated_at DESC,
                    knowledge_id DESC,
                    version DESC
                LIMIT 1
                """,
                (
                    normalized_subject,
                ),
            ).fetchone()

            if row is None:
                return None

            evidence = self._evidence_for(
                connection,
                row["knowledge_id"],
                int(row["version"]),
            )

        return self._from_row(
            row,
            evidence,
        )

    @staticmethod
    def _normalize_version(
        version: int,
    ) -> int:
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version <= 0
        ):
            raise ValueError(
                "version must be a positive integer"
            )
        return version

    @staticmethod
    def _evidence_for(
        connection: sqlite3.Connection,
        knowledge_id: str,
        version: int,
    ) -> tuple[KnowledgeEvidenceReference, ...]:
        rows = connection.execute(
            """
            SELECT *
            FROM knowledge_evidence
            WHERE knowledge_id = ?
              AND version = ?
            ORDER BY evidence_order
            """,
            (
                knowledge_id,
                version,
            ),
        ).fetchall()

        return tuple(
            KnowledgeEvidenceReference(
                evidence_type=row["evidence_type"],
                evidence_id=row["evidence_id"],
                observed_at=datetime.fromisoformat(
                    row["observed_at"]
                ),
                checksum_sha256=row["checksum_sha256"],
            )
            for row in rows
        )

    @staticmethod
    def _from_row(
        row: sqlite3.Row,
        evidence: tuple[
            KnowledgeEvidenceReference,
            ...,
        ],
    ) -> KnowledgeRecord:
        return KnowledgeRecord(
            knowledge_id=row["knowledge_id"],
            knowledge_type=row["knowledge_type"],
            version=int(row["version"]),
            subject_key=row["subject_key"],
            statement=row["statement"],
            valid_from=datetime.fromisoformat(
                row["valid_from"]
            ),
            valid_to=(
                None
                if row["valid_to"] is None
                else datetime.fromisoformat(
                    row["valid_to"]
                )
            ),
            generated_at=datetime.fromisoformat(
                row["generated_at"]
            ),
            evidence=evidence,
            status=row["status"],
        )
