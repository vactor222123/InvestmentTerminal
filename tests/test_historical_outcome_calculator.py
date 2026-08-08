"""
Tests for the pure single-recommendation outcome calculator.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalOutcomeEvidence,
)


ORIGIN_AT = datetime(
    2026,
    8,
    3,
    20,
    0,
    tzinfo=timezone.utc,
)
ENDPOINT_AT = ORIGIN_AT + timedelta(
    days=5
)


def evidence(
    *,
    origin_price: float | None = 100.0,
    endpoint_price: float | None = 105.0,
) -> HistoricalOutcomeEvidence:
    return HistoricalOutcomeEvidence(
        instrument_key="IWDA",
        origin_at=ORIGIN_AT,
        endpoint_at=(
            ENDPOINT_AT
            if endpoint_price is not None
            else None
        ),
        origin_price=origin_price,
        endpoint_price=endpoint_price,
        origin_source=(
            "LOCAL_CANDLE_REPOSITORY_CLOSE"
            if origin_price is not None
            else None
        ),
        endpoint_source=(
            "LOCAL_CANDLE_REPOSITORY_CLOSE"
            if endpoint_price is not None
            else None
        ),
        origin_currency=(
            "EUR"
            if origin_price is not None
            else None
        ),
        endpoint_currency=(
            "EUR"
            if endpoint_price is not None
            else None
        ),
        origin_resolution=(
            "D"
            if origin_price is not None
            else None
        ),
        endpoint_resolution=(
            "D"
            if endpoint_price is not None
            else None
        ),
    )


def test_calculates_positive_raw_price_movement() -> None:
    result = HistoricalRecommendationOutcomeCalculator().calculate(
        evidence=evidence(
            origin_price=100.0,
            endpoint_price=105.0,
        ),
        origin_currency=" eur ",
        endpoint_currency="EUR",
    )

    assert result.instrument_key == "IWDA"
    assert result.currency == "EUR"
    assert result.origin_price == 100.0
    assert result.endpoint_price == 105.0
    assert result.price_change == 5.0
    assert result.price_change_fraction == pytest.approx(
        0.05
    )


def test_calculates_negative_raw_price_movement() -> None:
    result = HistoricalRecommendationOutcomeCalculator().calculate(
        evidence=evidence(
            origin_price=100.0,
            endpoint_price=90.0,
        ),
        origin_currency="EUR",
        endpoint_currency="EUR",
    )

    assert result.price_change == -10.0
    assert result.price_change_fraction == pytest.approx(
        -0.10
    )


def test_calculates_zero_movement() -> None:
    result = HistoricalRecommendationOutcomeCalculator().calculate(
        evidence=evidence(
            origin_price=100.0,
            endpoint_price=100.0,
        ),
        origin_currency="EUR",
        endpoint_currency="EUR",
    )

    assert result.price_change == 0.0
    assert result.price_change_fraction == 0.0


def test_incomplete_evidence_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="complete origin and endpoint prices are required",
    ):
        HistoricalRecommendationOutcomeCalculator().calculate(
            evidence=evidence(
                endpoint_price=None,
            ),
            origin_currency="EUR",
            endpoint_currency="EUR",
        )


def test_currency_mismatch_is_rejected_without_fx_assumption() -> None:
    with pytest.raises(
        ValueError,
        match="FX-adjusted outcome calculation is not supported",
    ):
        HistoricalRecommendationOutcomeCalculator().calculate(
            evidence=evidence(),
            origin_currency="EUR",
            endpoint_currency="USD",
        )


def test_calculator_does_not_interpret_recommendation_action() -> None:
    result = HistoricalRecommendationOutcomeCalculator().calculate(
        evidence=evidence(
            origin_price=100.0,
            endpoint_price=90.0,
        ),
        origin_currency="EUR",
        endpoint_currency="EUR",
    )

    data = result.to_dict()

    assert "success" not in data
    assert "failure" not in data
    assert "action" not in data
    assert "performance" not in data
    assert "annualized" not in data


def test_result_preserves_provenance() -> None:
    result = HistoricalRecommendationOutcomeCalculator().calculate(
        evidence=evidence(),
        origin_currency="EUR",
        endpoint_currency="EUR",
    )

    assert result.origin_source == (
        "LOCAL_CANDLE_REPOSITORY_CLOSE"
    )
    assert result.endpoint_source == (
        "LOCAL_CANDLE_REPOSITORY_CLOSE"
    )


def test_result_is_json_ready() -> None:
    result = HistoricalRecommendationOutcomeCalculator().calculate(
        evidence=evidence(),
        origin_currency="EUR",
        endpoint_currency="EUR",
    )

    assert result.to_dict() == {
        "instrument_key": "IWDA",
        "currency": "EUR",
        "origin_price": 100.0,
        "endpoint_price": 105.0,
        "price_change": 5.0,
        "price_change_fraction": pytest.approx(
            0.05
        ),
        "origin_source": "LOCAL_CANDLE_REPOSITORY_CLOSE",
        "endpoint_source": "LOCAL_CANDLE_REPOSITORY_CLOSE",
    }


def test_result_rejects_inconsistent_derived_values() -> None:
    with pytest.raises(
        ValueError,
        match="price_change must match",
    ):
        HistoricalRecommendationOutcome(
            instrument_key="IWDA",
            currency="EUR",
            origin_price=100.0,
            endpoint_price=105.0,
            price_change=4.0,
            price_change_fraction=0.05,
            origin_source="history",
            endpoint_source="history",
        )
