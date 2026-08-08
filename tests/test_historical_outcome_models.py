"""
Tests for outcome-aware Historical Intelligence contracts.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
ORIGIN = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)
ENDPOINT = ORIGIN + timedelta(
    days=5
)


def test_observation_window_normalizes_without_calculating_endpoint() -> None:
    window = HistoricalObservationWindow(
        kind=" elapsed_time ",
        value=5,
    )

    assert window.kind == "ELAPSED_TIME"
    assert window.value == 5
    assert window.to_dict() == {
        "kind": "ELAPSED_TIME",
        "value": 5,
    }


@pytest.mark.parametrize(
    "value",
    (
        0,
        -1,
        True,
        1.5,
    ),
)
def test_observation_window_requires_positive_integer(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        HistoricalObservationWindow(
            kind="ELAPSED_TIME",
            value=value,  # type: ignore[arg-type]
        )


def test_complete_evidence_preserves_price_provenance() -> None:
    evidence = HistoricalOutcomeEvidence(
        instrument_key=" IWDA ",
        origin_at=ORIGIN,
        endpoint_at=ENDPOINT,
        origin_price=100,
        endpoint_price=105.5,
        origin_source=" local historical candles ",
        endpoint_source=" local historical candles ",
    )

    assert evidence.instrument_key == "IWDA"
    assert evidence.origin_price == 100.0
    assert evidence.endpoint_price == 105.5
    assert evidence.origin_source == "local historical candles"
    assert evidence.has_complete_prices

    assert evidence.to_dict()[
        "endpoint_at"
    ] == ENDPOINT.isoformat()


def test_evidence_requires_source_for_present_price() -> None:
    with pytest.raises(
        ValueError,
        match="origin_source is required",
    ):
        HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=None,
            origin_price=100.0,
            endpoint_price=None,
            origin_source=None,
            endpoint_source=None,
        )


def test_evidence_requires_endpoint_time_for_endpoint_price() -> None:
    with pytest.raises(
        ValueError,
        match="endpoint_at is required",
    ):
        HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=None,
            origin_price=None,
            endpoint_price=105.0,
            origin_source=None,
            endpoint_source="history",
        )


def test_evidence_rejects_non_positive_price() -> None:
    with pytest.raises(
        ValueError,
        match="origin_price must be a finite positive number",
    ):
        HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=None,
            origin_price=0.0,
            endpoint_price=None,
            origin_source="history",
            endpoint_source=None,
        )


def test_complete_observation_requires_complete_prices() -> None:
    with pytest.raises(
        ValueError,
        match="COMPLETE observation requires complete",
    ):
        HistoricalRecommendationObservation(
            origin_snapshot_id=SNAPSHOT_ID,
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind="ELAPSED_TIME",
                value=5,
            ),
            status="COMPLETE",
            evidence=None,
        )


def test_complete_observation_is_serializable_and_normalized() -> None:
    observation = HistoricalRecommendationObservation(
        origin_snapshot_id=SNAPSHOT_ID.upper(),
        recommendation_key=" WORLD ",
        symbol=" iwda ",
        action=" buy ",
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="elapsed_time",
            value=5,
        ),
        status=" complete ",
        evidence=HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=ENDPOINT,
            origin_price=100.0,
            endpoint_price=105.0,
            origin_source="history",
            endpoint_source="history",
        ),
        warnings=(
            "Raw price movement only; not portfolio performance",
        ),
    )

    assert observation.origin_snapshot_id == SNAPSHOT_ID
    assert observation.recommendation_key == "WORLD"
    assert observation.symbol == "IWDA"
    assert observation.action == "BUY"
    assert observation.status == "COMPLETE"
    assert observation.has_complete_outcome_evidence

    data = observation.to_dict()
    assert data[
        "window"
    ] == {
        "kind": "ELAPSED_TIME",
        "value": 5,
    }
    assert data[
        "warnings"
    ] == [
        "Raw price movement only; not portfolio performance",
    ]


@pytest.mark.parametrize(
    "status",
    (
        "PARTIAL",
        "UNAVAILABLE",
        "NOT_MATURE",
    ),
)
def test_non_complete_statuses_allow_incomplete_evidence(
    status: str,
) -> None:
    observation = HistoricalRecommendationObservation(
        origin_snapshot_id=SNAPSHOT_ID,
        recommendation_key="WORLD",
        symbol="IWDA",
        action="HOLD",
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=20,
        ),
        status=status,
        evidence=None,
    )

    assert observation.status == status
    assert not observation.has_complete_outcome_evidence


def test_not_mature_rejects_endpoint_price() -> None:
    evidence = HistoricalOutcomeEvidence(
        instrument_key="IWDA",
        origin_at=ORIGIN,
        endpoint_at=ENDPOINT,
        origin_price=100.0,
        endpoint_price=105.0,
        origin_source="history",
        endpoint_source="history",
    )

    with pytest.raises(
        ValueError,
        match="must not contain endpoint_price",
    ):
        HistoricalRecommendationObservation(
            origin_snapshot_id=SNAPSHOT_ID,
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind="ELAPSED_TIME",
                value=5,
            ),
            status="NOT_MATURE",
            evidence=evidence,
        )


def test_observation_rejects_mismatched_evidence_origin() -> None:
    evidence = HistoricalOutcomeEvidence(
        instrument_key="IWDA",
        origin_at=ORIGIN + timedelta(
            minutes=1
        ),
        endpoint_at=None,
        origin_price=100.0,
        endpoint_price=None,
        origin_source="history",
        endpoint_source=None,
    )

    with pytest.raises(
        ValueError,
        match="origin_at must match",
    ):
        HistoricalRecommendationObservation(
            origin_snapshot_id=SNAPSHOT_ID,
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind="ELAPSED_TIME",
                value=5,
            ),
            status="PARTIAL",
            evidence=evidence,
        )


def test_models_are_frozen() -> None:
    window = HistoricalObservationWindow(
        kind="ELAPSED_TIME",
        value=5,
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        window.value = 10  # type: ignore[misc]
