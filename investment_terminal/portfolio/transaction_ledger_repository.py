"""Repository contract for append-only portfolio transactions."""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
    PortfolioTransactionLedger,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class PortfolioTransactionRepository(ABC):
    """Persistence-agnostic append-only transaction repository contract."""

    @abstractmethod
    def add(self, transaction: PortfolioTransaction) -> PortfolioTransaction:
        """Append one transaction or reject its immutable identity."""

    @abstractmethod
    def add_batch(
        self,
        transactions: tuple[PortfolioTransaction, ...],
    ) -> tuple[bool, ...]:
        """Atomically append transactions and report each inserted identity."""

    @abstractmethod
    def get(self, transaction_id: str) -> PortfolioTransaction | None:
        """Return one exact transaction, or None when absent."""

    def require(self, transaction_id: str) -> PortfolioTransaction:
        transaction = self.get(transaction_id)
        if transaction is None:
            raise KeyError(
                f"No portfolio transaction found for {transaction_id}"
            )
        return transaction

    @abstractmethod
    def list_all(self) -> tuple[PortfolioTransaction, ...]:
        """Return transactions ordered by occurrence and identity."""

    @abstractmethod
    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PortfolioTransaction, ...]:
        """Return transactions in [started_at, ended_at)."""

    @abstractmethod
    def list_for_instrument(
        self,
        instrument_key: str,
    ) -> tuple[PortfolioTransaction, ...]:
        """Return instrument events in deterministic order."""

    @abstractmethod
    def snapshot(self) -> PortfolioTransactionLedger:
        """Return the current immutable ledger projection."""


class InMemoryPortfolioTransactionRepository(
    PortfolioTransactionRepository
):
    """Executable reference implementation of append-only semantics."""

    def __init__(
        self,
        *,
        ledger_id: str,
        portfolio_name: str,
        base_currency: str,
    ) -> None:
        empty_ledger = PortfolioTransactionLedger(
            ledger_id=ledger_id,
            portfolio_name=portfolio_name,
            base_currency=base_currency,
            transactions=(),
        )
        self._ledger_id = empty_ledger.ledger_id
        self._portfolio_name = empty_ledger.portfolio_name
        self._base_currency = empty_ledger.base_currency
        self._transactions: dict[str, PortfolioTransaction] = {}

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
        staged = self._transactions.copy()
        inserted: list[bool] = []
        for transaction in transactions:
            is_new = transaction.transaction_id not in staged
            inserted.append(is_new)
            if is_new:
                staged[transaction.transaction_id] = transaction
        self._transactions = staged
        return tuple(inserted)

    def get(self, transaction_id: str) -> PortfolioTransaction | None:
        normalized_id = normalize_required_text(
            transaction_id,
            field_name="transaction_id",
        )
        return self._transactions.get(normalized_id)

    def list_all(self) -> tuple[PortfolioTransaction, ...]:
        return tuple(
            sorted(
                self._transactions.values(),
                key=lambda transaction: (
                    transaction.occurred_at,
                    transaction.transaction_id,
                ),
            )
        )

    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PortfolioTransaction, ...]:
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
            transaction
            for transaction in self.list_all()
            if start <= transaction.occurred_at < end
        )

    def list_for_instrument(
        self,
        instrument_key: str,
    ) -> tuple[PortfolioTransaction, ...]:
        normalized_key = normalize_required_text(
            instrument_key,
            field_name="instrument_key",
            uppercase=True,
        )
        return tuple(
            transaction
            for transaction in self.list_all()
            if (
                transaction.instrument is not None
                and transaction.instrument.instrument_key == normalized_key
            )
        )

    def snapshot(self) -> PortfolioTransactionLedger:
        return PortfolioTransactionLedger(
            ledger_id=self._ledger_id,
            portfolio_name=self._portfolio_name,
            base_currency=self._base_currency,
            transactions=self.list_all(),
        )
