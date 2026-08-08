"""
Regression tests for enriched historical outcome evidence provenance.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_outcome_models import (
    HistoricalOutcomeEvidence,
)


ORIGIN = datetime(
    2026,
    8,
    3,
    20,
    0,
    tzinfo=timezone.utc,
)
ENDPOINT = ORIGIN + timedelta(
    days=5
)


def test_evidence_preserves_currency_and_resolution_provenance() -> None:
    evidence = HistoricalOutcomeEvidence(
        instrument_key="IWDA",
        origin_at=ORIGIN,
        endpoint_at=ENDPOINT,
        origin_price=100.0,
        endpoint_price=105.0,
        origin_source="history",
        endpoint_source="history",
        origin_currency="eur",
        endpoint_currency="EUR",
        origin_resolution="d",
        endpoint_resolution="D",
    )

    assert evidence.origin_currency == "EUR"
    assert evidence.endpoint_currency == "EUR"
    assert evidence.origin_resolution == "D"
    assert evidence.endpoint_resolution == "D"


def test_price_requires_complete_provenance() -> None:
    with pytest.raises(
        ValueError,
        match="origin_currency is required",
    ):
        HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=None,
            origin_price=100.0,
            endpoint_price=None,
            origin_source="history",
            endpoint_source=None,
            origin_currency=None,
            endpoint_currency=None,
            origin_resolution="D",
            endpoint_resolution=None,
        )


def test_provenance_without_price_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="origin provenance requires origin_price",
    ):
        HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=None,
            origin_price=None,
            endpoint_price=None,
            origin_source="history",
            endpoint_source=None,
            origin_currency=None,
            endpoint_currency=None,
            origin_resolution=None,
            endpoint_resolution=None,
        )
