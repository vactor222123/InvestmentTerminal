"""SQLite repository adapter for persisted admissible grounded generations."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any

from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.generation_repository import (
    GroundedGenerationRepository,
    _validate_limit,
    _validate_window,
)
from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.utils.validation import normalize_required_text


class SQLiteGroundedGenerationRepository(
    GroundedGenerationRepository
):
    def __init__(
        self,
        store: GroundedGenerationSQLiteStore,
    ) -> None:
        if not isinstance(
            store,
            GroundedGenerationSQLiteStore,
        ):
            raise TypeError(
                "store must be a GroundedGenerationSQLiteStore"
            )
        self.store = store

    def add(
        self,
        record: PersistedGroundedGeneration,
    ) -> PersistedGroundedGeneration:
        if not isinstance(
            record,
            PersistedGroundedGeneration,
        ):
            raise TypeError(
                "record must be a PersistedGroundedGeneration"
            )

        serialized = record.to_dict()

        self.store.initialize()
        try:
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO grounded_generations (
                        request_id,
                        generated_at,
                        prompt_protocol_identity,
                        answer_protocol_identity,
                        provider_identity,
                        model_identity,
                        selected_knowledge_identities_json,
                        cited_knowledge_identities_json,
                        generation_json,
                        trace_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.request_id,
                        record.generated_at.isoformat(),
                        record.prompt_protocol_identity,
                        record.answer_protocol_identity,
                        record.provider_identity,
                        record.model_identity,
                        self._json_dump(
                            serialized[
                                "selected_knowledge_identities"
                            ]
                        ),
                        self._json_dump(
                            serialized[
                                "cited_knowledge_identities"
                            ]
                        ),
                        self._json_dump(
                            serialized["generation"]
                        ),
                        self._json_dump(
                            serialized["trace"]
                        ),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Grounded generation request identity already exists "
                "or record violates repository constraints"
            ) from exc
        return record

    def get(
        self,
        request_id: str,
    ) -> PersistedGroundedGeneration | None:
        normalized = normalize_required_text(
            request_id,
            field_name="request_id",
        )
        self.store.initialize()
        with closing(
            self.store.connect()
        ) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM grounded_generations
                WHERE request_id = ?
                """,
                (normalized,),
            ).fetchone()
        return (
            None
            if row is None
            else self._from_row(row)
        )

    def list_all(
        self,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        self.store.initialize()
        with closing(
            self.store.connect()
        ) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM grounded_generations
                ORDER BY generated_at, request_id
                """
            ).fetchall()
        return tuple(
            self._from_row(row)
            for row in rows
        )

    def list_recent(
        self,
        limit: int,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        validated_limit = _validate_limit(
            limit
        )
        self.store.initialize()
        with closing(
            self.store.connect()
        ) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM grounded_generations
                ORDER BY generated_at DESC, request_id DESC
                LIMIT ?
                """,
                (validated_limit,),
            ).fetchall()
        return tuple(
            self._from_row(row)
            for row in rows
        )

    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        start, end = _validate_window(
            started_at,
            ended_at,
        )
        self.store.initialize()
        with closing(
            self.store.connect()
        ) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM grounded_generations
                WHERE generated_at >= ?
                  AND generated_at < ?
                ORDER BY generated_at, request_id
                """,
                (
                    start.isoformat(),
                    end.isoformat(),
                ),
            ).fetchall()
        return tuple(
            self._from_row(row)
            for row in rows
        )

    @staticmethod
    def _json_dump(
        value: object,
    ) -> str:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @staticmethod
    def _json_load(
        value: str,
    ) -> Any:
        def reject_non_finite(
            token: str,
        ) -> None:
            raise ValueError(
                "persisted JSON contains non-finite number "
                f"{token}"
            )

        return json.loads(
            value,
            parse_constant=reject_non_finite,
        )

    @classmethod
    def _from_row(
        cls,
        row: sqlite3.Row,
    ) -> PersistedGroundedGeneration:
        selected = cls._json_load(
            row["selected_knowledge_identities_json"]
        )
        cited = cls._json_load(
            row["cited_knowledge_identities_json"]
        )
        generation = cls._json_load(
            row["generation_json"]
        )
        trace = cls._json_load(
            row["trace_json"]
        )

        if not isinstance(selected, list):
            raise ValueError(
                "persisted selected Knowledge identities must be a list"
            )
        if not isinstance(cited, list):
            raise ValueError(
                "persisted cited Knowledge identities must be a list"
            )
        if not isinstance(generation, dict):
            raise ValueError(
                "persisted generation must be an object"
            )
        if not isinstance(trace, dict):
            raise ValueError(
                "persisted trace must be an object"
            )

        return PersistedGroundedGeneration(
            request_id=row["request_id"],
            generated_at=datetime.fromisoformat(
                row["generated_at"]
            ),
            prompt_protocol_identity=(
                row["prompt_protocol_identity"]
            ),
            answer_protocol_identity=(
                row["answer_protocol_identity"]
            ),
            provider_identity=row["provider_identity"],
            model_identity=row["model_identity"],
            selected_knowledge_identities=tuple(
                selected
            ),
            cited_knowledge_identities=tuple(
                cited
            ),
            generation=generation,
            trace=trace,
        )
