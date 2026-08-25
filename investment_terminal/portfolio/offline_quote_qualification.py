"""Read-only qualification of private offline portfolio quotes."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from investment_terminal.portfolio.portfolio_market_value_models import PortfolioPriceQuote
from investment_terminal.portfolio.instrument_metadata_enrichment import (
    InstrumentMetadataDocument,
    InstrumentMetadataEnrichmentService,
)
from investment_terminal.portfolio.position_reconstruction import PositionReconstructor
from investment_terminal.portfolio.transaction_ledger_repository import PortfolioTransactionRepository
from investment_terminal.utils.validation import validate_aware_datetime


class OfflineQuoteQualificationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class OfflineQuoteQualificationResult:
    status: OfflineQuoteQualificationStatus
    valued_at: datetime
    started_at: datetime
    completed_at: datetime
    transaction_count: int | None = None
    open_position_count: int | None = None
    required_quote_count: int | None = None
    matched_quote_count: int | None = None
    currency_count: int | None = None
    failure: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status.value,
            "request": {"valued_at": self.valued_at.isoformat()},
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "coverage": {
                "transaction_count": self.transaction_count,
                "open_position_count": self.open_position_count,
                "required_quote_count": self.required_quote_count,
                "matched_quote_count": self.matched_quote_count,
                "currency_count": self.currency_count,
            },
            "failure": self.failure,
            "limitations": [
                "report excludes paths, identities, instruments, quantities, prices, and monetary values",
                "quote age is caller-owned evidence; no freshness threshold is inferred",
                "qualification does not create a valuation database or snapshot",
                "qualification does not authorize analysis, workflow execution, or trading",
            ],
        }


class OfflineQuoteQualificationService:
    def __init__(self, transactions: PortfolioTransactionRepository, price_provider,
                 *, clock: Callable[[], datetime],
                 instrument_metadata: InstrumentMetadataDocument | None = None,
                 metadata_maximum_age_days: float | None = None) -> None:
        self.transactions = transactions
        self.price_provider = price_provider
        self.clock = clock
        self.instrument_metadata = instrument_metadata
        self.metadata_maximum_age_days = metadata_maximum_age_days

    def qualify(self, *, valued_at: datetime) -> OfflineQuoteQualificationResult:
        cutoff = validate_aware_datetime(valued_at, field_name="valued_at")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        counts: list[int | None] = [None] * 5
        try:
            ledger = self.transactions.snapshot()
            counts[0] = len(ledger.transactions)
            if any(item.occurred_at > cutoff for item in ledger.transactions):
                raise ValueError("transaction ledger contains activity later than valued_at")
            reconstruction = PositionReconstructor.reconstruct(ledger)
            if self.instrument_metadata is not None:
                if self.metadata_maximum_age_days is None:
                    raise ValueError("metadata_maximum_age_days is required with instrument metadata")
                reconstruction = InstrumentMetadataEnrichmentService.enrich(
                    reconstruction,
                    self.instrument_metadata,
                    checked_at=cutoff,
                    maximum_age_days=self.metadata_maximum_age_days,
                ).reconstruction
            elif self.metadata_maximum_age_days is not None:
                raise ValueError("instrument metadata is required with metadata_maximum_age_days")
            positions = reconstruction.positions
            counts[1] = counts[2] = len(positions)
            required = {item.instrument_key for item in positions}
            available = set(self.price_provider.instrument_keys)
            if available != required:
                raise ValueError("offline quote coverage must exactly match open positions")
            currencies: set[str] = set()
            for position in positions:
                ticker = position.instrument.exchange_ticker
                if ticker is None:
                    raise ValueError("open position has no exchange ticker")
                quote = self.price_provider.get_quote(
                    instrument_key=position.instrument_key, exchange_ticker=ticker
                )
                self._validate(position, quote, cutoff)
                currencies.add(quote.currency)
            counts[3] = len(positions)
            counts[4] = len(currencies)
            status = OfflineQuoteQualificationStatus.SUCCESS
            failure = None
        except Exception as exc:
            status = OfflineQuoteQualificationStatus.FAILED
            failure = {"type": type(exc).__name__, "reason": "offline quote qualification failed"}
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return OfflineQuoteQualificationResult(status, cutoff, started, completed, *counts, failure)

    @staticmethod
    def _validate(position, quote: PortfolioPriceQuote, cutoff: datetime) -> None:
        if not isinstance(quote, PortfolioPriceQuote):
            raise TypeError("price provider must return PortfolioPriceQuote")
        if quote.instrument_key != position.instrument_key:
            raise ValueError("quote instrument identity mismatch")
        if quote.exchange_ticker != position.instrument.exchange_ticker:
            raise ValueError("quote exchange ticker mismatch")
        if quote.currency != position.cost_currency:
            raise ValueError("quote currency mismatch")
        if quote.quoted_at > cutoff:
            raise ValueError("quote is later than valued_at")
