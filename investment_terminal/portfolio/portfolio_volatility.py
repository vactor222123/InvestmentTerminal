"""Deterministic portfolio volatility analysis."""

from dataclasses import dataclass
from datetime import datetime
from math import isclose, sqrt
from typing import Any

from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    RiskDataProvenance,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class PortfolioVolatilityAnalysis:
    ledger_id: str
    portfolio_name: str
    as_of: datetime
    currency: str
    period: str
    observation_count: int
    periods_per_year: int
    mean_period_return: float
    sample_volatility: float
    annualized_volatility: float
    provenance: RiskDataProvenance

    def __post_init__(self) -> None:
        for field_name in ("ledger_id", "portfolio_name"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        validate_aware_datetime(self.as_of, field_name="as_of")
        for field_name in ("currency", "period"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name, uppercase=True
                ),
            )
        if (
            isinstance(self.observation_count, bool)
            or not isinstance(self.observation_count, int)
            or self.observation_count < 2
        ):
            raise ValueError("observation_count must be an integer of at least two")
        if (
            isinstance(self.periods_per_year, bool)
            or not isinstance(self.periods_per_year, int)
            or self.periods_per_year <= 0
        ):
            raise ValueError("periods_per_year must be a positive integer")
        for name in (
            "mean_period_return",
            "sample_volatility",
            "annualized_volatility",
        ):
            object.__setattr__(
                self, name, validate_finite_number(getattr(self, name), field_name=name)
            )
        if self.sample_volatility < 0 or self.annualized_volatility < 0:
            raise ValueError("volatility values must be non-negative")
        expected = self.sample_volatility * sqrt(self.periods_per_year)
        if not isclose(self.annualized_volatility, expected, rel_tol=0, abs_tol=1e-12):
            raise ValueError(
                "annualized_volatility must match the explicit annualization factor"
            )
        if not isinstance(self.provenance, RiskDataProvenance):
            raise TypeError("provenance must be a RiskDataProvenance")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "as_of": self.as_of.isoformat(),
            "currency": self.currency,
            "period": self.period,
            "observation_count": self.observation_count,
            "periods_per_year": self.periods_per_year,
            "mean_period_return": self.mean_period_return,
            "sample_volatility": self.sample_volatility,
            "annualized_volatility": self.annualized_volatility,
            "provenance": self.provenance.to_dict(),
        }


class PortfolioVolatilityCalculator:
    @staticmethod
    def calculate(
        risk_input: PortfolioRiskInput, *, periods_per_year: int
    ) -> PortfolioVolatilityAnalysis:
        if not isinstance(risk_input, PortfolioRiskInput):
            raise TypeError("risk_input must be a PortfolioRiskInput")
        if (
            isinstance(periods_per_year, bool)
            or not isinstance(periods_per_year, int)
            or periods_per_year <= 0
        ):
            raise ValueError("periods_per_year must be a positive integer")
        values = tuple(
            item.return_fraction for item in risk_input.portfolio_returns.observations
        )
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        sample = sqrt(variance)
        series = risk_input.portfolio_returns
        return PortfolioVolatilityAnalysis(
            risk_input.ledger_id,
            risk_input.portfolio_name,
            risk_input.as_of,
            series.currency,
            series.period,
            len(values),
            periods_per_year,
            mean,
            sample,
            sample * sqrt(periods_per_year),
            series.provenance,
        )
