"""
Run a fresh live portfolio analysis with ranking,
recommendations, theses, and JSON export.
"""

from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import (
    YahooFinanceClient,
)
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
from investment_terminal.services.historical_market_service import (
    HistoricalMarketService,
)
from investment_terminal.services.market_data_freshness_service import (
    MarketDataFreshnessService,
)
from investment_terminal.services.market_data_refresh_service import (
    MarketDataRefreshService,
    UniverseMarketDataRefreshResult,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisService,
)


UNIVERSE_NAME = "Mega Cap Tech"
RESOLUTION = "D"
CURRENCY = "USD"

OUTPUT_PATH = (
    Path("output")
    / "mega_cap_tech_portfolio.json"
)


def main() -> None:
    """
    Refresh market data, run portfolio analysis, and export JSON.
    """
    database = Database()
    database.initialize()

    try:
        repository = CandleRepository(
            database
        )

        checked_at = datetime.now(
            timezone.utc
        )

        refresh_result = refresh_market_data(
            repository=repository,
            checked_at=checked_at,
        )

        print_refresh_result(
            refresh_result
        )

        require_fresh_market_data(
            refresh_result
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
                resolution=RESOLUTION,
                currency=CURRENCY,
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

        print_portfolio_result(
            export_package=export_package,
            thesis_result=thesis_result,
            saved_path=saved_path,
        )

    finally:
        database.close()


def refresh_market_data(
    repository: CandleRepository,
    checked_at: datetime,
) -> UniverseMarketDataRefreshResult:
    """
    Ensure all technical market data satisfies freshness policy.
    """
    historical_client = (
        YahooFinanceClient()
    )

    historical_market_service = (
        HistoricalMarketService(
            client=historical_client,
            repository=repository,
        )
    )

    freshness_service = (
        MarketDataFreshnessService(
            repository=repository,
        )
    )

    refresh_service = (
        MarketDataRefreshService(
            freshness_service=freshness_service,
            historical_market_service=(
                historical_market_service
            ),
        )
    )

    return refresh_service.ensure_many(
        symbols=MEGA_CAP_TECH,
        resolution=RESOLUTION,
        currency=CURRENCY,
        checked_at=checked_at,
    )


def require_fresh_market_data(
    result: UniverseMarketDataRefreshResult,
) -> None:
    """
    Stop analysis unless every candle series is fresh.
    """
    if result.all_ready:
        return

    failed_symbols = ", ".join(
        result.failed_symbols
    )

    raise RuntimeError(
        "Portfolio analysis was stopped because "
        "market data still exceeds the 24-hour "
        "freshness limit after refresh. "
        f"Affected symbols: {failed_symbols}."
    )


def print_refresh_result(
    result: UniverseMarketDataRefreshResult,
) -> None:
    """
    Print market-data freshness and refresh statistics.
    """
    print()
    print("=" * 110)
    print("Market Data Freshness")
    print("=" * 110)
    print(
        f"Checked at      : "
        f"{result.checked_at.isoformat()}"
    )
    print(
        f"Universe size   : "
        f"{result.universe_size}"
    )
    print(
        f"Ready           : "
        f"{result.ready_count}"
    )
    print(
        f"Not ready       : "
        f"{result.failed_count}"
    )
    print(
        f"Refresh attempts: "
        f"{result.refreshed_count}"
    )
    print("-" * 110)

    print(
        f"{'Symbol':<10}"
        f"{'Before':<12}"
        f"{'After':<12}"
        f"{'Age hours':>12}"
        f"{'Downloaded':>14}"
        f"{'Inserted':>12}"
        f"{'Ready':>10}"
    )

    print("-" * 110)

    for item in result.results:
        age_hours = (
            f"{item.freshness_after.age_hours:.2f}"
            if item.freshness_after.age_hours
            is not None
            else "N/A"
        )

        ready_text = (
            "YES"
            if item.is_ready
            else "NO"
        )

        print(
            f"{item.symbol:<10}"
            f"{item.freshness_before.status:<12}"
            f"{item.freshness_after.status:<12}"
            f"{age_hours:>12}"
            f"{item.downloaded:>14}"
            f"{item.inserted:>12}"
            f"{ready_text:>10}"
        )

    if not result.all_ready:
        print()
        print(
            "Freshness policy failed for: "
            + ", ".join(
                result.failed_symbols
            )
        )


def print_portfolio_result(
    *,
    export_package,
    thesis_result,
    saved_path: Path,
) -> None:
    """
    Print portfolio ranking and the top investment thesis.
    """
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


if __name__ == "__main__":
    main()