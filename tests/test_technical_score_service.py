"""
Tests for TechnicalScoreService.
"""

from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisResult,
    TechnicalDataQuality,
)
from investment_terminal.services.technical_score_service import (
    TechnicalScoreService,
)


def create_analysis() -> TechnicalAnalysisResult:
    return TechnicalAnalysisResult(
        symbol="MSFT",
        resolution="D",
        timestamp=datetime(
            2026,
            7,
            31,
            tzinfo=timezone.utc,
        ),
        latest_price=464.72,
        currency="USD",
        sma20=396.87,
        sma50=399.40,
        sma200=433.58,
        ema20=402.19,
        rsi14=74.50,
        macd_line=9.30,
        macd_signal=1.83,
        macd_histogram=7.47,
        atr14=16.02,
        atr_percent=3.45,
        bollinger_upper=439.40,
        bollinger_middle=396.87,
        bollinger_lower=354.33,
        bollinger_bandwidth=21.43,
        price_above_sma20=True,
        price_above_sma50=True,
        price_above_sma200=True,
        sma50_above_sma200=False,
        trend="UPTREND",
        bollinger_position="ABOVE_UPPER_BAND",
        volatility_status="MODERATE",
        data_quality=TechnicalDataQuality(
            candle_count=251,
            recommended_candle_count=200,
            completeness_percent=100.0,
            missing_indicators=(),
            sufficient_for_long_term=True,
        ),
    )


def test_score_analysis_returns_transparent_score() -> None:
    service = TechnicalScoreService(
        analysis_service=Mock()
    )

    result = service.score_analysis(
        create_analysis()
    )

    assert result.symbol == "MSFT"
    assert result.raw_score == pytest.approx(65.0)
    assert result.final_score == pytest.approx(65.0)
    assert result.classification == "POSITIVE"

    assert result.breakdown.trend == 30.0
    assert result.breakdown.momentum == 22.0
    assert result.breakdown.volatility == 11.0
    assert result.breakdown.price_position == 2.0


def test_score_calls_analysis_service() -> None:
    analysis = create_analysis()

    analysis_service = Mock()
    analysis_service.analyze.return_value = analysis

    result = TechnicalScoreService(
        analysis_service=analysis_service
    ).score(
        symbol="msft",
        resolution="d",
    )

    assert result.symbol == "MSFT"

    analysis_service.analyze.assert_called_once_with(
        symbol="msft",
        resolution="d",
    )


def test_score_applies_data_quality_factor() -> None:
    analysis = replace(
        create_analysis(),
        data_quality=TechnicalDataQuality(
            candle_count=100,
            recommended_candle_count=200,
            completeness_percent=50.0,
            missing_indicators=("sma200",),
            sufficient_for_long_term=False,
        ),
    )

    result = TechnicalScoreService(
        analysis_service=Mock()
    ).score_analysis(analysis)

    assert result.raw_score == pytest.approx(65.0)
    assert result.data_quality_factor == pytest.approx(0.5)
    assert result.final_score == pytest.approx(32.5)
    assert result.classification == "WEAK"

    assert any(
        "Insufficient history" in factor
        for factor in result.risk_factors
    )


def test_strong_uptrend_can_receive_strong_score() -> None:
    analysis = replace(
        create_analysis(),
        trend="STRONG_UPTREND",
        sma50_above_sma200=True,
        rsi14=60.0,
        bollinger_position="UPPER_HALF",
        volatility_status="LOW",
    )

    result = TechnicalScoreService(
        analysis_service=Mock()
    ).score_analysis(analysis)

    assert result.final_score >= 75.0
    assert result.classification == "STRONG"


def test_bearish_analysis_receives_low_score() -> None:
    analysis = replace(
        create_analysis(),
        latest_price=300.0,
        ema20=350.0,
        rsi14=25.0,
        macd_histogram=-5.0,
        trend="STRONG_DOWNTREND",
        bollinger_position="BELOW_LOWER_BAND",
        volatility_status="HIGH",
    )

    result = TechnicalScoreService(
        analysis_service=Mock()
    ).score_analysis(analysis)

    assert result.final_score < 40.0
    assert result.classification in {
        "WEAK",
        "VERY_WEAK",
    }


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (80.0, "STRONG"),
        (65.0, "POSITIVE"),
        (50.0, "NEUTRAL"),
        (30.0, "WEAK"),
        (10.0, "VERY_WEAK"),
    ],
)
def test_score_classification(
    score: float,
    expected: str,
) -> None:
    assert (
        TechnicalScoreService._classify_score(score)
        == expected
    )


def test_score_rejects_invalid_analysis() -> None:
    service = TechnicalScoreService(
        analysis_service=Mock()
    )

    with pytest.raises(
        TypeError,
        match="TechnicalAnalysisResult",
    ):
        service.score_analysis(None)