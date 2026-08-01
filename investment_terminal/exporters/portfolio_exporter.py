"""
Compact portfolio ranking, recommendation, and thesis JSON exporter.
"""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from investment_terminal.portfolio.ranking_models import (
    RankingResult,
)
from investment_terminal.portfolio.recommendation_models import (
    PortfolioRecommendationResult,
)
from investment_terminal.portfolio.thesis_models import (
    PortfolioThesisResult,
)


@dataclass(frozen=True, slots=True)
class PortfolioExportPackage:
    """
    Complete compact export package for one analyzed universe.

    Each analytical object is exported only once:

    - ranking contains decisions and analytical scores;
    - recommendations contain recommendation-specific information;
    - theses contain human-readable thesis information.

    Sections are connected through symbol and rank.
    """

    schema_version: str
    generated_at: datetime
    universe_name: str
    ranking: RankingResult
    recommendations: PortfolioRecommendationResult
    theses: PortfolioThesisResult

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, str)
            or not self.schema_version.strip()
        ):
            raise ValueError(
                "schema_version must be a non-empty string"
            )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        if (
            not isinstance(self.universe_name, str)
            or not self.universe_name.strip()
        ):
            raise ValueError(
                "universe_name must be a non-empty string"
            )

        if not isinstance(
            self.ranking,
            RankingResult,
        ):
            raise TypeError(
                "ranking must be a RankingResult"
            )

        if not isinstance(
            self.recommendations,
            PortfolioRecommendationResult,
        ):
            raise TypeError(
                "recommendations must be a "
                "PortfolioRecommendationResult"
            )

        if not isinstance(
            self.theses,
            PortfolioThesisResult,
        ):
            raise TypeError(
                "theses must be a PortfolioThesisResult"
            )

        object.__setattr__(
            self,
            "schema_version",
            self.schema_version.strip(),
        )
        object.__setattr__(
            self,
            "universe_name",
            self.universe_name.strip(),
        )

    @property
    def universe_size(self) -> int:
        return self.ranking.universe_size

    @property
    def top_symbol(self) -> str:
        return self.ranking.top_candidate.symbol

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the package to a compact JSON-ready dictionary.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "universe": {
                "name": self.universe_name,
                "size": self.universe_size,
                "symbols": [
                    candidate.symbol
                    for candidate
                    in self.ranking.candidates
                ],
            },
            "summary": self._build_summary(),
            "ranking": self._build_ranking_section(),
            "recommendations": (
                self._build_recommendation_section()
            ),
            "theses": self._build_thesis_section(),
        }

    def _build_summary(self) -> dict[str, Any]:
        """
        Build compact top-candidate summary information.
        """
        top_candidate = (
            self.ranking.top_candidate
        )
        top_recommendation = (
            self.recommendations.top_recommendation
        )
        top_thesis = self.theses.top_thesis

        return {
            "top_symbol": top_candidate.symbol,
            "top_rank": top_candidate.rank,
            "top_overall_score": (
                top_candidate.overall_score
            ),
            "top_recommendation": (
                top_recommendation.recommendation
            ),
            "top_risk_level": (
                top_candidate.risk_level
            ),
            "top_headline": top_thesis.headline,
            "top_action": top_thesis.action,
        }

    def _build_ranking_section(
        self,
    ) -> dict[str, Any]:
        """
        Export analytical decisions exactly once.
        """
        return {
            "schema_version": (
                self.ranking.schema_version
            ),
            "generated_at": (
                self.ranking.generated_at.isoformat()
            ),
            "universe_size": (
                self.ranking.universe_size
            ),
            "top_symbol": (
                self.ranking.top_candidate.symbol
            ),
            "candidates": [
                self._candidate_to_dict(candidate)
                for candidate
                in self.ranking.candidates
            ],
        }

    def _build_recommendation_section(
        self,
    ) -> dict[str, Any]:
        """
        Export only recommendation-specific information.
        """
        return {
            "schema_version": (
                self.recommendations.schema_version
            ),
            "generated_at": (
                self.recommendations
                .generated_at
                .isoformat()
            ),
            "universe_size": (
                self.recommendations.universe_size
            ),
            "top_symbol": (
                self.recommendations
                .top_recommendation
                .symbol
            ),
            "top_recommendation": (
                self.recommendations
                .top_recommendation
                .recommendation
            ),
            "items": [
                {
                    "rank": recommendation.rank,
                    "symbol": recommendation.symbol,
                    "recommendation": (
                        recommendation.recommendation
                    ),
                    "rationale": list(
                        recommendation.rationale
                    ),
                    "cautions": list(
                        recommendation.cautions
                    ),
                }
                for recommendation
                in self.recommendations.recommendations
            ],
        }

    def _build_thesis_section(
        self,
    ) -> dict[str, Any]:
        """
        Export only thesis-specific information.
        """
        return {
            "schema_version": (
                self.theses.schema_version
            ),
            "generated_at": (
                self.theses.generated_at.isoformat()
            ),
            "universe_size": (
                self.theses.universe_size
            ),
            "top_symbol": (
                self.theses.top_thesis.symbol
            ),
            "top_recommendation": (
                self.theses
                .top_thesis
                .recommendation_label
            ),
            "items": [
                {
                    "rank": thesis.rank,
                    "symbol": thesis.symbol,
                    "recommendation": (
                        thesis.recommendation_label
                    ),
                    "headline": thesis.headline,
                    "thesis": thesis.thesis,
                    "strengths": list(
                        thesis.strengths
                    ),
                    "risks": list(
                        thesis.risks
                    ),
                    "action": thesis.action,
                }
                for thesis in self.theses.theses
            ],
        }

    @staticmethod
    def _candidate_to_dict(
        candidate,
    ) -> dict[str, Any]:
        """
        Convert one ranked candidate without downstream duplication.
        """
        decision = candidate.decision

        return {
            "rank": candidate.rank,
            "symbol": candidate.symbol,
            "currency": candidate.currency,
            "scores": {
                "overall": (
                    candidate.overall_score
                ),
                "technical": (
                    candidate.technical_score
                ),
                "fundamental": (
                    candidate.fundamental_score
                ),
                "confidence": (
                    candidate.confidence_score
                ),
                "technical_weight": (
                    decision.scores.technical_weight
                ),
                "fundamental_weight": (
                    decision.scores.fundamental_weight
                ),
            },
            "classification": (
                candidate.classification
            ),
            "quality": {
                "business_quality": (
                    decision
                    .quality
                    .business_quality
                ),
                "financial_health": (
                    decision
                    .quality
                    .financial_health
                ),
                "growth": (
                    decision.quality.growth
                ),
                "valuation": (
                    decision.quality.valuation
                ),
                "technical_condition": (
                    decision
                    .quality
                    .technical_condition
                ),
                "risk_level": (
                    decision.quality.risk_level
                ),
            },
            "confidence": {
                "score": (
                    decision.confidence.score
                ),
                "classification": (
                    decision
                    .confidence
                    .classification
                ),
                "technical_data_quality": (
                    decision
                    .confidence
                    .technical_data_quality
                ),
                "fundamental_data_quality": (
                    decision
                    .confidence
                    .fundamental_data_quality
                ),
                "missing_data_penalty": (
                    decision
                    .confidence
                    .missing_data_penalty
                ),
            },
            "positive_factors": list(
                decision.positive_factors
            ),
            "risk_factors": list(
                decision.risk_factors
            ),
            "missing_data": list(
                decision.missing_data
            ),
            "summary": decision.summary,
        }


class PortfolioExporter:
    """
    Validate, combine, and save compact portfolio results.
    """

    SCHEMA_VERSION = "1.1"

    def build_package(
        self,
        *,
        universe_name: str,
        ranking: RankingResult,
        recommendations: PortfolioRecommendationResult,
        theses: PortfolioThesisResult,
        generated_at: datetime,
    ) -> PortfolioExportPackage:
        """
        Validate and combine portfolio analysis components.
        """
        self._validate_components(
            universe_name=universe_name,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=generated_at,
        )

        return PortfolioExportPackage(
            schema_version=self.SCHEMA_VERSION,
            generated_at=generated_at,
            universe_name=universe_name,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
        )

    def save_json(
        self,
        package: PortfolioExportPackage,
        output_path: str | Path,
    ) -> Path:
        """
        Save a compact portfolio package as formatted JSON.
        """
        if not isinstance(
            package,
            PortfolioExportPackage,
        ):
            raise TypeError(
                "package must be a PortfolioExportPackage"
            )

        path = Path(output_path)

        if path.suffix.lower() != ".json":
            raise ValueError(
                "output_path must use the .json extension"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                package.to_dict(),
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

        return path

    @staticmethod
    def _validate_components(
        *,
        universe_name: str,
        ranking: RankingResult,
        recommendations: PortfolioRecommendationResult,
        theses: PortfolioThesisResult,
        generated_at: datetime,
    ) -> None:
        """
        Ensure all components describe the same universe and run.
        """
        if (
            not isinstance(universe_name, str)
            or not universe_name.strip()
        ):
            raise ValueError(
                "universe_name must be a non-empty string"
            )

        if not isinstance(
            ranking,
            RankingResult,
        ):
            raise TypeError(
                "ranking must be a RankingResult"
            )

        if not isinstance(
            recommendations,
            PortfolioRecommendationResult,
        ):
            raise TypeError(
                "recommendations must be a "
                "PortfolioRecommendationResult"
            )

        if not isinstance(
            theses,
            PortfolioThesisResult,
        ):
            raise TypeError(
                "theses must be a PortfolioThesisResult"
            )

        if not isinstance(
            generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        ranking_symbols = tuple(
            candidate.symbol
            for candidate in ranking.candidates
        )
        recommendation_symbols = tuple(
            recommendation.symbol
            for recommendation
            in recommendations.recommendations
        )
        thesis_symbols = tuple(
            thesis.symbol
            for thesis in theses.theses
        )

        if (
            ranking_symbols
            != recommendation_symbols
            or ranking_symbols
            != thesis_symbols
        ):
            raise ValueError(
                "Portfolio components must contain "
                "the same symbols in the same order"
            )

        if (
            ranking.universe_size
            != recommendations.universe_size
            or ranking.universe_size
            != theses.universe_size
        ):
            raise ValueError(
                "Portfolio components must use "
                "the same universe size"
            )

        ranking_ranks = tuple(
            candidate.rank
            for candidate in ranking.candidates
        )
        recommendation_ranks = tuple(
            recommendation.rank
            for recommendation
            in recommendations.recommendations
        )
        thesis_ranks = tuple(
            thesis.rank
            for thesis in theses.theses
        )

        if (
            ranking_ranks
            != recommendation_ranks
            or ranking_ranks
            != thesis_ranks
        ):
            raise ValueError(
                "Portfolio components must use "
                "the same candidate ranks"
            )

        for recommendation, thesis in zip(
            recommendations.recommendations,
            theses.theses,
            strict=True,
        ):
            if (
                recommendation.recommendation
                != thesis.recommendation_label
            ):
                raise ValueError(
                    "Thesis recommendation labels must "
                    "match recommendation results"
                )

        timestamps = {
            ranking.generated_at,
            recommendations.generated_at,
            theses.generated_at,
            generated_at,
        }

        if len(timestamps) != 1:
            raise ValueError(
                "Portfolio components must use "
                "the same generated_at timestamp"
            )