"""SQLite adapter for the portfolio transaction repository contract."""

import json
import sqlite3
from datetime import datetime

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
    PortfolioTransactionLedger,
)
from investment_terminal.portfolio.transaction_ledger_repository import (
    PortfolioTransactionRepository,
)
from investment_terminal.portfolio.transaction_ledger_sqlite_store import (
    PortfolioTransactionSQLiteStore,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class SQLitePortfolioTransactionRepository(PortfolioTransactionRepository):
    """Persist append-only portfolio transactions in SQLite."""

    def __init__(self, store: PortfolioTransactionSQLiteStore) -> None:
        if not isinstance(store, PortfolioTransactionSQLiteStore):
            raise TypeError("store must be a PortfolioTransactionSQLiteStore")
        self.store = store

    def add(self, transaction: PortfolioTransaction) -> PortfolioTransaction:
        if not isinstance(transaction, PortfolioTransaction):
            raise TypeError("transaction must be a PortfolioTransaction")
        if not self.add_batch((transaction,))[0]:
            raise ValueError(
                "Portfolio transaction identity already exists"
            )
        return transaction

    def add_batch(
        self,
        transactions: tuple[PortfolioTransaction, ...],
    ) -> tuple[bool, ...]:
        if not isinstance(transactions, tuple):
            raise TypeError("transactions must be a tuple")
        if any(not isinstance(item, PortfolioTransaction) for item in transactions):
            raise TypeError(
                "transactions must contain only PortfolioTransaction objects"
            )
        rows = tuple(self._to_row(transaction) for transaction in transactions)
        inserted: list[bool] = []
        with self.store.transaction() as connection:
            for row in rows:
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO portfolio_transactions "
                    "(transaction_id, occurred_at, instrument_key, payload_json) "
                    "VALUES (?, ?, ?, ?)",
                    row,
                )
                inserted.append(cursor.rowcount == 1)
        return tuple(inserted)

    def get(self, transaction_id: str) -> PortfolioTransaction | None:
        normalized_id = normalize_required_text(
            transaction_id, field_name="transaction_id"
        )
        rows = self._query(
            "SELECT payload_json FROM portfolio_transactions "
            "WHERE transaction_id = ?",
            (normalized_id,),
        )
        return self._from_row(rows[0]) if rows else None

    def list_all(self) -> tuple[PortfolioTransaction, ...]:
        return tuple(
            self._from_row(row)
            for row in self._query(
                "SELECT payload_json FROM portfolio_transactions "
                "ORDER BY occurred_at, transaction_id"
            )
        )

    def list_between(
        self, started_at: datetime, ended_at: datetime
    ) -> tuple[PortfolioTransaction, ...]:
        start = validate_aware_datetime(started_at, field_name="started_at")
        end = validate_aware_datetime(ended_at, field_name="ended_at")
        if end <= start:
            raise ValueError("ended_at must be later than started_at")
        return tuple(
            self._from_row(row)
            for row in self._query(
                "SELECT payload_json FROM portfolio_transactions "
                "WHERE occurred_at >= ? AND occurred_at < ? "
                "ORDER BY occurred_at, transaction_id",
                (start.isoformat(), end.isoformat()),
            )
        )

    def list_for_instrument(
        self, instrument_key: str
    ) -> tuple[PortfolioTransaction, ...]:
        key = normalize_required_text(
            instrument_key, field_name="instrument_key", uppercase=True
        )
        return tuple(
            self._from_row(row)
            for row in self._query(
                "SELECT payload_json FROM portfolio_transactions "
                "WHERE instrument_key = ? ORDER BY occurred_at, transaction_id",
                (key,),
            )
        )

    def snapshot(self) -> PortfolioTransactionLedger:
        return PortfolioTransactionLedger(
            ledger_id=self.store.ledger_id,
            portfolio_name=self.store.portfolio_name,
            base_currency=self.store.base_currency,
            transactions=self.list_all(),
        )

    def _query(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> list[sqlite3.Row]:
        self.store.initialize()
        with self.store.connect() as connection:
            return connection.execute(sql, parameters).fetchall()

    @staticmethod
    def _to_row(transaction: PortfolioTransaction) -> tuple[object, ...]:
        payload = json.dumps(
            transaction.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return (
            transaction.transaction_id,
            transaction.occurred_at.isoformat(),
            transaction.instrument.instrument_key
            if transaction.instrument is not None
            else None,
            payload,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> PortfolioTransaction:
        payload = json.loads(row["payload_json"])
        identity_payload = payload["instrument"]
        identity = (
            InstrumentIdentity(
                symbol=identity_payload["symbol"],
                name=identity_payload["name"],
                instrument_type=identity_payload["instrument_type"],
                currency=identity_payload["currency"],
                isin=identity_payload["isin"],
                exchange_ticker=identity_payload["exchange_ticker"],
                exchange_code=identity_payload["exchange_code"],
            )
            if identity_payload is not None
            else None
        )
        return PortfolioTransaction(
            transaction_id=payload["transaction_id"],
            transaction_type=payload["transaction_type"],
            occurred_at=datetime.fromisoformat(payload["occurred_at"]),
            settlement_currency=payload["settlement_currency"],
            instrument=identity,
            quantity=payload["quantity"],
            unit_price=payload["unit_price"],
            cash_amount=payload["cash_amount"],
            source_reference=payload["source_reference"],
        )
