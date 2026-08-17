"""SQLite adapter for the portfolio valuation-history repository contract."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.portfolio_valuation_history import (
    PortfolioValuationCurrencySnapshot,
    PortfolioValuationHistory,
    PortfolioValuationSnapshot,
)
from investment_terminal.portfolio.portfolio_valuation_history_repository import (
    PortfolioValuationHistoryRepository,
)
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_store import (
    PortfolioValuationHistorySQLiteStore,
)
from investment_terminal.portfolio.realized_performance import (
    RealizedCurrencySummary,
    RealizedPerformance,
    RealizedSale,
)
from investment_terminal.portfolio.unrealized_performance import (
    UnrealizedCurrencySummary,
    UnrealizedPerformance,
    UnrealizedPositionPerformance,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class SQLitePortfolioValuationHistoryRepository(PortfolioValuationHistoryRepository):
    """Persist append-only portfolio valuation snapshots in SQLite."""

    def __init__(self, store: PortfolioValuationHistorySQLiteStore) -> None:
        if not isinstance(store, PortfolioValuationHistorySQLiteStore):
            raise TypeError("store must be a PortfolioValuationHistorySQLiteStore")
        self.store = store

    def add(self, snapshot: PortfolioValuationSnapshot) -> PortfolioValuationSnapshot:
        if not isinstance(snapshot, PortfolioValuationSnapshot):
            raise TypeError("snapshot must be a PortfolioValuationSnapshot")
        if snapshot.ledger_id != self.store.ledger_id:
            raise ValueError("snapshot must use the repository ledger_id")
        if snapshot.portfolio_name != self.store.portfolio_name:
            raise ValueError("snapshot must use the repository portfolio_name")
        payload = json.dumps(
            snapshot.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            with self.store.transaction() as connection:
                connection.execute(
                    "INSERT INTO portfolio_valuation_snapshots "
                    "(snapshot_id, valued_at, payload_json) VALUES (?, ?, ?)",
                    (snapshot.snapshot_id, snapshot.valued_at.isoformat(), payload),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Portfolio valuation snapshot identity already exists"
            ) from exc
        return snapshot

    def get(self, snapshot_id: str) -> PortfolioValuationSnapshot | None:
        normalized_id = normalize_required_text(snapshot_id, field_name="snapshot_id")
        rows = self._query(
            "SELECT payload_json FROM portfolio_valuation_snapshots "
            "WHERE snapshot_id = ?",
            (normalized_id,),
        )
        return self._from_row(rows[0]) if rows else None

    def list_all(self) -> tuple[PortfolioValuationSnapshot, ...]:
        return self._snapshots(
            self._query(
                "SELECT payload_json FROM portfolio_valuation_snapshots "
                "ORDER BY valued_at, snapshot_id"
            )
        )

    def list_between(
        self, started_at: datetime, ended_at: datetime
    ) -> tuple[PortfolioValuationSnapshot, ...]:
        start = validate_aware_datetime(started_at, field_name="started_at")
        end = validate_aware_datetime(ended_at, field_name="ended_at")
        if end <= start:
            raise ValueError("ended_at must be later than started_at")
        return self._snapshots(
            self._query(
                "SELECT payload_json FROM portfolio_valuation_snapshots "
                "WHERE valued_at >= ? AND valued_at < ? "
                "ORDER BY valued_at, snapshot_id",
                (start.isoformat(), end.isoformat()),
            )
        )

    def list_recent(self, limit: int) -> tuple[PortfolioValuationSnapshot, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        snapshots = self._snapshots(
            self._query(
                "SELECT payload_json FROM portfolio_valuation_snapshots "
                "ORDER BY valued_at DESC, snapshot_id DESC LIMIT ?",
                (limit,),
            )
        )
        return tuple(reversed(snapshots))

    def latest(self) -> PortfolioValuationSnapshot | None:
        snapshots = self.list_recent(1)
        return snapshots[0] if snapshots else None

    def history(self) -> PortfolioValuationHistory:
        return PortfolioValuationHistory(
            ledger_id=self.store.ledger_id,
            portfolio_name=self.store.portfolio_name,
            snapshots=self.list_all(),
        )

    def _query(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> list[sqlite3.Row]:
        self.store.initialize()
        with self.store.connect() as connection:
            return connection.execute(sql, parameters).fetchall()

    @classmethod
    def _snapshots(
        cls, rows: list[sqlite3.Row]
    ) -> tuple[PortfolioValuationSnapshot, ...]:
        return tuple(cls._from_row(row) for row in rows)

    @classmethod
    def _from_row(cls, row: sqlite3.Row) -> PortfolioValuationSnapshot:
        payload = json.loads(row["payload_json"])
        unrealized_payload = payload["unrealized"]
        realized_payload = payload["realized"]
        unrealized = UnrealizedPerformance(
            ledger_id=unrealized_payload["ledger_id"],
            portfolio_name=unrealized_payload["portfolio_name"],
            valued_at=datetime.fromisoformat(unrealized_payload["valued_at"]),
            positions=tuple(
                UnrealizedPositionPerformance(
                    instrument=cls._identity(item["instrument"]),
                    quantity=item["quantity"],
                    average_cost=item["average_cost"],
                    cost_basis=item["cost_basis"],
                    market_price=item["market_price"],
                    market_value=item["market_value"],
                    unrealized_gain_loss=item["unrealized_gain_loss"],
                    currency=item["currency"],
                    unrealized_return_percent=item["unrealized_return_percent"],
                    quoted_at=datetime.fromisoformat(item["quoted_at"]),
                    quote_source=item["quote_source"],
                )
                for item in unrealized_payload["positions"]
            ),
            currency_summaries=tuple(
                UnrealizedCurrencySummary(
                    currency=item["currency"],
                    cost_basis=item["cost_basis"],
                    market_value=item["market_value"],
                    unrealized_gain_loss=item["unrealized_gain_loss"],
                    unrealized_return_percent=item["unrealized_return_percent"],
                )
                for item in unrealized_payload["currency_summaries"]
            ),
        )
        realized = RealizedPerformance(
            ledger_id=realized_payload["ledger_id"],
            portfolio_name=realized_payload["portfolio_name"],
            sales=tuple(
                RealizedSale(
                    sell_transaction_id=item["sell_transaction_id"],
                    occurred_at=datetime.fromisoformat(item["occurred_at"]),
                    instrument=cls._identity(item["instrument"]),
                    quantity=item["quantity"],
                    proceeds=item["proceeds"],
                    allocated_cost_basis=item["allocated_cost_basis"],
                    realized_gain_loss=item["realized_gain_loss"],
                    currency=item["currency"],
                    realized_return_percent=item["realized_return_percent"],
                )
                for item in realized_payload["sales"]
            ),
            currency_summaries=tuple(
                RealizedCurrencySummary(
                    currency=item["currency"],
                    proceeds=item["proceeds"],
                    allocated_cost_basis=item["allocated_cost_basis"],
                    realized_gain_loss=item["realized_gain_loss"],
                )
                for item in realized_payload["currency_summaries"]
            ),
        )
        return PortfolioValuationSnapshot(
            snapshot_id=payload["snapshot_id"],
            unrealized=unrealized,
            realized=realized,
            currency_values=tuple(
                PortfolioValuationCurrencySnapshot(**item)
                for item in payload["currency_values"]
            ),
        )

    @staticmethod
    def _identity(payload: dict[str, Any]) -> InstrumentIdentity:
        return InstrumentIdentity(
            symbol=payload["symbol"],
            name=payload["name"],
            instrument_type=payload["instrument_type"],
            currency=payload["currency"],
            isin=payload["isin"],
            exchange_ticker=payload["exchange_ticker"],
            exchange_code=payload["exchange_code"],
        )
