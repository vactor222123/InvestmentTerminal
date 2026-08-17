"""Tests for deterministic portfolio drawdown analysis."""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_drawdown import (
    PortfolioDrawdownAnalysis,
    PortfolioDrawdownCalculator,
    PortfolioDrawdownPoint,
)
from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    ReturnObservation,
    ReturnSeries,
    RiskDataProvenance,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def risk_input(*returns: float) -> PortfolioRiskInput:
    observations = tuple(
        ReturnObservation(ts(index), ts(index + 1), value)
        for index, value in enumerate(returns, start=1)
    )
    series = ReturnSeries(
        subject_type="PORTFOLIO",
        subject_key="main",
        currency="EUR",
        period="DAILY",
        observations=observations,
        provenance=RiskDataProvenance("valuation-history", "series-v1", ts(8)),
    )
    return PortfolioRiskInput("main", "Personal", ts(9), series, ())


def test_calculator_compounds_returns_and_finds_recovered_episode() -> None:
    result = PortfolioDrawdownCalculator.calculate(risk_input(0.10, -0.20, -0.10, 0.50))
    assert tuple(round(item.cumulative_growth_factor, 3) for item in result.points) == (
        1.1,
        0.88,
        0.792,
        1.188,
    )
    assert result.max_drawdown_fraction == pytest.approx(-0.28)
    assert result.peak_at == ts(2)
    assert result.trough_at == ts(4)
    assert result.recovered_at == ts(5)
    assert result.recovered is True


def test_unrecovered_episode_remains_explicit() -> None:
    result = PortfolioDrawdownCalculator.calculate(risk_input(0.10, -0.20, 0.05))
    assert result.max_drawdown_fraction == pytest.approx(-0.20)
    assert result.peak_at == ts(2)
    assert result.trough_at == ts(3)
    assert result.recovered_at is None
    assert result.to_dict()["recovered"] is False


def test_initial_loss_uses_series_start_as_peak() -> None:
    result = PortfolioDrawdownCalculator.calculate(risk_input(-0.10, 0.20))
    assert result.peak_at == ts(1)
    assert result.trough_at == ts(2)
    assert result.recovered_at == ts(3)


def test_no_drawdown_has_no_synthetic_episode() -> None:
    result = PortfolioDrawdownCalculator.calculate(risk_input(0.10, 0.02))
    assert result.max_drawdown_fraction == 0
    assert result.peak_at is None
    assert result.trough_at is None
    assert result.recovered_at is None


def test_total_loss_is_bounded_at_negative_one() -> None:
    result = PortfolioDrawdownCalculator.calculate(risk_input(0.10, -1.0))
    assert result.max_drawdown_fraction == -1
    assert result.points[-1].cumulative_growth_factor == 0


def test_earliest_equal_worst_drawdown_is_retained() -> None:
    result = PortfolioDrawdownCalculator.calculate(risk_input(-0.10, 0.20, -0.10))
    assert result.trough_at == ts(2)


def test_calculator_preserves_identity_period_currency_and_provenance() -> None:
    source = risk_input(0.10, -0.05)
    result = PortfolioDrawdownCalculator.calculate(source)
    assert result.ledger_id == source.ledger_id
    assert result.portfolio_name == source.portfolio_name
    assert result.as_of == source.as_of
    assert result.currency == "EUR"
    assert result.period == "DAILY"
    assert result.provenance == source.portfolio_returns.provenance


def test_drawdown_point_rejects_inconsistent_evidence() -> None:
    with pytest.raises(ValueError, match="must match"):
        PortfolioDrawdownPoint(ts(2), 0.8, 1.0, -0.1)
    with pytest.raises(ValueError, match="between -1 and 0"):
        PortfolioDrawdownPoint(ts(2), 0.8, 1.0, 0.1)


def test_analysis_rejects_episode_for_zero_drawdown() -> None:
    point = PortfolioDrawdownPoint(ts(2), 1.1, 1.1, 0)
    with pytest.raises(ValueError, match="zero drawdown"):
        PortfolioDrawdownAnalysis(
            "main",
            "Personal",
            ts(3),
            "EUR",
            "DAILY",
            (point,),
            0,
            ts(1),
            ts(2),
            None,
            risk_input(0.1, 0.1).portfolio_returns.provenance,
        )


def test_calculator_requires_validated_risk_input() -> None:
    with pytest.raises(TypeError, match="PortfolioRiskInput"):
        PortfolioDrawdownCalculator.calculate(object())  # type: ignore[arg-type]
