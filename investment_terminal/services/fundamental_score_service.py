"""
Transparent fundamental scoring service.
"""

from dataclasses import asdict, dataclass
from typing import Any

from investment_terminal.clients.fundamental_data_client import (
    FundamentalDataClient,
)
from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)


@dataclass(frozen=True, slots=True)
class FundamentalScoreBreakdown:
    """
    Fundamental-score components.
    """

    growth: float
    profitability: float
    balance_sheet: float
    cash_flow: float
    valuation: float
    shareholder_returns: float

    growth_max: float = 20.0
    profitability_max: float = 25.0
    balance_sheet_max: float = 15.0
    cash_flow_max: float = 15.0
    valuation_max: float = 20.0
    shareholder_returns_max: float = 5.0

    def to_dict(self) -> dict[str, float]:
        """
        Convert the breakdown into a JSON-ready dictionary.
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FundamentalScoreResult:
    """
    Auditable fundamental score for one asset.
    """

    symbol: str
    currency: str

    raw_score: float
    data_quality_factor: float
    final_score: float
    classification: str

    breakdown: FundamentalScoreBreakdown
    positive_factors: tuple[str, ...]
    risk_factors: tuple[str, ...]
    missing_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the score into a JSON-ready dictionary.
        """
        return {
            "symbol": self.symbol,
            "currency": self.currency,
            "raw_score": self.raw_score,
            "data_quality_factor": self.data_quality_factor,
            "final_score": self.final_score,
            "classification": self.classification,
            "breakdown": self.breakdown.to_dict(),
            "positive_factors": list(
                self.positive_factors
            ),
            "risk_factors": list(
                self.risk_factors
            ),
            "missing_fields": list(
                self.missing_fields
            ),
        }


class FundamentalScoreService:
    """
    Convert normalized fundamentals into a transparent score.

    The score is a screening tool, not an investment recommendation.
    Valuation thresholds are generic and will later become
    sector-aware.
    """

    def __init__(
        self,
        client: FundamentalDataClient,
    ) -> None:
        self.client = client

    def score(
        self,
        symbol: str,
        currency: str = "USD",
    ) -> FundamentalScoreResult:
        """
        Download and score one fundamental snapshot.
        """
        snapshot = self.client.get_fundamentals(
            symbol=symbol,
            currency=currency,
        )

        return self.score_snapshot(snapshot)

    def score_snapshot(
        self,
        snapshot: FundamentalSnapshot,
    ) -> FundamentalScoreResult:
        """
        Score an already normalized snapshot.
        """
        if not isinstance(
            snapshot,
            FundamentalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a FundamentalSnapshot"
            )

        positive_factors: list[str] = []
        risk_factors: list[str] = []

        growth = self._score_growth(
            snapshot,
            positive_factors,
            risk_factors,
        )
        profitability = self._score_profitability(
            snapshot,
            positive_factors,
            risk_factors,
        )
        balance_sheet = self._score_balance_sheet(
            snapshot,
            positive_factors,
            risk_factors,
        )
        cash_flow = self._score_cash_flow(
            snapshot,
            positive_factors,
            risk_factors,
        )
        valuation = self._score_valuation(
            snapshot,
            positive_factors,
            risk_factors,
        )
        shareholder_returns = (
            self._score_shareholder_returns(
                snapshot,
                positive_factors,
                risk_factors,
            )
        )

        breakdown = FundamentalScoreBreakdown(
            growth=growth,
            profitability=profitability,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            valuation=valuation,
            shareholder_returns=shareholder_returns,
        )

        raw_score = (
            growth
            + profitability
            + balance_sheet
            + cash_flow
            + valuation
            + shareholder_returns
        )

        quality = snapshot.data_quality

        if quality is None:
            data_quality_factor = 0.0
            missing_fields = (
                snapshot.metric_field_names()
            )
            risk_factors.append(
                "Fundamental data quality is unavailable."
            )
        else:
            data_quality_factor = min(
                max(
                    quality.completeness_percent
                    / 100.0,
                    0.0,
                ),
                1.0,
            )
            missing_fields = quality.missing_fields

            if missing_fields:
                risk_factors.append(
                    "Some fundamental metrics are unavailable."
                )

        final_score = (
            raw_score * data_quality_factor
        )

        return FundamentalScoreResult(
            symbol=snapshot.symbol,
            currency=snapshot.currency,
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
            positive_factors=tuple(
                positive_factors
            ),
            risk_factors=tuple(
                risk_factors
            ),
            missing_fields=tuple(
                missing_fields
            ),
        )

    @classmethod
    def _score_growth(
        cls,
        snapshot: FundamentalSnapshot,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        if snapshot.revenue_growth is not None:
            points = cls._growth_points(
                snapshot.revenue_growth
            )
            metrics.append((points, 10.0))

            if snapshot.revenue_growth >= 0.10:
                positive.append(
                    "Revenue growth is strong."
                )
            elif snapshot.revenue_growth < 0:
                risks.append(
                    "Revenue is declining."
                )

        if snapshot.earnings_growth is not None:
            points = cls._growth_points(
                snapshot.earnings_growth
            )
            metrics.append((points, 10.0))

            if snapshot.earnings_growth >= 0.10:
                positive.append(
                    "Earnings growth is strong."
                )
            elif snapshot.earnings_growth < 0:
                risks.append(
                    "Earnings are declining."
                )

        return cls._normalize_component(
            metrics,
            component_max=20.0,
        )

    @classmethod
    def _score_profitability(
        cls,
        snapshot: FundamentalSnapshot,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        definitions = (
            (
                snapshot.gross_margin,
                5.0,
                (0.60, 0.40, 0.20),
                "Gross margin is strong.",
            ),
            (
                snapshot.operating_margin,
                5.0,
                (0.30, 0.15, 0.05),
                "Operating margin is strong.",
            ),
            (
                snapshot.net_margin,
                5.0,
                (0.25, 0.12, 0.03),
                "Net margin is strong.",
            ),
            (
                snapshot.return_on_equity,
                5.0,
                (0.25, 0.15, 0.05),
                "Return on equity is strong.",
            ),
            (
                snapshot.return_on_invested_capital,
                5.0,
                (0.20, 0.10, 0.04),
                "Return on invested capital is strong.",
            ),
        )

        for value, maximum, thresholds, message in definitions:
            if value is None:
                continue

            points = cls._threshold_points(
                value=value,
                maximum=maximum,
                strong=thresholds[0],
                acceptable=thresholds[1],
                weak=thresholds[2],
            )
            metrics.append((points, maximum))

            if value >= thresholds[0]:
                positive.append(message)
            elif value < thresholds[2]:
                risks.append(
                    "One profitability metric is weak."
                )

        return cls._normalize_component(
            metrics,
            component_max=25.0,
        )

    @classmethod
    def _score_balance_sheet(
        cls,
        snapshot: FundamentalSnapshot,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        if snapshot.debt_to_equity is not None:
            value = snapshot.debt_to_equity

            if value <= 0.5:
                points = 7.0
                positive.append(
                    "Debt-to-equity is conservative."
                )
            elif value <= 1.0:
                points = 5.0
            elif value <= 2.0:
                points = 2.5
                risks.append(
                    "Debt-to-equity is elevated."
                )
            else:
                points = 0.0
                risks.append(
                    "Debt-to-equity is high."
                )

            metrics.append((points, 7.0))

        if snapshot.current_ratio is not None:
            value = snapshot.current_ratio

            if 1.2 <= value <= 3.0:
                points = 4.0
                positive.append(
                    "Current liquidity is healthy."
                )
            elif value >= 1.0:
                points = 2.5
            else:
                points = 0.0
                risks.append(
                    "Current ratio is below one."
                )

            metrics.append((points, 4.0))

        if snapshot.quick_ratio is not None:
            value = snapshot.quick_ratio

            if value >= 1.0:
                points = 4.0
            elif value >= 0.7:
                points = 2.0
            else:
                points = 0.0
                risks.append(
                    "Quick liquidity is weak."
                )

            metrics.append((points, 4.0))

        return cls._normalize_component(
            metrics,
            component_max=15.0,
        )

    @classmethod
    def _score_cash_flow(
        cls,
        snapshot: FundamentalSnapshot,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        if snapshot.operating_cash_flow is not None:
            value = snapshot.operating_cash_flow
            points = 7.0 if value > 0 else 0.0
            metrics.append((points, 7.0))

            if value > 0:
                positive.append(
                    "Operating cash flow is positive."
                )
            else:
                risks.append(
                    "Operating cash flow is negative."
                )

        if snapshot.free_cash_flow is not None:
            value = snapshot.free_cash_flow
            points = 8.0 if value > 0 else 0.0
            metrics.append((points, 8.0))

            if value > 0:
                positive.append(
                    "Free cash flow is positive."
                )
            else:
                risks.append(
                    "Free cash flow is negative."
                )

        return cls._normalize_component(
            metrics,
            component_max=15.0,
        )

    @classmethod
    def _score_valuation(
        cls,
        snapshot: FundamentalSnapshot,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        valuation_metrics = (
            (
                snapshot.forward_pe,
                6.0,
                (15.0, 25.0, 40.0),
                "Forward P/E is attractive.",
                "Forward P/E is elevated.",
            ),
            (
                snapshot.peg_ratio,
                5.0,
                (1.0, 2.0, 3.0),
                "PEG ratio is attractive.",
                "PEG ratio is elevated.",
            ),
            (
                snapshot.enterprise_to_ebitda,
                5.0,
                (10.0, 18.0, 30.0),
                "EV/EBITDA is attractive.",
                "EV/EBITDA is elevated.",
            ),
            (
                snapshot.price_to_sales,
                4.0,
                (3.0, 8.0, 15.0),
                "Price-to-sales is moderate.",
                "Price-to-sales is elevated.",
            ),
        )

        for (
            value,
            maximum,
            thresholds,
            positive_message,
            risk_message,
        ) in valuation_metrics:
            if value is None:
                continue

            points = cls._inverse_threshold_points(
                value=value,
                maximum=maximum,
                attractive=thresholds[0],
                acceptable=thresholds[1],
                expensive=thresholds[2],
            )
            metrics.append((points, maximum))

            if value <= thresholds[0]:
                positive.append(
                    positive_message
                )
            elif value > thresholds[2]:
                risks.append(
                    risk_message
                )

        return cls._normalize_component(
            metrics,
            component_max=20.0,
        )

    @classmethod
    def _score_shareholder_returns(
        cls,
        snapshot: FundamentalSnapshot,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        if snapshot.dividend_yield is not None:
            value = snapshot.dividend_yield

            if value >= 0.03:
                points = 2.5
            elif value > 0:
                points = 1.5
            else:
                points = 0.0

            metrics.append((points, 2.5))

            if value > 0:
                positive.append(
                    "The company pays a dividend."
                )

        if snapshot.payout_ratio is not None:
            value = snapshot.payout_ratio

            if 0 <= value <= 0.60:
                points = 2.5
                positive.append(
                    "The dividend payout ratio is sustainable."
                )
            elif value <= 0.85:
                points = 1.0
            else:
                points = 0.0
                risks.append(
                    "The dividend payout ratio is high."
                )

            metrics.append((points, 2.5))

        return cls._normalize_component(
            metrics,
            component_max=5.0,
        )

    @staticmethod
    def _growth_points(value: float) -> float:
        if value >= 0.20:
            return 10.0

        if value >= 0.10:
            return 8.0

        if value >= 0.05:
            return 6.0

        if value >= 0:
            return 3.0

        return 0.0

    @staticmethod
    def _threshold_points(
        value: float,
        maximum: float,
        strong: float,
        acceptable: float,
        weak: float,
    ) -> float:
        if value >= strong:
            return maximum

        if value >= acceptable:
            return maximum * 0.75

        if value >= weak:
            return maximum * 0.4

        return 0.0

    @staticmethod
    def _inverse_threshold_points(
        value: float,
        maximum: float,
        attractive: float,
        acceptable: float,
        expensive: float,
    ) -> float:
        if value <= 0:
            return 0.0

        if value <= attractive:
            return maximum

        if value <= acceptable:
            return maximum * 0.75

        if value <= expensive:
            return maximum * 0.4

        return 0.0

    @staticmethod
    def _normalize_component(
        metrics: list[tuple[float, float]],
        component_max: float,
    ) -> float:
        """
        Normalize available metrics to the component maximum.

        Missing metrics are handled by the global data-quality factor.
        """
        if not metrics:
            return 0.0

        earned = sum(
            points for points, _ in metrics
        )
        available_maximum = sum(
            maximum for _, maximum in metrics
        )

        return round(
            earned
            / available_maximum
            * component_max,
            2,
        )

    @staticmethod
    def _classify_score(score: float) -> str:
        if score >= 80.0:
            return "EXCELLENT"

        if score >= 65.0:
            return "STRONG"

        if score >= 50.0:
            return "FAIR"

        if score >= 35.0:
            return "WEAK"

        return "VERY_WEAK"