"""
Tests for read-only methodology-aware outcome filtering.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
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
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
    HistoricalOutcomeQueryService,
)


def methodology(
    methodology_id: str,
    *,
    version: int = 1,
    window_kind: str = "ELAPSED_DAYS",
) -> HistoricalOutcomeMethodology:
    if window_kind == "TRADING_SESSIONS":
        endpoint = "TRADING_SESSION_CLOSE"
        selection = "SESSION_CLOSE_EXACT"
    else:
        endpoint = "ELAPSED_DURATION_UTC"
        selection = "EXACT_TIMESTAMP_CLOSE"

    return HistoricalOutcomeMethodology(
        methodology_id=methodology_id,
        version=version,
        window_kind=window_kind,
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


def observation_evidence(
    *,
    symbol: str,
    origin: datetime,
    status: str,
) -> HistoricalOutcomeEvidence | None:
    if status == HistoricalRecommendationObservation.COMPLETE:
        return HistoricalOutcomeEvidence(
            instrument_key=symbol,
            origin_at=origin,
            endpoint_at=origin + timedelta(days=5),
            origin_price=100.0,
            endpoint_price=105.0,
            origin_source="fixture",
            endpoint_source="fixture",
            origin_currency="EUR",
            endpoint_currency="EUR",
            origin_resolution="D",
            endpoint_resolution="D",
        )
    return None


def result(
    *,
    key: str,
    symbol: str,
    action: str,
    status: str,
    kind: str,
    value: int,
    methodology_id: str,
    methodology_version: int,
    origin_day: int,
) -> HistoricalMethodologyAwareObservationResult:
    origin = datetime(
        2026,
        8,
        origin_day,
        12,
        0,
        tzinfo=timezone.utc,
    )
    return HistoricalMethodologyAwareObservationResult(
        methodology=methodology(
            methodology_id,
            version=methodology_version,
            window_kind=kind,
        ),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=(
                f"11111111-1111-4111-8111-{origin_day:012d}"
            ),
            recommendation_key=key,
            symbol=symbol,
            action=action,
            origin_at=origin,
            window=HistoricalObservationWindow(
                kind=kind,
                value=value,
            ),
            status=status,
            evidence=observation_evidence(
                symbol=symbol,
                origin=origin,
                status=status,
            ),
            warnings=("fixture",),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


@pytest.fixture
def results():
    return (
        result(
            key="WORLD",
            symbol="IWDA",
            action="BUY",
            status="COMPLETE",
            kind="ELAPSED_DAYS",
            value=5,
            methodology_id="ELAPSED_DAYS_EXACT_CLOSE",
            methodology_version=1,
            origin_day=1,
        ),
        result(
            key="WORLD",
            symbol="IWDA",
            action="HOLD",
            status="PARTIAL",
            kind="TRADING_SESSIONS",
            value=5,
            methodology_id="TRADING_SESSIONS_EXACT_CLOSE",
            methodology_version=1,
            origin_day=5,
        ),
        result(
            key="TECH",
            symbol="QQQ",
            action="BUY",
            status="NOT_MATURE",
            kind="TRADING_SESSIONS",
            value=10,
            methodology_id="TRADING_SESSIONS_EXACT_CLOSE",
            methodology_version=2,
            origin_day=10,
        ),
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (HistoricalOutcomeQuery(recommendation_key="world"), 2),
        (HistoricalOutcomeQuery(symbol="iwda"), 2),
        (HistoricalOutcomeQuery(action="buy"), 2),
        (HistoricalOutcomeQuery(status="partial"), 1),
        (HistoricalOutcomeQuery(window_kind="trading_sessions"), 2),
        (HistoricalOutcomeQuery(window_value=5), 2),
        (
            HistoricalOutcomeQuery(
                methodology_id="trading_sessions_exact_close"
            ),
            2,
        ),
        (HistoricalOutcomeQuery(methodology_version=2), 1),
    ],
)
def test_individual_filters(results, query, expected) -> None:
    filtered = HistoricalOutcomeQueryService().filter(
        results,
        query=query,
    )
    assert len(filtered) == expected


def test_filters_compose_with_and_semantics(results) -> None:
    filtered = HistoricalOutcomeQueryService().filter(
        results,
        query=HistoricalOutcomeQuery(
            symbol="IWDA",
            action="HOLD",
            status="PARTIAL",
            window_kind="TRADING_SESSIONS",
            window_value=5,
            methodology_id="TRADING_SESSIONS_EXACT_CLOSE",
            methodology_version=1,
        ),
    )

    assert len(filtered) == 1
    assert filtered[0].observation.action == "HOLD"


def test_origin_range_is_inclusive(results) -> None:
    filtered = HistoricalOutcomeQueryService().filter(
        results,
        query=HistoricalOutcomeQuery(
            origin_from=datetime(
                2026, 8, 5, 12, 0, tzinfo=timezone.utc
            ),
            origin_to=datetime(
                2026, 8, 10, 12, 0, tzinfo=timezone.utc
            ),
        ),
    )

    assert len(filtered) == 2


def test_filter_preserves_input_order(results) -> None:
    filtered = HistoricalOutcomeQueryService().filter(
        results,
        query=HistoricalOutcomeQuery(
            window_kind="TRADING_SESSIONS",
        ),
    )

    assert [item.observation.symbol for item in filtered] == [
        "IWDA",
        "QQQ",
    ]


def test_empty_query_returns_all_results(results) -> None:
    filtered = HistoricalOutcomeQueryService().filter(
        results,
        query=HistoricalOutcomeQuery(),
    )
    assert filtered == results


def test_invalid_origin_range_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="origin_from must not be later",
    ):
        HistoricalOutcomeQuery(
            origin_from=datetime(
                2026, 8, 10, tzinfo=timezone.utc
            ),
            origin_to=datetime(
                2026, 8, 1, tzinfo=timezone.utc
            ),
        )


def test_query_is_json_ready() -> None:
    query = HistoricalOutcomeQuery(
        symbol="iwda",
        window_kind="trading_sessions",
        methodology_version=1,
    )

    data = query.to_dict()

    assert data["symbol"] == "IWDA"
    assert data["window_kind"] == "TRADING_SESSIONS"
    assert data["methodology_version"] == 1
