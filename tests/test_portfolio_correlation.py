from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_correlation import (
    PortfolioCorrelationAnalysis,
    PortfolioCorrelationCalculator,
    PortfolioCorrelationPair,
)
from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    ReturnObservation,
    ReturnSeries,
    RiskDataProvenance,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, tzinfo=timezone.utc)


def series(
    subject_type: str,
    subject_key: str,
    values: tuple[float, ...],
    *,
    currency: str = "EUR",
    period: str = "DAILY",
    start_day: int = 1,
) -> ReturnSeries:
    return ReturnSeries(
        subject_type,
        subject_key,
        currency,
        period,
        tuple(
            ReturnObservation(ts(day), ts(day + 1), value)
            for day, value in enumerate(values, start_day)
        ),
        RiskDataProvenance("test", subject_key, ts(10)),
    )


def risk_input(*instruments: ReturnSeries) -> PortfolioRiskInput:
    return PortfolioRiskInput(
        "main",
        "Personal",
        ts(12),
        series("PORTFOLIO", "main", (0.01, 0.02, 0.03)),
        tuple(instruments),
    )


def test_calculates_all_deterministically_ordered_pairwise_correlations() -> None:
    result = PortfolioCorrelationCalculator.calculate(
        risk_input(
            series("INSTRUMENT", "AAA", (0.02, 0.04, 0.06)),
            series("INSTRUMENT", "BBB", (-0.01, -0.02, -0.03)),
        )
    )
    assert [
        (item.left_subject_key, item.right_subject_key) for item in result.pairs
    ] == [
        ("AAA", "BBB"),
        ("MAIN", "AAA"),
        ("MAIN", "BBB"),
    ]
    assert [item.coefficient for item in result.pairs] == [-1.0, 1.0, -1.0]
    assert result.to_dict()["available_pair_count"] == 3
    assert result.as_of == ts(12)


@pytest.mark.parametrize(
    ("instrument", "reason", "count"),
    [
        (
            series("INSTRUMENT", "AAA", (0.01, 0.02), currency="USD"),
            "CURRENCY_MISMATCH",
            0,
        ),
        (
            series("INSTRUMENT", "AAA", (0.01, 0.02), period="WEEKLY"),
            "PERIOD_MISMATCH",
            0,
        ),
        (
            series("INSTRUMENT", "AAA", (0.01, 0.02), start_day=8),
            "INSUFFICIENT_OVERLAP",
            0,
        ),
        (series("INSTRUMENT", "AAA", (0.02, 0.02, 0.02)), "ZERO_VARIANCE", 3),
    ],
)
def test_unavailable_correlation_preserves_explicit_reason(
    instrument: ReturnSeries, reason: str, count: int
) -> None:
    pair = PortfolioCorrelationCalculator.calculate(risk_input(instrument)).pairs[0]
    assert pair.coefficient is None
    assert pair.unavailable_reason == reason
    assert pair.observation_count == count
    assert pair.available is False


def test_partial_overlap_uses_only_exact_period_keys() -> None:
    instrument = series("INSTRUMENT", "AAA", (0.04, 0.06, 0.08), start_day=2)
    pair = PortfolioCorrelationCalculator.calculate(risk_input(instrument)).pairs[0]
    assert pair.observation_count == 2
    assert pair.coefficient == 1.0


def test_empty_instrument_set_produces_explicit_empty_pair_set() -> None:
    result = PortfolioCorrelationCalculator.calculate(risk_input())
    assert result.pairs == ()
    assert result.to_dict()["pair_count"] == 0


def test_pair_rejects_coefficient_outside_correlation_bounds() -> None:
    provenance = RiskDataProvenance("test", "source", ts(10))
    with pytest.raises(ValueError, match="between -1 and 1"):
        PortfolioCorrelationPair(
            "PORTFOLIO",
            "main",
            "INSTRUMENT",
            "AAA",
            2,
            1.1,
            None,
            provenance,
            provenance,
        )


def test_analysis_requires_deterministically_ordered_pairs() -> None:
    result = PortfolioCorrelationCalculator.calculate(
        risk_input(
            series("INSTRUMENT", "AAA", (0.02, 0.04, 0.06)),
            series("INSTRUMENT", "BBB", (-0.01, -0.02, -0.03)),
        )
    )
    with pytest.raises(ValueError, match="deterministically ordered"):
        PortfolioCorrelationAnalysis(
            "main", "Personal", ts(12), tuple(reversed(result.pairs))
        )


def test_calculator_requires_portfolio_risk_input() -> None:
    with pytest.raises(TypeError, match="PortfolioRiskInput"):
        PortfolioCorrelationCalculator.calculate(object())  # type: ignore[arg-type]
