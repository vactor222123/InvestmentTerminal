"""
Transparent technical scoring service.
"""

from dataclasses import dataclass

from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisResult,
    TechnicalAnalysisService,
)


@dataclass(frozen=True, slots=True)
class TechnicalScoreBreakdown:
    """
    Individual technical-score components.
    """

    trend: float
    momentum: float
    volatility: float
    price_position: float

    trend_max: float = 40.0
    momentum_max: float = 30.0
    volatility_max: float = 15.0
    price_position_max: float = 15.0


@dataclass(frozen=True, slots=True)
class TechnicalScoreResult:
    """
    Normalized technical score with an auditable explanation.
    """

    symbol: str
    resolution: str

    raw_score: float
    data_quality_factor: float
    final_score: float
    classification: str

    breakdown: TechnicalScoreBreakdown
    positive_factors: tuple[str, ...]
    risk_factors: tuple[str, ...]


class TechnicalScoreService:
    """
    Convert TechnicalAnalysisResult into a transparent score.

    The score describes technical conditions only. It is not an
    investment recommendation.
    """

    def __init__(
        self,
        analysis_service: TechnicalAnalysisService,
    ) -> None:
        self.analysis_service = analysis_service

    def score(
        self,
        symbol: str,
        resolution: str = "D",
    ) -> TechnicalScoreResult:
        """
        Analyze an asset and calculate its technical score.
        """
        analysis = self.analysis_service.analyze(
            symbol=symbol,
            resolution=resolution,
        )

        return self.score_analysis(analysis)

    def score_analysis(
        self,
        analysis: TechnicalAnalysisResult,
    ) -> TechnicalScoreResult:
        """
        Score an already calculated technical-analysis snapshot.
        """
        if not isinstance(
            analysis,
            TechnicalAnalysisResult,
        ):
            raise TypeError(
                "analysis must be a TechnicalAnalysisResult"
            )

        positive_factors: list[str] = []
        risk_factors: list[str] = []

        trend_score = self._score_trend(
            analysis,
            positive_factors,
            risk_factors,
        )

        momentum_score = self._score_momentum(
            analysis,
            positive_factors,
            risk_factors,
        )

        volatility_score = self._score_volatility(
            analysis,
            positive_factors,
            risk_factors,
        )

        price_position_score = self._score_price_position(
            analysis,
            positive_factors,
            risk_factors,
        )

        breakdown = TechnicalScoreBreakdown(
            trend=trend_score,
            momentum=momentum_score,
            volatility=volatility_score,
            price_position=price_position_score,
        )

        raw_score = (
            trend_score
            + momentum_score
            + volatility_score
            + price_position_score
        )

        data_quality_factor = min(
            max(
                analysis.data_quality.completeness_percent
                / 100.0,
                0.0,
            ),
            1.0,
        )

        if analysis.data_quality.missing_indicators:
            risk_factors.append(
                "Some technical indicators are unavailable."
            )

        if not analysis.data_quality.sufficient_for_long_term:
            risk_factors.append(
                "Insufficient history for reliable long-term analysis."
            )

        final_score = raw_score * data_quality_factor

        return TechnicalScoreResult(
            symbol=analysis.symbol,
            resolution=analysis.resolution,
            raw_score=round(raw_score, 2),
            data_quality_factor=round(
                data_quality_factor,
                4,
            ),
            final_score=round(final_score, 2),
            classification=self._classify_score(
                final_score
            ),
            breakdown=breakdown,
            positive_factors=tuple(positive_factors),
            risk_factors=tuple(risk_factors),
        )

    @staticmethod
    def _score_trend(
        analysis: TechnicalAnalysisResult,
        positive_factors: list[str],
        risk_factors: list[str],
    ) -> float:
        scores = {
            "STRONG_UPTREND": 40.0,
            "UPTREND": 30.0,
            "NEUTRAL": 20.0,
            "DOWNTREND": 10.0,
            "STRONG_DOWNTREND": 0.0,
            "INSUFFICIENT_DATA": 0.0,
        }

        score = scores.get(
            analysis.trend,
            0.0,
        )

        if analysis.trend == "STRONG_UPTREND":
            positive_factors.append(
                "Price and moving averages form a strong uptrend."
            )
        elif analysis.trend == "UPTREND":
            positive_factors.append(
                "Price remains above the long-term moving average."
            )
        elif analysis.trend in {
            "DOWNTREND",
            "STRONG_DOWNTREND",
        }:
            risk_factors.append(
                "The moving-average structure is bearish."
            )
        elif analysis.trend == "INSUFFICIENT_DATA":
            risk_factors.append(
                "Trend cannot be fully classified."
            )

        if analysis.sma50_above_sma200 is True:
            positive_factors.append(
                "SMA50 is above SMA200."
            )
        elif analysis.sma50_above_sma200 is False:
            risk_factors.append(
                "SMA50 remains below SMA200."
            )

        return score

    @staticmethod
    def _score_momentum(
        analysis: TechnicalAnalysisResult,
        positive_factors: list[str],
        risk_factors: list[str],
    ) -> float:
        score = 0.0

        if analysis.macd_histogram is not None:
            if analysis.macd_histogram > 0:
                score += 12.0
                positive_factors.append(
                    "MACD histogram is positive."
                )
            elif analysis.macd_histogram < 0:
                score += 3.0
                risk_factors.append(
                    "MACD histogram is negative."
                )
            else:
                score += 6.0

        if analysis.rsi14 is not None:
            if 45.0 <= analysis.rsi14 <= 65.0:
                score += 12.0
                positive_factors.append(
                    "RSI is in a constructive momentum range."
                )
            elif (
                35.0 <= analysis.rsi14 < 45.0
                or 65.0 < analysis.rsi14 <= 70.0
            ):
                score += 8.0
            elif (
                30.0 <= analysis.rsi14 < 35.0
                or 70.0 < analysis.rsi14 <= 75.0
            ):
                score += 4.0

                if analysis.rsi14 > 70.0:
                    risk_factors.append(
                        "RSI indicates an overbought market."
                    )
            else:
                if analysis.rsi14 > 75.0:
                    risk_factors.append(
                        "RSI indicates strong overbought conditions."
                    )
                else:
                    risk_factors.append(
                        "RSI indicates strong downside momentum."
                    )

        if (
            analysis.ema20 is not None
            and analysis.latest_price > analysis.ema20
        ):
            score += 6.0
            positive_factors.append(
                "Price is above EMA20."
            )

        return min(score, 30.0)

    @staticmethod
    def _score_volatility(
        analysis: TechnicalAnalysisResult,
        positive_factors: list[str],
        risk_factors: list[str],
    ) -> float:
        scores = {
            "LOW": 15.0,
            "MODERATE": 11.0,
            "HIGH": 5.0,
            "INSUFFICIENT_DATA": 0.0,
        }

        score = scores.get(
            analysis.volatility_status,
            0.0,
        )

        if analysis.volatility_status == "LOW":
            positive_factors.append(
                "ATR indicates relatively low volatility."
            )
        elif analysis.volatility_status == "MODERATE":
            positive_factors.append(
                "ATR indicates manageable volatility."
            )
        elif analysis.volatility_status == "HIGH":
            risk_factors.append(
                "ATR indicates high price volatility."
            )

        return score

    @staticmethod
    def _score_price_position(
        analysis: TechnicalAnalysisResult,
        positive_factors: list[str],
        risk_factors: list[str],
    ) -> float:
        scores = {
            "BELOW_LOWER_BAND": 15.0,
            "LOWER_HALF": 12.0,
            "UPPER_HALF": 8.0,
            "ABOVE_UPPER_BAND": 2.0,
            "INSUFFICIENT_DATA": 0.0,
        }

        score = scores.get(
            analysis.bollinger_position,
            0.0,
        )

        if analysis.bollinger_position == "BELOW_LOWER_BAND":
            positive_factors.append(
                "Price is below the lower Bollinger Band."
            )
            risk_factors.append(
                "A lower-band break may also reflect strong weakness."
            )
        elif analysis.bollinger_position == "LOWER_HALF":
            positive_factors.append(
                "Price is in the lower half of its Bollinger range."
            )
        elif analysis.bollinger_position == "ABOVE_UPPER_BAND":
            risk_factors.append(
                "Price is above the upper Bollinger Band."
            )

        return score

    @staticmethod
    def _classify_score(score: float) -> str:
        """
        Classify the score without producing a trading instruction.
        """
        if score >= 75.0:
            return "STRONG"

        if score >= 60.0:
            return "POSITIVE"

        if score >= 40.0:
            return "NEUTRAL"

        if score >= 25.0:
            return "WEAK"

        return "VERY_WEAK"