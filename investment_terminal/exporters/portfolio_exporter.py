"""
Portfolio ranking, recommendation, and thesis JSON exporter.
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
    Complete export package for one analyzed asset universe.
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
        Convert the complete package to JSON-ready data.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "universe": {
                "name": self.universe_name,
                "size": self.universe_size,
            },
            "summary": {
                "top_symbol": self.top_symbol,
                "top_recommendation": (
                    self.recommendations
                    .top_recommendation
                    .recommendation
                ),
                "top_headline": (
                    self.theses
                    .top_thesis
                    .headline
                ),
            },
            "ranking": self.ranking.to_dict(),
            "recommendations": (
                self.recommendations.to_dict()
            ),
            "theses": self.theses.to_dict(),
        }


class PortfolioExporter:
    """
    Validate, combine, and save portfolio analysis results.
    """

    SCHEMA_VERSION = "1.0"

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
        Save a portfolio export package as formatted JSON.
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
        Ensure all portfolio components describe the same universe.
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