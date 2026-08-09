"""
Tests for methodology-aware historical outcome aggregation.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_methodology_aware_aggregation import (
    HistoricalMethodologyOutcomeAggregator,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalEvidenceSelectionPolicy,
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)


def methodology(
    methodology_id: str,
    *,
    version: int = 1,
    kind: str = "ELAPSED_DAYS",
) -> HistoricalOutcomeMethodology:
    if kind == "TRADING_SESSIONS":
        endpoint = "TRADING_SESSION_CLOSE"
        selection = "SESSION_CLOSE_EXACT"
    else:
        endpoint = "ELAPSED_DURATION_UTC"
        selection = "EXACT_TIMESTAMP_CLOSE"

    return HistoricalOutcomeMethodology(
        methodology_id=methodology_id,
        version=version,
        window_kind=kind,
        endpoint_policy=HistoricalEndpointPolicy(
            policy_id=endpoint,
            version=1,
        ),
        evidence_selection_policy=HistoricalEvidenceSelectionPolicy(
            policy_id=selection,
            version=1,
            price_field="CLOSE",
        ),
    )


def result(
    *,
    methodology_value: HistoricalOutcomeMethodology,
    status: str,
    action: str,
    origin_day: int,
    movement: float | None = None,
) -> HistoricalMethodologyAwareObservationResult:
    origin = datetime(
        2026,
        8,
        origin_day,
        12,
        0,
        tzinfo=timezone.utc,
    )
    endpoint = origin + timedelta(days=5)

    evidence = None
    outcome = None

    if status == "COMPLETE":
        assert movement is not None
        origin_price = 100.0
        endpoint_price = origin_price * (1.0 + movement)
        price_change = endpoint_price - origin_price
        price_change_fraction = (
            endpoint_price / origin_price
        ) - 1.0

        evidence = HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=origin,
            endpoint_at=endpoint,
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            origin_source="fixture",
            endpoint_source="fixture",
            origin_currency="EUR",
            endpoint_currency="EUR",
            origin_resolution="D",
            endpoint_resolution="D",
        )
        outcome = HistoricalRecommendationOutcome(
            instrument_key="IWDA",
            currency="EUR",
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            price_change=price_change,
            price_change_fraction=price_change_fraction,
            origin_source="fixture",
            endpoint_source="fixture",
        )

    return HistoricalMethodologyAwareObservationResult(
        methodology=methodology_value,
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=(
                f"11111111-1111-4111-8111-{origin_day:012d}"
            ),
            recommendation_key="WORLD",
            symbol="IWDA",
            action=action,
            origin_at=origin,
            window=HistoricalObservationWindow(
                kind=methodology_value.window_kind,
                value=5,
            ),
            status=status,
            evidence=evidence,
            warnings=("fixture",),
        ),
        outcome=outcome,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def test_summarize_one_keeps_exact_methodology_identity() -> None:
    m = methodology("ELAPSED_DAYS_EXACT_CLOSE")
    summary = HistoricalMethodologyOutcomeAggregator().summarize_one(
        (
            result(
                methodology_value=m,
                status="COMPLETE",
                action="BUY",
                origin_day=1,
                movement=0.10,
            ),
            result(
                methodology_value=m,
                status="COMPLETE",
                action="HOLD",
                origin_day=2,
                movement=-0.05,
            ),
            result(
                methodology_value=m,
                status="NOT_MATURE",
                action="BUY",
                origin_day=3,
            ),
        )
    )

    assert summary.methodology.identity_key == (
        "ELAPSED_DAYS_EXACT_CLOSE@1"
    )
    assert summary.total_count == 3
    assert summary.complete_count == 2
    assert summary.not_mature_count == 1
    assert summary.coverage_fraction == pytest.approx(2 / 3)
    assert summary.mean_price_change_fraction == pytest.approx(0.025)
    assert summary.median_price_change_fraction == pytest.approx(0.025)
    assert [item.to_dict() for item in summary.action_counts] == [
        {"action": "BUY", "count": 2},
        {"action": "HOLD", "count": 1},
    ]


def test_summarize_one_rejects_mixed_methodology_identity() -> None:
    elapsed = methodology("ELAPSED_DAYS_EXACT_CLOSE")
    sessions = methodology(
        "TRADING_SESSIONS_EXACT_CLOSE",
        kind="TRADING_SESSIONS",
    )

    with pytest.raises(
        ValueError,
        match="mixed methodology identities",
    ):
        HistoricalMethodologyOutcomeAggregator().summarize_one(
            (
                result(
                    methodology_value=elapsed,
                    status="NOT_MATURE",
                    action="BUY",
                    origin_day=1,
                ),
                result(
                    methodology_value=sessions,
                    status="NOT_MATURE",
                    action="BUY",
                    origin_day=2,
                ),
            )
        )


def test_grouped_summary_separates_incompatible_methodologies() -> None:
    elapsed = methodology("ELAPSED_DAYS_EXACT_CLOSE")
    sessions = methodology(
        "TRADING_SESSIONS_EXACT_CLOSE",
        kind="TRADING_SESSIONS",
    )

    summaries = HistoricalMethodologyOutcomeAggregator().summarize_grouped(
        (
            result(
                methodology_value=sessions,
                status="NOT_MATURE",
                action="HOLD",
                origin_day=3,
            ),
            result(
                methodology_value=elapsed,
                status="COMPLETE",
                action="BUY",
                origin_day=1,
                movement=0.05,
            ),
            result(
                methodology_value=sessions,
                status="PARTIAL",
                action="BUY",
                origin_day=2,
            ),
        )
    )

    assert [
        summary.methodology.identity_key
        for summary in summaries
    ] == [
        "ELAPSED_DAYS_EXACT_CLOSE@1",
        "TRADING_SESSIONS_EXACT_CLOSE@1",
    ]
    assert [summary.total_count for summary in summaries] == [1, 2]


def test_different_versions_are_not_silently_mixed() -> None:
    v1 = methodology("TEST", version=1)
    v2 = methodology("TEST", version=2)

    summaries = HistoricalMethodologyOutcomeAggregator().summarize_grouped(
        (
            result(
                methodology_value=v2,
                status="NOT_MATURE",
                action="BUY",
                origin_day=2,
            ),
            result(
                methodology_value=v1,
                status="NOT_MATURE",
                action="BUY",
                origin_day=1,
            ),
        )
    )

    assert [
        summary.methodology.identity_key
        for summary in summaries
    ] == [
        "TEST@1",
        "TEST@2",
    ]


def test_empty_grouped_summary_is_empty() -> None:
    assert HistoricalMethodologyOutcomeAggregator().summarize_grouped(
        ()
    ) == ()


def test_summarize_one_rejects_empty_input() -> None:
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        HistoricalMethodologyOutcomeAggregator().summarize_one(
            ()
        )


def test_summary_json_keeps_non_effectiveness_semantics() -> None:
    m = methodology("ELAPSED_DAYS_EXACT_CLOSE")
    summary = HistoricalMethodologyOutcomeAggregator().summarize_one(
        (
            result(
                methodology_value=m,
                status="COMPLETE",
                action="BUY",
                origin_day=1,
                movement=0.05,
            ),
        )
    )

    data = summary.to_dict()

    assert data["methodology"]["identity_key"] == (
        "ELAPSED_DAYS_EXACT_CLOSE@1"
    )
    assert "one exact methodology identity only" in data[
        "metric_semantics"
    ]
    assert "not portfolio performance" in data[
        "metric_semantics"
    ]
    assert "effectiveness" in data[
        "metric_semantics"
    ]
