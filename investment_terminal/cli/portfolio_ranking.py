"""
Run a live portfolio ranking.
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
    Execute a live portfolio ranking.
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

        print()
        print("=" * 90)
        print("Investment Terminal Portfolio Ranking")
        print("=" * 90)
        print(
            f"Universe size : {ranking.universe_size}"
        )
        print(
            f"Generated     : "
            f"{ranking.generated_at.isoformat()}"
        )
        print("-" * 90)

        print(
            f"{'Rank':<5}"
            f"{'Symbol':<8}"
            f"{'Overall':>10}"
            f"{'Tech':>10}"
            f"{'Fund':>10}"
            f"{'Conf':>10}"
            f"{'Risk':>14}"
        )

        print("-" * 90)

        for candidate in ranking.candidates:
            print(
                f"{candidate.rank:<5}"
                f"{candidate.symbol:<8}"
                f"{candidate.overall_score:>10.2f}"
                f"{candidate.technical_score:>10.2f}"
                f"{candidate.fundamental_score:>10.2f}"
                f"{candidate.confidence_score:>10.2f}"
                f"{candidate.risk_level:>14}"
            )

        top = ranking.top_candidate

        print()
        print("=" * 90)
        print("Top Candidate")
        print("=" * 90)
        print(f"Symbol            : {top.symbol}")
        print(
            f"Overall Score     : "
            f"{top.overall_score:.2f}"
        )
        print(
            f"Business Quality  : "
            f"{top.business_quality}"
        )
        print(
            f"Risk Level        : "
            f"{top.risk_level}"
        )
        print(
            f"Classification    : "
            f"{top.classification}"
        )

        print()
        print("Summary")
        print("-" * 90)
        print(top.decision.summary)

    finally:
        database.close()


if __name__ == "__main__":
    main()