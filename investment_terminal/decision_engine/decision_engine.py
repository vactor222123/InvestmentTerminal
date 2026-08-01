"""
Modular investment decision engine.
"""

from datetime import datetime, timezone

from investment_terminal.decision_engine.aggregators import (
    DecisionFactorAggregator,
)
from investment_terminal.decision_engine.classifiers import (
    DecisionClassifiers,
)
from investment_terminal.decision_engine.confidence import (
    ConfidenceEngine,
)
from investment_terminal.decision_engine.decision_model import (
    DecisionResult,
    DecisionScoreSummary,
)
from investment_terminal.decision_engine.weighting import (
    DecisionWeighting,
    DecisionWeights,
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


class DecisionEngine:
    """
    Combine technical and fundamental analysis.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        weights: DecisionWeights | None = None,
    ) -> None:
        self.weights = (
            weights
            if weights is not None
            else DecisionWeights()
        )

    def evaluate(
        self,
        technical_analysis: TechnicalAnalysisResult,
        technical_score: TechnicalScoreResult,
        fundamental_snapshot: FundamentalSnapshot,
        fundamental_score: FundamentalScoreResult,
        generated_at: datetime | None = None,
    ) -> DecisionResult:
        """
        Produce one structured investment decision.
        """
        self._validate_components(
            technical_analysis=technical_analysis,
            technical_score=technical_score,
            fundamental_snapshot=fundamental_snapshot,
            fundamental_score=fundamental_score,
        )

        overall_score = (
            DecisionWeighting.calculate_overall(
                technical_score=(
                    technical_score.final_score
                ),
                fundamental_score=(
                    fundamental_score.final_score
                ),
                weights=self.weights,
            )
        )

        technical_quality = (
            technical_analysis
            .data_quality
            .completeness_percent
        )

        fundamental_quality = (
            fundamental_snapshot
            .data_quality
            .completeness_percent
            if fundamental_snapshot.data_quality
            is not None
            else 0.0
        )

        technical_missing = (
            technical_analysis
            .data_quality
            .missing_indicators
        )

        fundamental_missing = (
            fundamental_score.missing_fields
        )

        confidence = ConfidenceEngine.calculate(
            technical_quality=technical_quality,
            fundamental_quality=fundamental_quality,
            technical_missing_count=len(
                technical_missing
            ),
            fundamental_missing_count=len(
                fundamental_missing
            ),
        )

        quality = (
            DecisionClassifiers.build_quality_summary(
                technical_analysis=technical_analysis,
                technical_score=technical_score,
                fundamental_snapshot=(
                    fundamental_snapshot
                ),
                fundamental_score=fundamental_score,
            )
        )

        positive_factors = (
            DecisionFactorAggregator.merge(
                technical_score.positive_factors,
                fundamental_score.positive_factors,
            )
        )

        risk_factors = (
            DecisionFactorAggregator.merge(
                technical_score.risk_factors,
                fundamental_score.risk_factors,
            )
        )

        missing_data = (
            DecisionFactorAggregator.build_missing_data(
                technical_missing=technical_missing,
                fundamental_missing=(
                    fundamental_missing
                ),
            )
        )

        classification = (
            DecisionClassifiers.classify_overall(
                overall_score
            )
        )

        return DecisionResult(
            schema_version=self.SCHEMA_VERSION,
            generated_at=(
                generated_at
                if generated_at is not None
                else datetime.now(timezone.utc)
            ),
            symbol=technical_analysis.symbol,
            currency=technical_analysis.currency,
            scores=DecisionScoreSummary(
                technical=(
                    technical_score.final_score
                ),
                fundamental=(
                    fundamental_score.final_score
                ),
                overall=overall_score,
                technical_weight=(
                    self.weights.technical
                ),
                fundamental_weight=(
                    self.weights.fundamental
                ),
            ),
            quality=quality,
            confidence=confidence,
            classification=classification,
            positive_factors=positive_factors,
            risk_factors=risk_factors,
            missing_data=missing_data,
            summary=self._build_summary(
                quality=quality,
                classification=classification,
            ),
        )

    @staticmethod
    def _build_summary(
        quality,
        classification: str,
    ) -> str:
        """
        Create a deterministic summary without generative AI.
        """
        return (
            f"Overall condition is {classification}. "
            f"Business quality is "
            f"{quality.business_quality}, "
            f"financial health is "
            f"{quality.financial_health}, "
            f"growth is {quality.growth}, "
            f"valuation is {quality.valuation}, "
            f"and technical condition is "
            f"{quality.technical_condition}. "
            f"Current risk level is "
            f"{quality.risk_level}."
        )

    @staticmethod
    def _validate_components(
        technical_analysis: TechnicalAnalysisResult,
        technical_score: TechnicalScoreResult,
        fundamental_snapshot: FundamentalSnapshot,
        fundamental_score: FundamentalScoreResult,
    ) -> None:
        if not isinstance(
            technical_analysis,
            TechnicalAnalysisResult,
        ):
            raise TypeError(
                "technical_analysis must be "
                "a TechnicalAnalysisResult"
            )

        if not isinstance(
            technical_score,
            TechnicalScoreResult,
        ):
            raise TypeError(
                "technical_score must be "
                "a TechnicalScoreResult"
            )

        if not isinstance(
            fundamental_snapshot,
            FundamentalSnapshot,
        ):
            raise TypeError(
                "fundamental_snapshot must be "
                "a FundamentalSnapshot"
            )

        if not isinstance(
            fundamental_score,
            FundamentalScoreResult,
        ):
            raise TypeError(
                "fundamental_score must be "
                "a FundamentalScoreResult"
            )

        symbols = {
            technical_analysis.symbol,
            technical_score.symbol,
            fundamental_snapshot.symbol,
            fundamental_score.symbol,
        }

        if len(symbols) != 1:
            raise ValueError(
                "Decision components must use "
                "the same symbol"
            )

        currencies = {
            technical_analysis.currency,
            fundamental_snapshot.currency,
            fundamental_score.currency,
        }

        if len(currencies) != 1:
            raise ValueError(
                "Decision components must use "
                "the same currency"
            )