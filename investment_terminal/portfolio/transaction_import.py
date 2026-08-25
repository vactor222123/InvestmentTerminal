"""Provider-neutral portfolio transaction import contracts and service."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
)
from investment_terminal.portfolio.transaction_ledger_repository import (
    PortfolioTransactionRepository,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class TransactionImportBatch:
    source_name: str
    imported_at: datetime
    transactions: tuple[PortfolioTransaction, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", normalize_required_text(
            self.source_name, field_name="source_name"
        ))
        validate_aware_datetime(self.imported_at, field_name="imported_at")
        if not isinstance(self.transactions, tuple):
            raise TypeError("transactions must be a tuple")
        if any(not isinstance(item, PortfolioTransaction) for item in self.transactions):
            raise TypeError("transactions must contain only PortfolioTransaction objects")


@dataclass(frozen=True, slots=True)
class TransactionImportResult:
    source_name: str
    imported_at: datetime
    submitted_count: int
    imported_transaction_ids: tuple[str, ...]
    duplicate_transaction_ids: tuple[str, ...]

    @property
    def imported_count(self) -> int:
        return len(self.imported_transaction_ids)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_transaction_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "imported_at": self.imported_at.isoformat(),
            "submitted_count": self.submitted_count,
            "imported_count": self.imported_count,
            "duplicate_count": self.duplicate_count,
            "imported_transaction_ids": list(self.imported_transaction_ids),
            "duplicate_transaction_ids": list(self.duplicate_transaction_ids),
        }


class TransactionImportService:
    """Append new transaction identities and account for every duplicate."""

    def __init__(self, repository: PortfolioTransactionRepository) -> None:
        if not isinstance(repository, PortfolioTransactionRepository):
            raise TypeError("repository must be a PortfolioTransactionRepository")
        self.repository = repository

    def import_batch(self, batch: TransactionImportBatch) -> TransactionImportResult:
        if not isinstance(batch, TransactionImportBatch):
            raise TypeError("batch must be a TransactionImportBatch")
        inserted = self.repository.add_batch(batch.transactions)
        imported = [
            transaction.transaction_id
            for transaction, was_inserted in zip(
                batch.transactions, inserted, strict=True
            )
            if was_inserted
        ]
        duplicates = [
            transaction.transaction_id
            for transaction, was_inserted in zip(
                batch.transactions, inserted, strict=True
            )
            if not was_inserted
        ]
        return TransactionImportResult(
            source_name=batch.source_name,
            imported_at=batch.imported_at,
            submitted_count=len(batch.transactions),
            imported_transaction_ids=tuple(imported),
            duplicate_transaction_ids=tuple(duplicates),
        )
