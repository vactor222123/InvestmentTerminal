from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.transaction_import import TransactionImportBatch, TransactionImportService
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransaction
from investment_terminal.portfolio.transaction_ledger_repository import InMemoryPortfolioTransactionRepository


NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)
ASSET = InstrumentIdentity(symbol="WORLD", name="World ETF", instrument_type="ETF", currency="EUR", isin="IE00B4L5Y983")


def tx(transaction_id: str) -> PortfolioTransaction:
    return PortfolioTransaction(transaction_id=transaction_id, transaction_type="BUY", occurred_at=NOW, settlement_currency="EUR", instrument=ASSET, quantity=1.0, unit_price=100.0)


def repository() -> InMemoryPortfolioTransactionRepository:
    return InMemoryPortfolioTransactionRepository(ledger_id="main", portfolio_name="Personal", base_currency="EUR")


def test_import_accounts_for_new_and_existing_identities() -> None:
    repo = repository()
    repo.add(tx("existing"))
    result = TransactionImportService(repo).import_batch(TransactionImportBatch(
        source_name=" broker export ", imported_at=NOW,
        transactions=(tx("new"), tx("existing")),
    ))
    assert result.imported_transaction_ids == ("new",)
    assert result.duplicate_transaction_ids == ("existing",)
    assert result.to_dict()["submitted_count"] == 2


def test_repeated_identity_inside_batch_is_counted_not_hidden() -> None:
    result = TransactionImportService(repository()).import_batch(TransactionImportBatch(
        source_name="source", imported_at=NOW,
        transactions=(tx("same"), tx("same"), tx("same")),
    ))
    assert result.imported_count == 1
    assert result.duplicate_count == 2
    assert result.duplicate_transaction_ids == ("same", "same")


def test_reimport_is_idempotent_with_explicit_duplicate_accounting() -> None:
    repo = repository()
    service = TransactionImportService(repo)
    batch = TransactionImportBatch(source_name="source", imported_at=NOW, transactions=(tx("a"), tx("b")))
    assert service.import_batch(batch).imported_count == 2
    second = service.import_batch(batch)
    assert second.imported_count == 0
    assert second.duplicate_transaction_ids == ("a", "b")
    assert len(repo.list_all()) == 2


def test_empty_batch_is_valid_and_explicit() -> None:
    result = TransactionImportService(repository()).import_batch(TransactionImportBatch(source_name="source", imported_at=NOW, transactions=()))
    assert result.to_dict()["submitted_count"] == 0
    assert result.imported_count == result.duplicate_count == 0


def test_batch_rejects_naive_import_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        TransactionImportBatch(source_name="source", imported_at=datetime(2026, 8, 17), transactions=())
