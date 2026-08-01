"""
Decision classifications and descriptive labels.
"""

from investment_terminal.decision_engine.decision_model import (
    DecisionQualitySummary,
)
from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreResult,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisResult,
)
from investment_terminal.services.technical_score_service import (
    TechnicalScoreResult,
)


class DecisionClassifiers:
    """Convert scores and metrics into descriptive classifications."""

    @staticmethod
    def classify_overall(score: float) -> str:
        if score >= 80.0:
            return "EXCELLENT"
        if score >= 65.0:
            return "STRONG"
        if score >= 50.0:
            return "BALANCED"
        if score >= 35.0:
            return "WEAK"
        return "VERY WEAK"

    @classmethod
    def build_quality_summary(
        cls,
        technical_analysis: TechnicalAnalysisResult,
        technical_score: TechnicalScoreResult,
        fundamental_snapshot: FundamentalSnapshot,
        fundamental_score: FundamentalScoreResult,
    ) -> DecisionQualitySummary:
        return DecisionQualitySummary(
            business_quality=cls._classify_business_quality(
                fundamental_score
            ),
            financial_health=cls._classify_financial_health(
                fundamental_score
            ),
            growth=cls._classify_growth(
                fundamental_snapshot
            ),
            valuation=cls._classify_valuation(
                fundamental_score
            ),
            technical_condition=cls._classify_technical_condition(
                technical_analysis,
                technical_score,
            ),
            risk_level=cls._classify_risk(
                technical_analysis,
                fundamental_score,
            ),
        )

    @staticmethod
    def _component_percentage(
        value: float,
        maximum: float,
    ) -> float | None:
        if maximum <= 0:
            return None
        return value / maximum * 100.0

    @classmethod
    def _classify_business_quality(
        cls,
        score: FundamentalScoreResult,
    ) -> str:
        percentages = tuple(
            value
            for value in (
                cls._component_percentage(
                    score.breakdown.profitability,
                    score.breakdown.profitability_max,
                ),
                cls._component_percentage(
                    score.breakdown.cash_flow,
                    score.breakdown.cash_flow_max,
                ),
            )
            if value is not None
        )

        if not percentages:
            return "UNKNOWN"

        average = sum(percentages) / len(percentages)

        if average >= 85.0:
            return "EXCELLENT"
        if average >= 70.0:
            return "STRONG"
        if average >= 50.0:
            return "FAIR"
        return "WEAK"

    @classmethod
    def _classify_financial_health(
        cls,
        score: FundamentalScoreResult,
    ) -> str:
        percentage = cls._component_percentage(
            score.breakdown.balance_sheet,
            score.breakdown.balance_sheet_max,
        )

        if percentage is None:
            return "UNKNOWN"
        if percentage >= 80.0:
            return "STRONG"
        if percentage >= 50.0:
            return "ADEQUATE"
        if percentage > 0.0:
            return "WEAK"

        balance_sheet_risks = {
            "Debt-to-equity is elevated.",
            "Debt-to-equity is high.",
            "Current ratio is below one.",
            "Quick liquidity is weak.",
        }
        if balance_sheet_risks.intersection(
            score.risk_factors
        ):
            return "WEAK"
        return "UNKNOWN"

    @staticmethod
    def _classify_growth(
        snapshot: FundamentalSnapshot,
    ) -> str:
        values = [
            value
            for value in (
                snapshot.revenue_growth,
                snapshot.earnings_growth,
            )
            if value is not None
        ]
        if not values:
            return "UNKNOWN"

        average = sum(values) / len(values)
        if average >= 0.20:
            return "VERY STRONG"
        if average >= 0.10:
            return "STRONG"
        if average >= 0.05:
            return "MODERATE"
        if average >= 0:
            return "LOW"
        return "NEGATIVE"

    @classmethod
    def _classify_valuation(
        cls,
        score: FundamentalScoreResult,
    ) -> str:
        percentage = cls._component_percentage(
            score.breakdown.valuation,
            score.breakdown.valuation_max,
        )
        if percentage is None:
            return "UNKNOWN"
        if percentage >= 80.0:
            return "ATTRACTIVE"
        if percentage >= 60.0:
            return "FAIR"
        if percentage >= 40.0:
            return "ELEVATED"
        return "EXPENSIVE"

    @staticmethod
    def _classify_technical_condition(
        analysis: TechnicalAnalysisResult,
        score: TechnicalScoreResult,
    ) -> str:
        if (
            analysis.bollinger_position == "ABOVE_UPPER_BAND"
            or (
                analysis.rsi14 is not None
                and analysis.rsi14 > 70.0
            )
        ):
            return "POSITIVE BUT EXTENDED"
        return score.classification

    @staticmethod
    def _classify_risk(
        technical_analysis: TechnicalAnalysisResult,
        fundamental_score: FundamentalScoreResult,
    ) -> str:
        risk_points = 0

        if technical_analysis.volatility_status == "HIGH":
            risk_points += 2
        elif technical_analysis.volatility_status == "MODERATE":
            risk_points += 1

        if (
            technical_analysis.rsi14 is not None
            and technical_analysis.rsi14 > 70.0
        ):
            risk_points += 1

        debt_risks = {
            "Debt-to-equity is elevated.",
            "Debt-to-equity is high.",
        }
        if debt_risks.intersection(
            fundamental_score.risk_factors
        ):
            risk_points += 2

        if risk_points >= 4:
            return "HIGH"
        if risk_points >= 2:
            return "MEDIUM"
        return "LOW"