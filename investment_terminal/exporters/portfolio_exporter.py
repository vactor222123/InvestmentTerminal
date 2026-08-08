"""
Compact portfolio ranking, recommendation, thesis, and market-data JSON exporter.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from investment_terminal.portfolio.allocation_models import (
    PortfolioAllocationResult,
)
from investment_terminal.portfolio.ranking_models import RankingResult
from investment_terminal.portfolio.recommendation_models import (
    PortfolioRecommendationResult,
)
from investment_terminal.portfolio.thesis_models import PortfolioThesisResult
from investment_terminal.services.market_data_refresh_service import (
    UniverseMarketDataRefreshResult,
)
from investment_terminal.utils.atomic_write import (
    write_json_atomic,
)


@dataclass(frozen=True, slots=True)
class PortfolioExportPackage:
    """Complete compact export package for one analyzed universe."""

    schema_version: str
    generated_at: datetime
    universe_name: str
    market_data: UniverseMarketDataRefreshResult
    allocation: PortfolioAllocationResult
    ranking: RankingResult
    recommendations: PortfolioRecommendationResult
    theses: PortfolioThesisResult

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("schema_version must be a non-empty string")
        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be a datetime")
        if not isinstance(self.universe_name, str) or not self.universe_name.strip():
            raise ValueError("universe_name must be a non-empty string")
        if not isinstance(self.market_data, UniverseMarketDataRefreshResult):
            raise TypeError(
                "market_data must be a UniverseMarketDataRefreshResult"
            )
        if not isinstance(
            self.allocation,
            PortfolioAllocationResult,
        ):
            raise TypeError(
                "allocation must be a "
                "PortfolioAllocationResult"
            )
        if not isinstance(self.ranking, RankingResult):
            raise TypeError("ranking must be a RankingResult")
        if not isinstance(self.recommendations, PortfolioRecommendationResult):
            raise TypeError(
                "recommendations must be a PortfolioRecommendationResult"
            )
        if not isinstance(self.theses, PortfolioThesisResult):
            raise TypeError("theses must be a PortfolioThesisResult")

        object.__setattr__(self, "schema_version", self.schema_version.strip())
        object.__setattr__(self, "universe_name", self.universe_name.strip())

    @property
    def universe_size(self) -> int:
        return self.ranking.universe_size

    @property
    def top_symbol(self) -> str:
        return self.ranking.top_candidate.symbol

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "universe": {
                "name": self.universe_name,
                "size": self.universe_size,
                "symbols": [candidate.symbol for candidate in self.ranking.candidates],
            },
            "market_data": self._build_market_data_section(),
            "allocation": self._build_allocation_section(),
            "summary": self._build_summary(),
            "ranking": self._build_ranking_section(),
            "recommendations": self._build_recommendation_section(),
            "theses": self._build_thesis_section(),
        }

    def _build_market_data_section(self) -> dict[str, Any]:
        market_data_by_symbol = {
            item.symbol: item
            for item in self.market_data.results
        }

        ordered_items = [
            market_data_by_symbol[candidate.symbol]
            for candidate in self.ranking.candidates
        ]

        return {
            "checked_at": self.market_data.checked_at.isoformat(),
            "universe_size": self.market_data.universe_size,
            "ready_count": self.market_data.ready_count,
            "failed_count": self.market_data.failed_count,
            "refreshed_count": self.market_data.refreshed_count,
            "all_ready": self.market_data.all_ready,
            "failed_symbols": list(self.market_data.failed_symbols),
            "items": [
                self._market_data_item_to_dict(item)
                for item in ordered_items
            ],
        }

    @staticmethod
    def _market_data_item_to_dict(item) -> dict[str, Any]:
        freshness = item.freshness_after
        import_result = item.import_result
        return {
            "symbol": item.symbol,
            "resolution": item.resolution,
            "policy": freshness.policy,
            "status": freshness.status,
            "is_ready": item.is_ready,
            "last_candle_at": (
                freshness.last_candle_at.isoformat()
                if freshness.last_candle_at is not None
                else None
            ),
            "age_hours": freshness.age_hours,
            "maximum_age_hours": freshness.maximum_age_hours,
            "expected_session_date": (
                freshness.expected_session_date.isoformat()
                if freshness.expected_session_date is not None
                else None
            ),
            "last_candle_session_date": (
                freshness.last_candle_session_date.isoformat()
                if freshness.last_candle_session_date is not None
                else None
            ),
            "refresh_attempted": item.refresh_attempted,
            "downloaded": item.downloaded,
            "inserted": item.inserted,
            "duplicates": item.duplicates,
            "stored_total": (
                import_result.stored_total if import_result is not None else None
            ),
        }


    def _build_allocation_section(self) -> dict[str, Any]:
        """
        Export the generated target portfolio allocation.
        """
        return {
            "schema_version": self.allocation.schema_version,
            "generated_at": (
                self.allocation.generated_at.isoformat()
            ),
            "profile": self.allocation.constraints.profile,
            "currency": self.allocation.currency,
            "total_capital": self.allocation.total_capital,
            "invested_amount": self.allocation.invested_amount,
            "cash_amount": self.allocation.cash_amount,
            "invested_weight": self.allocation.invested_weight,
            "cash_weight": self.allocation.cash_weight,
            "top_symbol": self.allocation.top_position.symbol,
            "constraints": (
                self.allocation.constraints.to_dict()
            ),
            "positions": [
                position.to_dict()
                for position in self.allocation.positions
            ],
        }

    def _build_summary(self) -> dict[str, Any]:
        top_candidate = self.ranking.top_candidate
        top_recommendation = self.recommendations.top_recommendation
        top_thesis = self.theses.top_thesis
        return {
            "top_symbol": top_candidate.symbol,
            "top_rank": top_candidate.rank,
            "top_overall_score": top_candidate.overall_score,
            "top_recommendation": top_recommendation.recommendation,
            "top_risk_level": top_candidate.risk_level,
            "top_headline": top_thesis.headline,
            "top_action": top_thesis.action,
            "market_data_ready": self.market_data.all_ready,
            "market_data_checked_at": self.market_data.checked_at.isoformat(),
            "allocation_profile": (
                self.allocation.constraints.profile
            ),
            "allocation_total_capital": (
                self.allocation.total_capital
            ),
            "allocation_cash_weight": (
                self.allocation.cash_weight
            ),
        }

    def _build_ranking_section(self) -> dict[str, Any]:
        return {
            "schema_version": self.ranking.schema_version,
            "generated_at": self.ranking.generated_at.isoformat(),
            "universe_size": self.ranking.universe_size,
            "top_symbol": self.ranking.top_candidate.symbol,
            "candidates": [
                self._candidate_to_dict(candidate)
                for candidate in self.ranking.candidates
            ],
        }

    def _build_recommendation_section(self) -> dict[str, Any]:
        return {
            "schema_version": self.recommendations.schema_version,
            "generated_at": self.recommendations.generated_at.isoformat(),
            "universe_size": self.recommendations.universe_size,
            "top_symbol": self.recommendations.top_recommendation.symbol,
            "top_recommendation": (
                self.recommendations.top_recommendation.recommendation
            ),
            "items": [
                {
                    "rank": recommendation.rank,
                    "symbol": recommendation.symbol,
                    "recommendation": recommendation.recommendation,
                    "rationale": list(recommendation.rationale),
                    "cautions": list(recommendation.cautions),
                }
                for recommendation in self.recommendations.recommendations
            ],
        }

    def _build_thesis_section(self) -> dict[str, Any]:
        return {
            "schema_version": self.theses.schema_version,
            "generated_at": self.theses.generated_at.isoformat(),
            "universe_size": self.theses.universe_size,
            "top_symbol": self.theses.top_thesis.symbol,
            "top_recommendation": self.theses.top_thesis.recommendation_label,
            "items": [
                {
                    "rank": thesis.rank,
                    "symbol": thesis.symbol,
                    "recommendation": thesis.recommendation_label,
                    "headline": thesis.headline,
                    "thesis": thesis.thesis,
                    "strengths": list(thesis.strengths),
                    "risks": list(thesis.risks),
                    "action": thesis.action,
                }
                for thesis in self.theses.theses
            ],
        }

    @staticmethod
    def _candidate_to_dict(candidate) -> dict[str, Any]:
        decision = candidate.decision
        return {
            "rank": candidate.rank,
            "symbol": candidate.symbol,
            "currency": candidate.currency,
            "scores": {
                "overall": candidate.overall_score,
                "technical": candidate.technical_score,
                "fundamental": candidate.fundamental_score,
                "confidence": candidate.confidence_score,
                "technical_weight": decision.scores.technical_weight,
                "fundamental_weight": decision.scores.fundamental_weight,
            },
            "classification": candidate.classification,
            "quality": {
                "business_quality": decision.quality.business_quality,
                "financial_health": decision.quality.financial_health,
                "growth": decision.quality.growth,
                "valuation": decision.quality.valuation,
                "technical_condition": decision.quality.technical_condition,
                "risk_level": decision.quality.risk_level,
            },
            "confidence": {
                "score": decision.confidence.score,
                "classification": decision.confidence.classification,
                "technical_data_quality": (
                    decision.confidence.technical_data_quality
                ),
                "fundamental_data_quality": (
                    decision.confidence.fundamental_data_quality
                ),
                "missing_data_penalty": decision.confidence.missing_data_penalty,
            },
            "positive_factors": list(decision.positive_factors),
            "risk_factors": list(decision.risk_factors),
            "missing_data": list(decision.missing_data),
            "summary": decision.summary,
        }


class PortfolioExporter:
    """Validate, combine, and save compact portfolio results."""

    SCHEMA_VERSION = "1.3"

    def build_package(
        self,
        *,
        universe_name: str,
        market_data: UniverseMarketDataRefreshResult,
        allocation: PortfolioAllocationResult,
        ranking: RankingResult,
        recommendations: PortfolioRecommendationResult,
        theses: PortfolioThesisResult,
        generated_at: datetime,
    ) -> PortfolioExportPackage:
        self._validate_components(
            universe_name=universe_name,
            market_data=market_data,
            allocation=allocation,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=generated_at,
        )
        return PortfolioExportPackage(
            schema_version=self.SCHEMA_VERSION,
            generated_at=generated_at,
            universe_name=universe_name,
            market_data=market_data,
            allocation=allocation,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
        )

    def save_json(
        self,
        package: PortfolioExportPackage,
        output_path: str | Path,
    ) -> Path:
        if not isinstance(package, PortfolioExportPackage):
            raise TypeError("package must be a PortfolioExportPackage")

        path = Path(output_path)
        if path.suffix.lower() != ".json":
            raise ValueError("output_path must use the .json extension")

        return write_json_atomic(
            path,
            package.to_dict(),
            ensure_ascii=False,
            indent=2,
            trailing_newline=False,
        )

    @staticmethod
    def _validate_components(
        *,
        universe_name: str,
        market_data: UniverseMarketDataRefreshResult,
        allocation: PortfolioAllocationResult,
        ranking: RankingResult,
        recommendations: PortfolioRecommendationResult,
        theses: PortfolioThesisResult,
        generated_at: datetime,
    ) -> None:
        if not isinstance(universe_name, str) or not universe_name.strip():
            raise ValueError("universe_name must be a non-empty string")
        if not isinstance(market_data, UniverseMarketDataRefreshResult):
            raise TypeError(
                "market_data must be a UniverseMarketDataRefreshResult"
            )
        if not isinstance(
            allocation,
            PortfolioAllocationResult,
        ):
            raise TypeError(
                "allocation must be a "
                "PortfolioAllocationResult"
            )
        if not isinstance(ranking, RankingResult):
            raise TypeError("ranking must be a RankingResult")
        if not isinstance(recommendations, PortfolioRecommendationResult):
            raise TypeError(
                "recommendations must be a PortfolioRecommendationResult"
            )
        if not isinstance(theses, PortfolioThesisResult):
            raise TypeError("theses must be a PortfolioThesisResult")
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be a datetime")
        if not market_data.all_ready:
            raise ValueError("market_data must be ready before export")

        ranking_symbols = tuple(candidate.symbol for candidate in ranking.candidates)
        recommendation_symbols = tuple(
            recommendation.symbol
            for recommendation in recommendations.recommendations
        )
        thesis_symbols = tuple(thesis.symbol for thesis in theses.theses)
        market_symbols = tuple(item.symbol for item in market_data.results)
        allocation_symbols = tuple(
            position.symbol
            for position in allocation.positions
        )

        if (
            ranking_symbols != recommendation_symbols
            or ranking_symbols != thesis_symbols
        ):
            raise ValueError(
                "Ranking, recommendation, and thesis components must "
                "contain the same symbols in the same order"
            )

        if ranking_symbols != allocation_symbols:
            raise ValueError(
                "Allocation and portfolio components must contain "
                "the same symbols in the same order"
            )

        if set(ranking_symbols) != set(market_symbols):
            raise ValueError(
                "Market-data and portfolio components must contain "
                "the same symbols"
            )

        if (
            ranking.universe_size != recommendations.universe_size
            or ranking.universe_size != theses.universe_size
            or ranking.universe_size != market_data.universe_size
            or ranking.universe_size != allocation.universe_size
        ):
            raise ValueError(
                "Portfolio components must use the same universe size"
            )

        ranking_ranks = tuple(candidate.rank for candidate in ranking.candidates)
        recommendation_ranks = tuple(
            recommendation.rank
            for recommendation in recommendations.recommendations
        )
        thesis_ranks = tuple(thesis.rank for thesis in theses.theses)
        if ranking_ranks != recommendation_ranks or ranking_ranks != thesis_ranks:
            raise ValueError(
                "Portfolio components must use the same candidate ranks"
            )

        for recommendation, thesis in zip(
            recommendations.recommendations,
            theses.theses,
            strict=True,
        ):
            if recommendation.recommendation != thesis.recommendation_label:
                raise ValueError(
                    "Thesis recommendation labels must match "
                    "recommendation results"
                )

        timestamps = {
            ranking.generated_at,
            recommendations.generated_at,
            theses.generated_at,
            allocation.generated_at,
            generated_at,
        }
        if allocation.currency != ranking.top_candidate.currency:
            raise ValueError(
                "allocation currency must match "
                "the portfolio currency"
            )

        if len(timestamps) != 1:
            raise ValueError(
                "Portfolio components must use the same generated_at timestamp"
            )
