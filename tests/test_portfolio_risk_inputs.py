"""Tests for provider-neutral portfolio risk inputs."""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    ReturnObservation,
    ReturnSeries,
    RiskDataProvenance,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def observations() -> tuple[ReturnObservation, ...]:
    return (
        ReturnObservation(ts(1), ts(2), 0.02),
        ReturnObservation(ts(2), ts(3), -0.01),
    )


def series(
    subject_type: str = "PORTFOLIO",
    subject_key: str = "main",
    *,
    values: tuple[ReturnObservation, ...] | None = None,
    fetched_at: datetime | None = None,
) -> ReturnSeries:
    return ReturnSeries(
        subject_type=subject_type,
        subject_key=subject_key,
        currency="eur",
        period="daily",
        observations=values or observations(),
        provenance=RiskDataProvenance(
            source="valuation-history",
            source_record_id=f"{subject_key}-returns-v1",
            fetched_at=fetched_at or ts(3),
        ),
    )


def test_return_observation_is_timezone_aware_and_loss_bounded() -> None:
    value = ReturnObservation(ts(1), ts(2), -1)
    assert value.to_dict()["return_fraction"] == -1
    with pytest.raises(ValueError, match="less than -1"):
        ReturnObservation(ts(1), ts(2), -1.01)
    with pytest.raises(ValueError, match="later than"):
        ReturnObservation(ts(2), ts(2), 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        ReturnObservation(datetime(2026, 8, 1), ts(2), 0)


def test_return_series_normalizes_identity_and_preserves_provenance() -> None:
    value = series()
    assert value.subject_type == "PORTFOLIO"
    assert value.subject_key == "MAIN"
    assert value.currency == "EUR"
    assert value.period == "DAILY"
    assert value.to_dict()["observation_count"] == 2
    assert value.to_dict()["provenance"]["source_record_id"] == "main-returns-v1"


def test_return_series_requires_supported_subject_and_period() -> None:
    with pytest.raises(ValueError, match="subject_type"):
        ReturnSeries(
            "BENCHMARK", "index", "EUR", "DAILY", observations(), series().provenance
        )
    with pytest.raises(ValueError, match="period"):
        ReturnSeries(
            "PORTFOLIO", "main", "EUR", "HOURLY", observations(), series().provenance
        )


def test_return_series_requires_at_least_two_ordered_unique_periods() -> None:
    first, second = observations()
    with pytest.raises(ValueError, match="at least two"):
        series(values=(first,))
    with pytest.raises(ValueError, match="ordered"):
        series(values=(second, first))
    with pytest.raises(ValueError, match="unique periods"):
        series(values=(first, first))


def test_return_series_rejects_overlapping_periods() -> None:
    values = (
        ReturnObservation(ts(1), ts(3), 0.02),
        ReturnObservation(ts(2), ts(4), 0.01),
    )
    with pytest.raises(ValueError, match="must not overlap"):
        series(values=values)


def test_portfolio_risk_input_preserves_distinct_currency_explicit_series() -> None:
    portfolio = series()
    instrument = series("INSTRUMENT", "IE00B4L5Y983")
    result = PortfolioRiskInput(
        ledger_id="main",
        portfolio_name="Personal",
        as_of=ts(4),
        portfolio_returns=portfolio,
        instrument_returns=(instrument,),
    )
    assert result.portfolio_returns == portfolio
    assert result.instrument_returns == (instrument,)
    assert result.to_dict()["instrument_series_count"] == 1


def test_portfolio_series_must_match_ledger_identity_and_subject_type() -> None:
    with pytest.raises(ValueError, match="PORTFOLIO subject_type"):
        PortfolioRiskInput("main", "Personal", ts(4), series("INSTRUMENT", "main"), ())
    with pytest.raises(ValueError, match="input ledger_id"):
        PortfolioRiskInput("main", "Personal", ts(4), series("PORTFOLIO", "other"), ())


def test_instrument_series_are_unique_and_ordered() -> None:
    first = series("INSTRUMENT", "AAA")
    second = series("INSTRUMENT", "BBB")
    with pytest.raises(ValueError, match="ordered by subject_key"):
        PortfolioRiskInput("main", "Personal", ts(4), series(), (second, first))
    with pytest.raises(ValueError, match="unique subject keys"):
        PortfolioRiskInput("main", "Personal", ts(4), series(), (first, first))


def test_instrument_collection_rejects_portfolio_subjects() -> None:
    with pytest.raises(ValueError, match="INSTRUMENT subject_type"):
        PortfolioRiskInput("main", "Personal", ts(4), series(), (series(),))


def test_as_of_rejects_future_observations_or_provenance() -> None:
    future_values = (
        ReturnObservation(ts(3), ts(4), 0.01),
        ReturnObservation(ts(4), ts(5), 0.02),
    )
    with pytest.raises(ValueError, match="observations"):
        PortfolioRiskInput("main", "Personal", ts(4), series(values=future_values), ())
    with pytest.raises(ValueError, match="provenance"):
        PortfolioRiskInput("main", "Personal", ts(4), series(fetched_at=ts(5)), ())
