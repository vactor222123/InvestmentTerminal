"""
Run a live portfolio ranking with recommendations, theses,
and JSON export.
"""

from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.yahoo_fundamental_client import (
    YahooFundamentalClient,
)
from investment_terminal.config.universe import (
    MEGA_CAP_TECH,
)
from investment_terminal.database.database import (
    Database,
)
from investment_terminal.exporters.portfolio_exporter import (
    PortfolioExporter,
)
from investment_terminal.portfolio.ranking_engine import (
    RankingEngine,
)
from investment_terminal.portfolio.recommendation_engine import (
    RecommendationEngine,
)
from investment_terminal.portfolio.thesis_generator import (
    InvestmentThesisGenerator,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)
from investment_terminal.services.asset_analysis_service import (
    AssetAnalysisService,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


UNIVERSE_NAME = "Mega Cap Tech"

OUTPUT_PATH = (
    Path("output")
    / "mega_cap_tech_portfolio.json"
)


def main() -> None:
    """
    Execute a live portfolio analysis and save the result as JSON.
    """
    database = Database()
    database.initialize()

    try:
        repository = CandleRepository(
            database
        )

        technical_analysis_service = (
            TechnicalAnalysisService(
                repository=repository,
            )
        )

        fundamental_client = (
            YahooFundamentalClient()
        )

        asset_analysis_service = (
            AssetAnalysisService(
                technical_analysis_service=(
                    technical_analysis_service
                ),
                fundamental_client=fundamental_client,
            )
        )

        ranking_engine = RankingEngine()
        recommendation_engine = (
            RecommendationEngine()
        )
        thesis_generator = (
            InvestmentThesisGenerator()
        )
        portfolio_exporter = (
            PortfolioExporter()
        )

        decisions = [
            asset_analysis_service.analyze(
                symbol=symbol,
                resolution="D",
                currency="USD",
            )
            for symbol in MEGA_CAP_TECH
        ]

        generated_at = datetime.now(
            timezone.utc
        )

        ranking = ranking_engine.rank(
            decisions=decisions,
            generated_at=generated_at,
        )

        recommendation_result = (
            recommendation_engine.recommend(
                ranking=ranking,
                generated_at=generated_at,
            )
        )

        thesis_result = thesis_generator.generate(
            recommendation_result=(
                recommendation_result
            ),
            generated_at=generated_at,
        )

        export_package = (
            portfolio_exporter.build_package(
                universe_name=UNIVERSE_NAME,
                ranking=ranking,
                recommendations=(
                    recommendation_result
                ),
                theses=thesis_result,
                generated_at=generated_at,
            )
        )

        saved_path = portfolio_exporter.save_json(
            package=export_package,
            output_path=OUTPUT_PATH,
        )

        print()
        print("=" * 110)
        print(
            "Investment Terminal Portfolio "
            "Ranking and Recommendations"
        )
        print("=" * 110)
        print(
            f"Universe      : "
            f"{export_package.universe_name}"
        )
        print(
            f"Universe size : "
            f"{export_package.universe_size}"
        )
        print(
            f"Generated     : "
            f"{export_package.generated_at.isoformat()}"
        )
        print("-" * 110)

        print(
            f"{'Rank':<5}"
            f"{'Symbol':<8}"
            f"{'Overall':>10}"
            f"{'Tech':>10}"
            f"{'Fund':>10}"
            f"{'Conf':>10}"
            f"{'Risk':>12}"
            f"{'Recommendation':>20}"
        )

        print("-" * 110)

        for thesis in thesis_result.theses:
            recommendation = thesis.recommendation
            candidate = recommendation.candidate

            print(
                f"{thesis.rank:<5}"
                f"{thesis.symbol:<8}"
                f"{candidate.overall_score:>10.2f}"
                f"{candidate.technical_score:>10.2f}"
                f"{candidate.fundamental_score:>10.2f}"
                f"{candidate.confidence_score:>10.2f}"
                f"{candidate.risk_level:>12}"
                f"{thesis.recommendation_label:>20}"
            )

        top = thesis_result.top_thesis
        candidate = top.recommendation.candidate
        decision = candidate.decision

        print()
        print("=" * 110)
        print("Top Investment Thesis")
        print("=" * 110)
        print(
            f"Symbol            : "
            f"{top.symbol}"
        )
        print(
            f"Rank              : "
            f"#{top.rank}"
        )
        print(
            f"Recommendation    : "
            f"{top.recommendation_label}"
        )
        print(
            f"Overall Score     : "
            f"{top.overall_score:.2f}"
        )
        print(
            f"Technical Score   : "
            f"{candidate.technical_score:.2f}"
        )
        print(
            f"Fundamental Score : "
            f"{candidate.fundamental_score:.2f}"
        )
        print(
            f"Confidence        : "
            f"{top.confidence_score:.2f}"
        )
        print(
            f"Business Quality  : "
            f"{candidate.business_quality}"
        )
        print(
            f"Financial Health  : "
            f"{decision.quality.financial_health}"
        )
        print(
            f"Growth            : "
            f"{decision.quality.growth}"
        )
        print(
            f"Valuation         : "
            f"{decision.quality.valuation}"
        )
        print(
            f"Technical State   : "
            f"{decision.quality.technical_condition}"
        )
        print(
            f"Risk Level        : "
            f"{top.risk_level}"
        )

        print()
        print("Headline")
        print("-" * 110)
        print(top.headline)

        print()
        print("Investment Thesis")
        print("-" * 110)
        print(top.thesis)

        print()
        print("Strengths")
        print("-" * 110)

        for strength in top.strengths:
            print(
                f"+ {strength}"
            )

        if top.risks:
            print()
            print("Risks")
            print("-" * 110)

            for risk in top.risks:
                print(
                    f"- {risk}"
                )

        print()
        print("Analytical Action")
        print("-" * 110)
        print(top.action)

        print()
        print("Export")
        print("-" * 110)
        print(
            f"JSON saved to: "
            f"{saved_path.resolve()}"
        )

        print()
        print(
            "Note: Recommendations and actions are "
            "analytical screening outputs. They are not "
            "personalized financial advice or automatic "
            "trading instructions."
        )

    finally:
        database.close()


if __name__ == "__main__":
    main()