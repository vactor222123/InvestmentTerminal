"""Tests for bounded transaction-derived valuation composition."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.portfolio_market_value_models import PortfolioPriceQuote
from investment_terminal.portfolio.portfolio_price_provider import InMemoryPortfolioPriceProvider
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_repository import SQLitePortfolioValuationHistoryRepository
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_store import PortfolioValuationHistorySQLiteStore
from investment_terminal.portfolio.transaction_derived_valuation import TransactionDerivedValuationService, TransactionDerivedValuationStatus
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransaction
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore

NOW = datetime(2026, 8, 25, 18, tzinfo=timezone.utc)
STOCK = InstrumentIdentity(symbol="MSFT", name="Microsoft", instrument_type="STOCK", currency="USD", exchange_ticker="MSFT")


def repositories(tmp_path: Path):
    tx = SQLitePortfolioTransactionRepository(PortfolioTransactionSQLiteStore(tmp_path / "tx.db", ledger_id="main", portfolio_name="Personal", base_currency="EUR"))
    values = SQLitePortfolioValuationHistoryRepository(PortfolioValuationHistorySQLiteStore(tmp_path / "values.db", ledger_id="main", portfolio_name="Personal"))
    return tx, values


def buy(occurred_at: datetime = NOW - timedelta(days=1)) -> PortfolioTransaction:
    return PortfolioTransaction(transaction_id="buy-1", transaction_type="BUY", occurred_at=occurred_at, settlement_currency="USD", instrument=STOCK, quantity=2, unit_price=100, cash_amount=None, source_reference=None)


def provider(currency: str = "USD", quoted_at: datetime = NOW):
    quote = PortfolioPriceQuote(instrument_key=STOCK.instrument_key, exchange_ticker="MSFT", price=120, currency=currency, quoted_at=quoted_at, source="TEST")
    return InMemoryPortfolioPriceProvider({STOCK.instrument_key: quote})


def service(tmp_path: Path, price_provider=None):
    tx, values = repositories(tmp_path)
    return tx, values, TransactionDerivedValuationService(tx, values, price_provider or provider(), clock=lambda: NOW)


def test_appends_one_private_snapshot_and_returns_redacted_counts(tmp_path: Path) -> None:
    tx, values, value = service(tmp_path)
    tx.add(buy())
    result = value.run(snapshot_id="v-1", valued_at=NOW)
    assert result.status is TransactionDerivedValuationStatus.SUCCESS
    assert (result.transaction_count, result.open_position_count, result.quote_count, result.currency_count, result.stored_snapshot_total) == (1, 1, 1, 1, 1)
    assert len(values.list_all()) == 1
    payload = result.to_dict()
    text = str(payload)
    assert "MSFT" not in text and "120" not in text and "Personal" not in text


def test_future_transaction_fails_before_persistence(tmp_path: Path) -> None:
    tx, values, value = service(tmp_path)
    tx.add(buy(NOW + timedelta(seconds=1)))
    result = value.run(snapshot_id="v-1", valued_at=NOW)
    assert result.status is TransactionDerivedValuationStatus.FAILED
    assert result.failure == {"type": "ValueError", "reason": "transaction-derived valuation failed"}
    assert values.list_all() == ()


def test_missing_quote_and_currency_mismatch_fail_closed(tmp_path: Path) -> None:
    for index, prices in enumerate((InMemoryPortfolioPriceProvider({}), provider("EUR"))):
        root = tmp_path / str(index)
        tx, values, value = service(root, prices)
        tx.add(buy())
        assert value.run(snapshot_id="v-1", valued_at=NOW).status is TransactionDerivedValuationStatus.FAILED
        assert values.list_all() == ()


def test_duplicate_snapshot_is_visible_and_preserves_original(tmp_path: Path) -> None:
    tx, values, value = service(tmp_path)
    tx.add(buy())
    assert value.run(snapshot_id="v-1", valued_at=NOW).status is TransactionDerivedValuationStatus.SUCCESS
    assert value.run(snapshot_id="v-1", valued_at=NOW).status is TransactionDerivedValuationStatus.FAILED
    assert len(values.list_all()) == 1
