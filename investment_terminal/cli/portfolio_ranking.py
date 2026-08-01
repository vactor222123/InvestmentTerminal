"""
Run a live portfolio ranking with contextual recommendations.
"""

from investment_terminal.clients.yahoo_fundamental_client import (
    YahooFundamentalClient,
)
from investment_terminal.config.universe import (
    MEGA_CAP_TECH,
)
from investment_terminal.database.database import (
    Database,
)
from investment_terminal.portfolio.ranking_engine import (
    RankingEngine,
)
from investment_terminal.portfolio.recommendation_engine import (
    RecommendationEngine,
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


def main() -> None:
    """
    Execute a live portfolio ranking and recommendation run.
    """
    database = Database()
    database.initialize()

    try:
        repository = CandleRepository(database)

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
                technical_analysis_service=technical_analysis_service,
                fundamental_client=fundamental_client,
            )
        )

        ranking_engine = RankingEngine()
        recommendation_engine = (
            RecommendationEngine()
        )

        decisions = [
            asset_analysis_service.analyze(
                symbol=symbol,
                resolution="D",
                currency="USD",
            )
            for symbol in MEGA_CAP_TECH
        ]

        ranking = ranking_engine.rank(
            decisions=decisions,
        )

        recommendation_result = (
            recommendation_engine.recommend(
                ranking=ranking,
            )
        )

        print()
        print("=" * 110)
        print(
            "Investment Terminal Portfolio "
            "Ranking and Recommendations"
        )
        print("=" * 110)
        print(
            f"Universe size : "
            f"{recommendation_result.universe_size}"
        )
        print(
            f"Generated     : "
            f"{recommendation_result.generated_at.isoformat()}"
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

        for recommendation in (
            recommendation_result.recommendations
        ):
            candidate = recommendation.candidate

            print(
                f"{recommendation.rank:<5}"
                f"{recommendation.symbol:<8}"
                f"{candidate.overall_score:>10.2f}"
                f"{candidate.technical_score:>10.2f}"
                f"{candidate.fundamental_score:>10.2f}"
                f"{candidate.confidence_score:>10.2f}"
                f"{candidate.risk_level:>12}"
                f"{recommendation.recommendation:>20}"
            )

        top = (
            recommendation_result
            .top_recommendation
        )

        print()
        print("=" * 110)
        print("Top Portfolio Candidate")
        print("=" * 110)
        print(f"Symbol            : {top.symbol}")
        print(
            f"Rank              : "
            f"#{top.rank}"
        )
        print(
            f"Recommendation    : "
            f"{top.recommendation}"
        )
        print(
            f"Overall Score     : "
            f"{top.overall_score:.2f}"
        )
        print(
            f"Confidence        : "
            f"{top.confidence_score:.2f}"
        )
        print(
            f"Business Quality  : "
            f"{top.candidate.business_quality}"
        )
        print(
            f"Risk Level        : "
            f"{top.risk_level}"
        )
        print(
            f"Classification    : "
            f"{top.candidate.classification}"
        )

        print()
        print("Why")
        print("-" * 110)

        for item in top.rationale:
            print(f"+ {item}")

        if top.cautions:
            print()
            print("Cautions")
            print("-" * 110)

            for item in top.cautions:
                print(f"- {item}")

        print()
        print("Decision Summary")
        print("-" * 110)
        print(top.candidate.decision.summary)

        print()
        print(
            "Note: Recommendations are analytical "
            "screening labels and are not personalized "
            "financial advice."
        )

    finally:
        database.close()


if __name__ == "__main__":
    main()