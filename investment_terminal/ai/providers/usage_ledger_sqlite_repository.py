"""
SQLite adapter for the provider usage/cost ledger repository contract.
"""

import sqlite3
from datetime import datetime
from decimal import Decimal

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    GroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)
from investment_terminal.utils.validation import normalize_required_text


class SQLiteGroundedProviderUsageCostLedgerRepository(
    GroundedProviderUsageCostLedgerRepository
):
    """Persist immutable provider usage/cost ledger records in SQLite."""

    def __init__(
        self,
        store: GroundedProviderUsageCostLedgerSQLiteStore,
    ) -> None:
        if not isinstance(
            store,
            GroundedProviderUsageCostLedgerSQLiteStore,
        ):
            raise TypeError(
                "store must be a GroundedProviderUsageCostLedgerSQLiteStore"
            )
        self.store = store

    def add(
        self,
        record: GroundedProviderUsageCostLedgerRecord,
    ) -> GroundedProviderUsageCostLedgerRecord:
        if not isinstance(
            record,
            GroundedProviderUsageCostLedgerRecord,
        ):
            raise TypeError(
                "record must be a GroundedProviderUsageCostLedgerRecord"
            )

        self.store.initialize()

        try:
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO provider_usage_cost_ledger (
                        request_id,
                        provider_identity,
                        model_identity,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        currency,
                        input_cost,
                        output_cost,
                        total_cost,
                        recorded_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.request_id,
                        record.provider_identity,
                        record.model_identity,
                        record.input_tokens,
                        record.output_tokens,
                        record.total_tokens,
                        record.currency,
                        str(record.input_cost),
                        str(record.output_cost),
                        str(record.total_cost),
                        record.recorded_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Provider usage/cost ledger request identity already exists "
                "or record violates repository constraints"
            ) from exc

        return record

    def get(
        self,
        request_id: str,
    ) -> GroundedProviderUsageCostLedgerRecord | None:
        normalized_id = normalize_required_text(
            request_id,
            field_name="request_id",
        )

        self.store.initialize()
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM provider_usage_cost_ledger
                WHERE request_id = ?
                """,
                (
                    normalized_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._from_row(row)

    def list_all(
        self,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        self.store.initialize()
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM provider_usage_cost_ledger
                ORDER BY
                    recorded_at,
                    request_id
                """
            ).fetchall()

        return tuple(
            self._from_row(row)
            for row in rows
        )

    @staticmethod
    def _from_row(
        row: sqlite3.Row,
    ) -> GroundedProviderUsageCostLedgerRecord:
        return GroundedProviderUsageCostLedgerRecord(
            request_id=row["request_id"],
            provider_identity=row["provider_identity"],
            model_identity=row["model_identity"],
            input_tokens=int(row["input_tokens"]),
            output_tokens=int(row["output_tokens"]),
            total_tokens=int(row["total_tokens"]),
            currency=row["currency"],
            input_cost=Decimal(row["input_cost"]),
            output_cost=Decimal(row["output_cost"]),
            total_cost=Decimal(row["total_cost"]),
            recorded_at=datetime.fromisoformat(
                row["recorded_at"]
            ),
        )
