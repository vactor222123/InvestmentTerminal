"""
Tests for transparent historical outcome descriptive statistics.
"""

from math import sqrt

import pytest

from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
)
from investment_terminal.history.historical_outcome_descriptive_summary import (
    HistoricalOutcomeDescriptiveSummary,
    HistoricalOutcomeDescriptiveSummaryService,
)


def outcome(
    fraction: float,
) -> HistoricalRecommendationOutcome:
    origin = 100.0
    endpoint = origin * (1.0 + fraction)
    return HistoricalRecommendationOutcome(
        instrument_key="IWDA",
        currency="EUR",
        origin_price=origin,
        endpoint_price=endpoint,
        price_change=endpoint - origin,
        price_change_fraction=(endpoint / origin) - 1.0,
        origin_source="fixture",
        endpoint_source="fixture",
    )


def test_empty_sample_returns_no_descriptive_summary() -> None:
    assert HistoricalOutcomeDescriptiveSummaryService().summarize(
        outcomes=(),
    ) is None


def test_single_observation_has_no_sample_standard_deviation() -> None:
    summary = HistoricalOutcomeDescriptiveSummaryService().summarize(
        outcomes=(
            outcome(0.05),
        ),
    )

    assert summary is not None
    assert summary.count == 1
    assert summary.mean_price_change_fraction == pytest.approx(0.05)
    assert summary.median_price_change_fraction == pytest.approx(0.05)
    assert summary.minimum_price_change_fraction == pytest.approx(0.05)
    assert summary.maximum_price_change_fraction == pytest.approx(0.05)
    assert summary.sample_standard_deviation is None
    assert summary.positive_movement_count == 1
    assert summary.negative_movement_count == 0
    assert summary.zero_movement_count == 0


def test_mixed_movements_have_deterministic_statistics() -> None:
    summary = HistoricalOutcomeDescriptiveSummaryService().summarize(
        outcomes=(
            outcome(-0.10),
            outcome(0.0),
            outcome(0.10),
        ),
    )

    assert summary is not None
    assert summary.count == 3
    assert summary.mean_price_change_fraction == pytest.approx(0.0)
    assert summary.median_price_change_fraction == pytest.approx(0.0)
    assert summary.minimum_price_change_fraction == pytest.approx(-0.10)
    assert summary.maximum_price_change_fraction == pytest.approx(0.10)
    assert summary.sample_standard_deviation == pytest.approx(0.10)
    assert summary.positive_movement_count == 1
    assert summary.negative_movement_count == 1
    assert summary.zero_movement_count == 1


def test_sample_standard_deviation_uses_n_minus_one() -> None:
    summary = HistoricalOutcomeDescriptiveSummaryService().summarize(
        outcomes=(
            outcome(0.0),
            outcome(0.02),
            outcome(0.04),
        ),
    )

    assert summary is not None
    expected = sqrt(
        (
            (0.0 - 0.02) ** 2
            + (0.02 - 0.02) ** 2
            + (0.04 - 0.02) ** 2
        )
        / 2
    )
    assert summary.sample_standard_deviation == pytest.approx(expected)


def test_order_does_not_change_summary() -> None:
    service = HistoricalOutcomeDescriptiveSummaryService()
    first = service.summarize(
        outcomes=(
            outcome(-0.05),
            outcome(0.03),
            outcome(0.01),
        ),
    )
    second = service.summarize(
        outcomes=(
            outcome(0.01),
            outcome(-0.05),
            outcome(0.03),
        ),
    )

    assert first == second


def test_serialization_contains_only_descriptive_movement_terms() -> None:
    summary = HistoricalOutcomeDescriptiveSummaryService().summarize(
        outcomes=(
            outcome(-0.02),
            outcome(0.04),
        ),
    )

    assert summary is not None
    serialized = summary.to_dict()

    assert serialized["count"] == 2
    assert serialized["positive_movement_count"] == 1
    assert serialized["negative_movement_count"] == 1
    assert "hit_rate" not in serialized
    assert "win_rate" not in serialized
    assert "accuracy" not in serialized
    assert "effectiveness" not in serialized


def test_summary_model_rejects_non_finite_statistics() -> None:
    with pytest.raises(
        ValueError,
        match="finite",
    ):
        HistoricalOutcomeDescriptiveSummary(
            count=1,
            mean_price_change_fraction=float("nan"),
            median_price_change_fraction=0.0,
            minimum_price_change_fraction=0.0,
            maximum_price_change_fraction=0.0,
            sample_standard_deviation=None,
            positive_movement_count=0,
            negative_movement_count=0,
            zero_movement_count=1,
        )


def test_summary_model_rejects_inconsistent_movement_counts() -> None:
    with pytest.raises(
        ValueError,
        match="movement counts",
    ):
        HistoricalOutcomeDescriptiveSummary(
            count=2,
            mean_price_change_fraction=0.0,
            median_price_change_fraction=0.0,
            minimum_price_change_fraction=-0.01,
            maximum_price_change_fraction=0.01,
            sample_standard_deviation=0.01,
            positive_movement_count=1,
            negative_movement_count=0,
            zero_movement_count=0,
        )


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeDescriptiveSummaryService()

    with pytest.raises(
        TypeError,
        match="outcomes",
    ):
        service.summarize(
            outcomes=[],  # type: ignore[arg-type]
        )

    with pytest.raises(
        TypeError,
        match="contain only",
    ):
        service.summarize(
            outcomes=(
                object(),  # type: ignore[arg-type]
            ),
        )
