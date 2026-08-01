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

    macd_line: float | None
    macd_signal: float | None
    macd_histogram: float | None

    atr14: float | None
    atr_percent: float | None

    bollinger_upper: float | None
    bollinger_middle: float | None
    bollinger_lower: float | None
    bollinger_bandwidth: float | None

    price_above_sma20: bool | None
    price_above_sma50: bool | None
    price_above_sma200: bool | None
    sma50_above_sma200: bool | None

    trend: str
    bollinger_position: str
    volatility_status: str

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
        latest_price = float(latest_candle.close_price)

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

        macd = TechnicalIndicators.macd(candles)

        macd_line = TechnicalIndicators.latest(
            macd.macd_line
        )
        macd_signal = TechnicalIndicators.latest(
            macd.signal_line
        )
        macd_histogram = TechnicalIndicators.latest(
            macd.histogram
        )

        atr14 = TechnicalIndicators.latest(
            TechnicalIndicators.atr(
                candles,
                period=14,
            )
        )

        atr_percent = (
            atr14 / latest_price * 100.0
            if atr14 is not None
            else None
        )

        bollinger = TechnicalIndicators.bollinger_bands(
            candles,
            period=20,
            standard_deviations=2.0,
        )

        bollinger_upper = TechnicalIndicators.latest(
            bollinger.upper
        )
        bollinger_middle = TechnicalIndicators.latest(
            bollinger.middle
        )
        bollinger_lower = TechnicalIndicators.latest(
            bollinger.lower
        )
        bollinger_bandwidth = TechnicalIndicators.latest(
            bollinger.bandwidth_percent
        )

        indicator_values = {
            "sma20": sma20,
            "sma50": sma50,
            "sma200": sma200,
            "ema20": ema20,
            "rsi14": rsi14,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_histogram,
            "atr14": atr14,
            "bollinger_upper": bollinger_upper,
            "bollinger_middle": bollinger_middle,
            "bollinger_lower": bollinger_lower,
            "bollinger_bandwidth": bollinger_bandwidth,
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
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            atr14=atr14,
            atr_percent=atr_percent,
            bollinger_upper=bollinger_upper,
            bollinger_middle=bollinger_middle,
            bollinger_lower=bollinger_lower,
            bollinger_bandwidth=bollinger_bandwidth,
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
            bollinger_position=self._classify_bollinger_position(
                latest_price=latest_price,
                upper=bollinger_upper,
                middle=bollinger_middle,
                lower=bollinger_lower,
            ),
            volatility_status=self._classify_volatility(
                atr_percent
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
    def _classify_bollinger_position(
        latest_price: float,
        upper: float | None,
        middle: float | None,
        lower: float | None,
    ) -> str:
        """
        Classify price position relative to Bollinger Bands.
        """
        if (
            upper is None
            or middle is None
            or lower is None
        ):
            return "INSUFFICIENT_DATA"

        if latest_price > upper:
            return "ABOVE_UPPER_BAND"

        if latest_price < lower:
            return "BELOW_LOWER_BAND"

        if latest_price >= middle:
            return "UPPER_HALF"

        return "LOWER_HALF"

    @staticmethod
    def _classify_volatility(
        atr_percent: float | None,
    ) -> str:
        """
        Classify ATR as a percentage of the latest price.

        Thresholds provide descriptive context and are not trading rules.
        """
        if atr_percent is None:
            return "INSUFFICIENT_DATA"

        if atr_percent < 2.0:
            return "LOW"

        if atr_percent < 4.0:
            return "MODERATE"

        return "HIGH"

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