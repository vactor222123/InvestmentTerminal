"""
Technical analysis orchestration service.
"""

from dataclasses import dataclass
from datetime import datetime

from investment_terminal.indicators.technical_indicators import (
    TechnicalIndicators,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


@dataclass(frozen=True, slots=True)
class TechnicalDataQuality:
    """
    Data-quality assessment for technical analysis.
    """

    candle_count: int
    recommended_candle_count: int
    completeness_percent: float
    missing_indicators: tuple[str, ...]
    sufficient_for_long_term: bool


@dataclass(frozen=True, slots=True)
class TechnicalAnalysisResult:
    """
    Latest technical-analysis snapshot for one asset.
    """

    symbol: str
    resolution: str
    timestamp: datetime
    latest_price: float
    currency: str

    sma20: float | None
    sma50: float | None
    sma200: float | None
    ema20: float | None
    rsi14: float | None

    price_above_sma20: bool | None
    price_above_sma50: bool | None
    price_above_sma200: bool | None
    sma50_above_sma200: bool | None

    trend: str
    data_quality: TechnicalDataQuality


class TechnicalAnalysisService:
    """
    Load stored candles and calculate a technical-analysis snapshot.
    """

    RECOMMENDED_CANDLE_COUNT = 200

    def __init__(
        self,
        repository: CandleRepository,
    ) -> None:
        self.repository = repository

    def analyze(
        self,
        symbol: str,
        resolution: str = "D",
    ) -> TechnicalAnalysisResult:
        """
        Analyze all stored candles for a symbol and resolution.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )

        candles = self.repository.get_range(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
        )

        if not candles:
            raise ValueError(
                "No candles are available for "
                f"{normalized_symbol} {normalized_resolution}."
            )

        latest_candle = candles[-1]

        sma20 = TechnicalIndicators.latest(
            TechnicalIndicators.sma(
                candles,
                period=20,
            )
        )
        sma50 = TechnicalIndicators.latest(
            TechnicalIndicators.sma(
                candles,
                period=50,
            )
        )
        sma200 = TechnicalIndicators.latest(
            TechnicalIndicators.sma(
                candles,
                period=200,
            )
        )
        ema20 = TechnicalIndicators.latest(
            TechnicalIndicators.ema(
                candles,
                period=20,
            )
        )
        rsi14 = TechnicalIndicators.latest(
            TechnicalIndicators.rsi(
                candles,
                period=14,
            )
        )

        indicator_values = {
            "sma20": sma20,
            "sma50": sma50,
            "sma200": sma200,
            "ema20": ema20,
            "rsi14": rsi14,
        }

        missing_indicators = tuple(
            name
            for name, value in indicator_values.items()
            if value is None
        )

        candle_count = len(candles)

        completeness_percent = min(
            candle_count
            / self.RECOMMENDED_CANDLE_COUNT
            * 100.0,
            100.0,
        )

        data_quality = TechnicalDataQuality(
            candle_count=candle_count,
            recommended_candle_count=(
                self.RECOMMENDED_CANDLE_COUNT
            ),
            completeness_percent=round(
                completeness_percent,
                2,
            ),
            missing_indicators=missing_indicators,
            sufficient_for_long_term=(
                sma200 is not None
            ),
        )

        latest_price = float(
            latest_candle.close_price
        )

        return TechnicalAnalysisResult(
            symbol=normalized_symbol,
            resolution=normalized_resolution,
            timestamp=latest_candle.timestamp,
            latest_price=latest_price,
            currency=latest_candle.currency,
            sma20=sma20,
            sma50=sma50,
            sma200=sma200,
            ema20=ema20,
            rsi14=rsi14,
            price_above_sma20=self._compare(
                latest_price,
                sma20,
            ),
            price_above_sma50=self._compare(
                latest_price,
                sma50,
            ),
            price_above_sma200=self._compare(
                latest_price,
                sma200,
            ),
            sma50_above_sma200=self._compare(
                sma50,
                sma200,
            ),
            trend=self._classify_trend(
                latest_price=latest_price,
                sma20=sma20,
                sma50=sma50,
                sma200=sma200,
            ),
            data_quality=data_quality,
        )

    @staticmethod
    def _classify_trend(
        latest_price: float,
        sma20: float | None,
        sma50: float | None,
        sma200: float | None,
    ) -> str:
        """
        Classify the current moving-average structure.

        This is descriptive context, not a buy or sell signal.
        """
        if sma200 is None:
            return "INSUFFICIENT_DATA"

        if sma20 is not None and sma50 is not None:
            if (
                latest_price > sma20
                and sma20 > sma50
                and sma50 > sma200
            ):
                return "STRONG_UPTREND"

            if (
                latest_price < sma20
                and sma20 < sma50
                and sma50 < sma200
            ):
                return "STRONG_DOWNTREND"

        if latest_price > sma200:
            return "UPTREND"

        if latest_price < sma200:
            return "DOWNTREND"

        return "NEUTRAL"

    @staticmethod
    def _compare(
        first: float | None,
        second: float | None,
    ) -> bool | None:
        """
        Compare two values when both are available.
        """
        if first is None or second is None:
            return None

        return first > second

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip().upper()