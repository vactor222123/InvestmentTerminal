"""Bounded transaction-derived portfolio valuation composition."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from investment_terminal.portfolio.portfolio_valuation_history import PortfolioValuationSnapshot
from investment_terminal.portfolio.portfolio_valuation_history_repository import PortfolioValuationHistoryRepository
from investment_terminal.portfolio.position_reconstruction import PositionReconstructor
from investment_terminal.portfolio.realized_performance import RealizedPerformanceCalculator
from investment_terminal.portfolio.transaction_ledger_repository import PortfolioTransactionRepository
from investment_terminal.portfolio.unrealized_performance import UnrealizedPerformanceCalculator
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class TransactionDerivedValuationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TransactionDerivedValuationResult:
    schema_version: int
    status: TransactionDerivedValuationStatus
    valued_at: datetime
    started_at: datetime
    completed_at: datetime
    transaction_count: int | None
    open_position_count: int | None
    quote_count: int | None
    currency_count: int | None
    stored_snapshot_total: int | None
    failure: dict[str, str] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "request": {"valued_at": self.valued_at.isoformat()},
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "coverage": {
                "transaction_count": self.transaction_count,
                "open_position_count": self.open_position_count,
                "quote_count": self.quote_count,
                "currency_count": self.currency_count,
                "stored_snapshot_total": self.stored_snapshot_total,
            },
            "failure": self.failure,
            "limitations": [
                "report excludes paths, identities, instruments, quantities, prices, and monetary values",
                "quote age is caller-owned evidence; no freshness threshold is inferred",
                "result excludes cash valuation and does not execute a workflow",
                "result does not authorize analysis or trading",
            ],
        }


class TransactionDerivedValuationService:
    """Build and append one valuation snapshot with fail-closed inputs."""

    def __init__(self, transactions: PortfolioTransactionRepository,
                 valuations: PortfolioValuationHistoryRepository, price_provider,
                 *, clock: Callable[[], datetime]) -> None:
        self.transactions = transactions
        self.valuations = valuations
        self.price_provider = price_provider
        self.clock = clock

    def run(self, *, snapshot_id: str, valued_at: datetime) -> TransactionDerivedValuationResult:
        snapshot_key = normalize_required_text(snapshot_id, field_name="snapshot_id")
        valuation_time = validate_aware_datetime(valued_at, field_name="valued_at")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        counts: list[int | None] = [None] * 5
        try:
            ledger = self.transactions.snapshot()
            counts[0] = len(ledger.transactions)
            if any(item.occurred_at > valuation_time for item in ledger.transactions):
                raise ValueError("transaction ledger contains activity later than valued_at")
            reconstruction = PositionReconstructor.reconstruct(ledger)
            counts[1] = len(reconstruction.positions)
            unrealized = UnrealizedPerformanceCalculator(self.price_provider).calculate(
                reconstruction, valued_at=valuation_time
            )
            counts[2] = len(unrealized.positions)
            realized = RealizedPerformanceCalculator.calculate(ledger)
            snapshot = PortfolioValuationSnapshot.build(
                snapshot_id=snapshot_key, unrealized=unrealized, realized=realized
            )
            counts[3] = len(snapshot.currency_values)
            before = len(self.valuations.list_all())
            self.valuations.add(snapshot)
            counts[4] = before + 1
            status = TransactionDerivedValuationStatus.SUCCESS
            failure = None
        except Exception as exc:
            status = TransactionDerivedValuationStatus.FAILED
            failure = {"type": type(exc).__name__, "reason": "transaction-derived valuation failed"}
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return TransactionDerivedValuationResult(
            1, status, valuation_time, started, completed, *counts, failure
        )
