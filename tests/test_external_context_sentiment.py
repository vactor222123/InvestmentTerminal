"""Tests for provider-independent external-context sentiment evidence."""

from datetime import datetime, timezone

import pytest

from investment_terminal.context.external_context_sentiment import (
    ExternalContextSentimentEvidence,
)


ASSESSED_AT = datetime(2026, 8, 17, tzinfo=timezone.utc)


def sentiment(**overrides) -> ExternalContextSentimentEvidence:
    values = {
        "context_id": "context-1",
        "label": "positive",
        "score": 0.6,
        "confidence": 0.8,
        "assessed_at": ASSESSED_AT,
        "method": "provider_model",
        "method_version": "2026-08",
        "reasons": (),
    }
    values.update(overrides)
    return ExternalContextSentimentEvidence(**values)


def test_sentiment_is_normalized_traceable_and_json_ready() -> None:
    value = sentiment()

    assert value.label == "POSITIVE"
    assert value.is_quantified is True
    assert value.to_dict() == {
        "context_id": "context-1",
        "label": "POSITIVE",
        "score": 0.6,
        "confidence": 0.8,
        "assessed_at": ASSESSED_AT.isoformat(),
        "method": "provider_model",
        "method_version": "2026-08",
        "reasons": [],
        "is_quantified": True,
    }


def test_unknown_sentiment_preserves_missing_quantification() -> None:
    value = sentiment(
        label="UNKNOWN",
        score=None,
        confidence=None,
        reasons=("Evidence is contradictory.",),
    )

    assert value.is_quantified is False
    assert value.reasons == ("Evidence is contradictory.",)


@pytest.mark.parametrize(
    ("field", "value"),
    [("score", -1.01), ("score", 1.01), ("confidence", -0.01),
     ("confidence", 1.01)],
)
def test_sentiment_rejects_out_of_range_numbers(
    field: str,
    value: float,
) -> None:
    with pytest.raises(ValueError, match=field):
        sentiment(**{field: value})


def test_unknown_and_mixed_sentiment_require_reasons() -> None:
    with pytest.raises(ValueError, match="reasons"):
        sentiment(label="MIXED", reasons=())


def test_sentiment_rejects_naive_assessment_time() -> None:
    with pytest.raises(ValueError, match="assessed_at"):
        sentiment(assessed_at=datetime(2026, 8, 17))
