"""Detached one-instrument average-cost projection in an explicit split basis."""

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256

from investment_terminal.market.corporate_actions import canonical_bytes
from investment_terminal.market.split_adjustment import SplitPlan, finite_float
from investment_terminal.portfolio.position_reconstruction import ReconstructedPosition
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransactionLedger


@dataclass(frozen=True, slots=True)
class SplitPortfolioProjection:
    source_ledger_sha256: str
    plan: SplitPlan
    instrument_key: str
    trade_count: int
    changed_trade_count: int
    position: ReconstructedPosition | None
    realized_gain_loss: float
    settlement_currency: str

    def to_dict(self):
        return {
            "schema_version": 1,
            "operation_identity": "SPLIT_PORTFOLIO_PROJECTION",
            "source_ledger_sha256": self.source_ledger_sha256,
            "split_evidence": self.plan.to_dict(),
            "instrument_key": self.instrument_key,
            "input_trade_basis": "AS_TRADED",
            "output_share_basis": "SPLIT_ADJUSTED_TO_EXCLUSIVE_END",
            "trade_count": self.trade_count,
            "changed_trade_count": self.changed_trade_count,
            "position": self.position.to_dict() if self.position else None,
            "realized_gain_loss": self.realized_gain_loss,
            "settlement_currency": self.settlement_currency,
            "limitations": [
                "conditional on observed splits; action completeness unknown",
                "requires complete original trade history; no opening holdings or transfers inferred",
                "fractional entitlement retained; no broker rounding or cash-in-lieu inferred",
                "average-cost gross trades only; no dividends, fees, tax or total return",
                "not a transaction ledger, broker balance or persisted valuation",
            ],
        }


def project_split_positions(ledger: PortfolioTransactionLedger, plan: SplitPlan,
                            *, instrument_key: str, trade_basis: str) -> SplitPortfolioProjection:
    """Replay primary trades in common end-date share units using exact arithmetic.

    Original trade gross amounts are retained, not recomputed from rounded
    adjusted unit prices. Derived output cannot be passed back as a ledger.
    """
    if not isinstance(ledger, PortfolioTransactionLedger) or not isinstance(plan, SplitPlan):
        raise TypeError("Expected primary ledger and split plan")
    if trade_basis != "AS_TRADED":
        raise ValueError("Only original as-traded broker transactions are supported")
    trades = tuple(t for t in ledger.transactions if t.transaction_type in ("BUY", "SELL")
                   and t.instrument.instrument_key == instrument_key)
    if not trades:
        raise ValueError("Selected instrument has no trades")
    instrument = trades[0].instrument
    currency = trades[0].settlement_currency
    # Do not guess cross-listing mappings or apply ratios to an ambiguous alias.
    if (instrument.symbol, instrument.currency, instrument.instrument_type) != (
            plan.snapshot.symbol, plan.snapshot.quote_currency, plan.snapshot.instrument_type.replace("EQUITY", "STOCK")):
        raise ValueError("Exact instrument/action mapping required")
    quantity = cost = realized = Fraction(0)
    changed = 0
    for trade in trades:
        if trade.instrument != instrument or trade.settlement_currency != currency:
            raise ValueError("Instrument identity or settlement currency changed")
        factor = plan.factor(trade.occurred_at, trade=True)
        changed += factor != 1
        units = Fraction(str(trade.quantity)) * factor
        gross = Fraction(str(trade.quantity)) * Fraction(str(trade.unit_price))
        if trade.transaction_type == "BUY":
            quantity += units
            cost += gross
        else:
            if units > quantity:
                raise ValueError("SELL exceeds split-adjusted available quantity")
            allocated = cost * units / quantity
            realized += gross - allocated
            quantity -= units
            cost -= allocated
    position = None if quantity == 0 else ReconstructedPosition(
        instrument, finite_float(quantity), finite_float(cost),
        finite_float(cost / quantity), currency,
    )
    return SplitPortfolioProjection(
        sha256(canonical_bytes(ledger.to_dict())).hexdigest(), plan, instrument_key,
        len(trades), changed, position, finite_float(realized), currency,
    )
