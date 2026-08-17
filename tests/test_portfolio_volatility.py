from datetime import datetime, timezone
from math import sqrt

import pytest

from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    ReturnObservation,
    ReturnSeries,
    RiskDataProvenance,
)
from investment_terminal.portfolio.portfolio_volatility import (
    PortfolioVolatilityAnalysis,
    PortfolioVolatilityCalculator,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, tzinfo=timezone.utc)


def source(*values: float) -> PortfolioRiskInput:
    observations = tuple(
        ReturnObservation(ts(i), ts(i + 1), value) for i, value in enumerate(values, 1)
    )
    series = ReturnSeries(
        "PORTFOLIO",
        "main",
        "EUR",
        "DAILY",
        observations,
        RiskDataProvenance("test", "returns", ts(5)),
    )
    return PortfolioRiskInput("main", "Personal", ts(6), series, ())


def test_calculates_sample_and_explicit_annualized_volatility() -> None:
    result = PortfolioVolatilityCalculator.calculate(
        source(0.01, 0.03), periods_per_year=252
    )
    assert result.mean_period_return == pytest.approx(0.02)
    assert result.sample_volatility == pytest.approx(sqrt(0.0002))
    assert result.annualized_volatility == pytest.approx(sqrt(0.0002) * sqrt(252))
    assert result.as_of == ts(6)
    assert result.provenance == source(0.01, 0.03).portfolio_returns.provenance
    assert result.to_dict()["periods_per_year"] == 252
    assert result.to_dict()["as_of"] == ts(6).isoformat()


def test_zero_volatility_is_explicit() -> None:
    assert (
        PortfolioVolatilityCalculator.calculate(
            source(0.02, 0.02), periods_per_year=12
        ).annualized_volatility
        == 0
    )


@pytest.mark.parametrize("value", [0, -1, True, 12.0])
def test_annualization_factor_must_be_explicit_positive_integer(value: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        PortfolioVolatilityCalculator.calculate(source(0.01, 0.02), periods_per_year=value)  # type: ignore[arg-type]


def test_analysis_rejects_inconsistent_annualization() -> None:
    provenance = source(0.01, 0.02).portfolio_returns.provenance
    with pytest.raises(ValueError, match="annualization factor"):
        PortfolioVolatilityAnalysis(
            "main",
            "Personal",
            ts(6),
            "EUR",
            "DAILY",
            2,
            252,
            0.015,
            0.01,
            0.01,
            provenance,
        )


@pytest.mark.parametrize("value", [True, 2.0, 1])
def test_analysis_requires_integer_observation_count_of_at_least_two(
    value: object,
) -> None:
    provenance = source(0.01, 0.02).portfolio_returns.provenance
    with pytest.raises(ValueError, match="integer of at least two"):
        PortfolioVolatilityAnalysis(
            "main",
            "Personal",
            ts(6),
            "EUR",
            "DAILY",
            value,  # type: ignore[arg-type]
            252,
            0.015,
            0.01,
            0.01 * sqrt(252),
            provenance,
        )


def test_calculator_requires_risk_input() -> None:
    with pytest.raises(TypeError, match="PortfolioRiskInput"):
        PortfolioVolatilityCalculator.calculate(object(), periods_per_year=252)  # type: ignore[arg-type]
