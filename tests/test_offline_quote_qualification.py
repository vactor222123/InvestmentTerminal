"""Tests for read-only offline quote qualification."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import MarketMetadataProvenance
from investment_terminal.portfolio.instrument_metadata_enrichment import InstrumentMetadataDocument, InstrumentMetadataEvidence
from investment_terminal.portfolio.offline_quote_qualification import OfflineQuoteQualificationService, OfflineQuoteQualificationStatus
from investment_terminal.portfolio.portfolio_market_value_models import PortfolioPriceQuote
from investment_terminal.portfolio.portfolio_price_provider import InMemoryPortfolioPriceProvider
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransaction
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore

NOW = datetime(2026, 8, 25, 18, tzinfo=timezone.utc)
STOCK = InstrumentIdentity(symbol="MSFT", name="Microsoft", instrument_type="STOCK", currency="USD", exchange_ticker="MSFT")


def repository(path: Path):
    return SQLitePortfolioTransactionRepository(PortfolioTransactionSQLiteStore(path / "tx.db", ledger_id="main", portfolio_name="Personal", base_currency="EUR"))


def buy(at=NOW - timedelta(days=1)):
    return PortfolioTransaction(transaction_id="b1", transaction_type="BUY", occurred_at=at, settlement_currency="USD", instrument=STOCK, quantity=1, unit_price=100, cash_amount=None, source_reference=None)


def provider(*, currency="USD", at=NOW, extra=False):
    q = PortfolioPriceQuote(instrument_key="MSFT", exchange_ticker="MSFT", price=120, currency=currency, quoted_at=at, source="TEST")
    values = {"MSFT": q}
    if extra:
        values["EXTRA"] = PortfolioPriceQuote(instrument_key="EXTRA", exchange_ticker="EXTRA", price=1, currency="USD", quoted_at=at, source="TEST")
    return InMemoryPortfolioPriceProvider(values)


def qualify(tmp_path, prices):
    repo = repository(tmp_path)
    repo.add(buy())
    return OfflineQuoteQualificationService(repo, prices, clock=lambda: NOW).qualify(valued_at=NOW)


def test_success_reports_only_aggregate_coverage(tmp_path: Path):
    result = qualify(tmp_path, provider())
    assert result.status is OfflineQuoteQualificationStatus.SUCCESS
    assert (result.transaction_count, result.open_position_count, result.required_quote_count, result.matched_quote_count, result.currency_count) == (1, 1, 1, 1, 1)
    text = str(result.to_dict())
    assert "MSFT" not in text and "120" not in text and "Personal" not in text


def test_missing_extra_currency_and_future_quotes_fail_closed(tmp_path: Path):
    cases = (InMemoryPortfolioPriceProvider({}), provider(extra=True), provider(currency="EUR"), provider(at=NOW + timedelta(seconds=1)))
    for index, prices in enumerate(cases):
        assert qualify(tmp_path / str(index), prices).status is OfflineQuoteQualificationStatus.FAILED


def test_future_transaction_fails_closed(tmp_path: Path):
    repo = repository(tmp_path)
    repo.add(buy(NOW + timedelta(seconds=1)))
    result = OfflineQuoteQualificationService(repo, provider(), clock=lambda: NOW).qualify(valued_at=NOW)
    assert result.status is OfflineQuoteQualificationStatus.FAILED


def test_missing_ticker_can_use_ready_detached_metadata(tmp_path: Path):
    identity = InstrumentIdentity("MSFT", "Microsoft", "STOCK", "USD", isin="US5949181045")
    repo = repository(tmp_path)
    repo.add(PortfolioTransaction("b1", "BUY", NOW - timedelta(days=1), "USD", identity, 1, 100))
    quote = PortfolioPriceQuote(identity.instrument_key, "MSFT", 120, "USD", NOW, "TEST")
    metadata = InstrumentMetadataDocument((InstrumentMetadataEvidence(
        identity.instrument_key, "MSFT", "XNAS",
        MarketMetadataProvenance(
            "EXCHANGE_REFERENCE", NOW - timedelta(days=1), NOW - timedelta(days=1),
            source_record_id="MSFT", checksum_sha256="a" * 64,
        ),
    ),))
    result = OfflineQuoteQualificationService(
        repo, InMemoryPortfolioPriceProvider({identity.instrument_key: quote}),
        clock=lambda: NOW, instrument_metadata=metadata,
        metadata_maximum_age_days=7,
    ).qualify(valued_at=NOW)
    assert result.status is OfflineQuoteQualificationStatus.SUCCESS
    assert result.matched_quote_count == 1
    assert repo.snapshot().transactions[0].instrument.exchange_ticker is None


def test_metadata_arguments_must_be_supplied_together(tmp_path: Path):
    repo = repository(tmp_path)
    repo.add(buy())
    result = OfflineQuoteQualificationService(
        repo, provider(), clock=lambda: NOW, metadata_maximum_age_days=7
    ).qualify(valued_at=NOW)
    assert result.status is OfflineQuoteQualificationStatus.FAILED
