"""Append-only repository boundary for portfolio valuation snapshots."""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.portfolio.portfolio_valuation_history import (
    PortfolioValuationHistory,
    PortfolioValuationSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class PortfolioValuationHistoryRepository(ABC):
    """Persistence-agnostic append-only valuation-history repository."""

    @abstractmethod
    def add(
        self,
        snapshot: PortfolioValuationSnapshot,
    ) -> PortfolioValuationSnapshot:
        """Append one snapshot or reject its immutable identity."""

    @abstractmethod
    def get(self, snapshot_id: str) -> PortfolioValuationSnapshot | None:
        """Return one exact snapshot, or None when absent."""

    def require(self, snapshot_id: str) -> PortfolioValuationSnapshot:
        snapshot = self.get(snapshot_id)
        if snapshot is None:
            raise KeyError(f"No portfolio valuation snapshot found for {snapshot_id}")
        return snapshot

    @abstractmethod
    def list_all(self) -> tuple[PortfolioValuationSnapshot, ...]:
        """Return snapshots ordered by valuation time and identity."""

    @abstractmethod
    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PortfolioValuationSnapshot, ...]:
        """Return valuation snapshots in [started_at, ended_at)."""

    @abstractmethod
    def list_recent(
        self,
        limit: int,
    ) -> tuple[PortfolioValuationSnapshot, ...]:
        """Return the latest limit snapshots in chronological order."""

    @abstractmethod
    def latest(self) -> PortfolioValuationSnapshot | None:
        """Return the latest snapshot, or None when the repository is empty."""

    @abstractmethod
    def history(self) -> PortfolioValuationHistory:
        """Return the current immutable valuation-history projection."""


class InMemoryPortfolioValuationHistoryRepository(PortfolioValuationHistoryRepository):
    """Executable reference implementation of valuation append semantics."""

    def __init__(
        self,
        *,
        ledger_id: str,
        portfolio_name: str,
    ) -> None:
        empty_history = PortfolioValuationHistory(
            ledger_id=ledger_id,
            portfolio_name=portfolio_name,
            snapshots=(),
        )
        self._ledger_id = empty_history.ledger_id
        self._portfolio_name = empty_history.portfolio_name
        self._snapshots: dict[str, PortfolioValuationSnapshot] = {}

    def add(
        self,
        snapshot: PortfolioValuationSnapshot,
    ) -> PortfolioValuationSnapshot:
        if not isinstance(snapshot, PortfolioValuationSnapshot):
            raise TypeError("snapshot must be a PortfolioValuationSnapshot")
        if snapshot.ledger_id != self._ledger_id:
            raise ValueError("snapshot must use the repository ledger_id")
        if snapshot.portfolio_name != self._portfolio_name:
            raise ValueError("snapshot must use the repository portfolio_name")
        if snapshot.snapshot_id in self._snapshots:
            raise ValueError("Portfolio valuation snapshot identity already exists")
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def get(self, snapshot_id: str) -> PortfolioValuationSnapshot | None:
        normalized_id = normalize_required_text(
            snapshot_id,
            field_name="snapshot_id",
        )
        return self._snapshots.get(normalized_id)

    def list_all(self) -> tuple[PortfolioValuationSnapshot, ...]:
        return tuple(
            sorted(
                self._snapshots.values(),
                key=lambda snapshot: (
                    snapshot.valued_at,
                    snapshot.snapshot_id,
                ),
            )
        )

    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PortfolioValuationSnapshot, ...]:
        start = validate_aware_datetime(
            started_at,
            field_name="started_at",
        )
        end = validate_aware_datetime(
            ended_at,
            field_name="ended_at",
        )
        if end <= start:
            raise ValueError("ended_at must be later than started_at")
        return tuple(
            snapshot
            for snapshot in self.list_all()
            if start <= snapshot.valued_at < end
        )

    def list_recent(
        self,
        limit: int,
    ) -> tuple[PortfolioValuationSnapshot, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        return self.list_all()[-limit:]

    def latest(self) -> PortfolioValuationSnapshot | None:
        snapshots = self.list_all()
        return snapshots[-1] if snapshots else None

    def history(self) -> PortfolioValuationHistory:
        return PortfolioValuationHistory(
            ledger_id=self._ledger_id,
            portfolio_name=self._portfolio_name,
            snapshots=self.list_all(),
        )
