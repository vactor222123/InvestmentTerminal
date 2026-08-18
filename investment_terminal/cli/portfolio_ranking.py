"""
Run a fresh live portfolio analysis with ranking, recommendations,
theses, and compact JSON export.
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.clients.yahoo_fundamental_client import (
    YahooFundamentalClient,
)
from investment_terminal.database.database import Database
from investment_terminal.exporters.portfolio_exporter import (
    PortfolioExporter,
    PortfolioExportPackage,
)
from investment_terminal.market.company_classification_registry import (
    CompanyClassificationRegistry,
)
from investment_terminal.portfolio.allocation_engine import (
    PortfolioAllocationEngine,
)
from investment_terminal.portfolio.allocation_models import (
    ALLOCATION_PROFILES,
    PortfolioAllocationResult,
)
from investment_terminal.portfolio.ranking_engine import RankingEngine
from investment_terminal.portfolio.coverage_aware_recommendation_engine import (
    CoverageAwareRecommendationEngine,
)
from investment_terminal.portfolio.thesis_generator import InvestmentThesisGenerator
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.services.asset_analysis_service import AssetAnalysisService
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
from investment_terminal.services.sector_aware_fundamental_score_service import (
    SectorAwareFundamentalScoreService,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from investment_terminal.universe.universe_loader import (
    UniverseLoader,
)
from investment_terminal.universe.universe_models import (
    InvestmentUniverse,
)


DEFAULT_UNIVERSE_KEY = "mega_cap_tech"
DEFAULT_RESOLUTION = "D"
DEFAULT_CURRENCY = "USD"
DEFAULT_OUTPUT_DIRECTORY = Path("output")
DEFAULT_ALLOCATION_PROFILE = "BALANCED"
DEFAULT_ALLOCATION_CAPITAL = 100_000.0
DEFAULT_ALLOCATION_SIZE = 5

SUPPORTED_RESOLUTIONS = (
    "D",
    "W",
    "M",
)


@dataclass(frozen=True, slots=True)
class PortfolioRankingOptions:
    """Validated command-line options for one portfolio run."""

    universe_key: str
    capital: float
    profile: str
    currency: str
    resolution: str
    output_path: Path
    allocation_size: int


def main(
    argv: Sequence[str] | None = None,
) -> PortfolioExportPackage:
    options = parse_arguments(argv)
    database = Database()
    database.initialize()

    try:
        repository = CandleRepository(database)
        universe = UniverseLoader().load(
            options.universe_key
        )
        checked_at = datetime.now(timezone.utc)

        refresh_result = refresh_market_data(
            repository=repository,
            universe=universe,
            resolution=options.resolution,
            currency=options.currency,
            checked_at=checked_at,
        )
        print_refresh_result(refresh_result)
        require_fresh_market_data(refresh_result)

        technical_analysis_service = TechnicalAnalysisService(
            repository=repository,
        )
        fundamental_client = YahooFundamentalClient()
        classification_registry = (
            CompanyClassificationRegistry.load()
        )
        fundamental_score_service = (
            SectorAwareFundamentalScoreService(
                client=fundamental_client,
                registry=classification_registry,
            )
        )
        asset_analysis_service = AssetAnalysisService(
            technical_analysis_service=technical_analysis_service,
            fundamental_client=fundamental_client,
            fundamental_score_service=fundamental_score_service,
        )

        decisions = [
            asset_analysis_service.analyze(
                symbol=symbol,
                resolution=options.resolution,
                currency=options.currency,
            )
            for symbol in universe.symbols
        ]

        generated_at = datetime.now(timezone.utc)
        ranking = RankingEngine().rank(
            decisions=decisions,
            generated_at=generated_at,
        )
        recommendation_result = (
            CoverageAwareRecommendationEngine()
            .recommend(
                ranking=ranking,
                generated_at=generated_at,
            )
        )
        thesis_result = InvestmentThesisGenerator().generate(
            recommendation_result=recommendation_result,
            generated_at=generated_at,
        )

        allocation_result = (
            PortfolioAllocationEngine().allocate(
                recommendations=recommendation_result,
                total_capital=options.capital,
                profile=options.profile,
                currency=options.currency,
                generated_at=generated_at,
                max_positions=options.allocation_size,
            )
        )

        exporter = PortfolioExporter()
        export_package = exporter.build_package(
            universe_name=universe.name,
            market_data=refresh_result,
            allocation=allocation_result,
            ranking=ranking,
            recommendations=recommendation_result,
            theses=thesis_result,
            generated_at=generated_at,
        )
        saved_path = exporter.save_json(
            package=export_package,
            output_path=options.output_path,
        )

        print_portfolio_result(
            export_package=export_package,
            thesis_result=thesis_result,
            allocation_result=allocation_result,
            saved_path=saved_path,
        )
        return export_package
    finally:
        database.close()


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> PortfolioRankingOptions:
    """Parse and normalize command-line options."""
    parser = build_argument_parser()
    namespace = parser.parse_args(argv)

    universe_key = (
        UniverseLoader
        ._normalize_universe_name(
            namespace.universe
        )
    )
    profile = namespace.profile.upper()
    currency = namespace.currency.upper()
    resolution = namespace.resolution.upper()

    output_path = (
        namespace.output
        if namespace.output is not None
        else build_output_path(
            universe_key
        )
    )

    return PortfolioRankingOptions(
        universe_key=universe_key,
        capital=namespace.capital,
        profile=profile,
        currency=currency,
        resolution=resolution,
        output_path=output_path,
        allocation_size=namespace.allocation_size,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the portfolio-ranking command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Refresh market data, analyze a configured universe, "
            "rank candidates, generate recommendations and theses, "
            "build a target allocation, and export compact JSON."
        ),
    )

    parser.add_argument(
        "--universe",
        default=DEFAULT_UNIVERSE_KEY,
        help=(
            "Universe file name from data/universes without the "
            ".txt extension. Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--capital",
        type=positive_float,
        default=DEFAULT_ALLOCATION_CAPITAL,
        help=(
            "Capital used by the allocation engine. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--allocation-size",
        type=positive_int,
        default=DEFAULT_ALLOCATION_SIZE,
        help=(
            "Maximum number of ranked candidates receiving "
            "non-zero portfolio weights. Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--profile",
        type=str.upper,
        choices=ALLOCATION_PROFILES,
        default=DEFAULT_ALLOCATION_PROFILE,
        help="Allocation profile. Default: %(default)s.",
    )
    parser.add_argument(
        "--currency",
        type=non_empty_upper_text,
        default=DEFAULT_CURRENCY,
        help="Analysis and allocation currency. Default: %(default)s.",
    )
    parser.add_argument(
        "--resolution",
        type=str.upper,
        choices=SUPPORTED_RESOLUTIONS,
        default=DEFAULT_RESOLUTION,
        help="Market-data resolution. Default: %(default)s.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional JSON output path. When omitted, the file is "
            "written to output/<universe>_portfolio.json."
        ),
    )

    return parser


def positive_float(value: str) -> float:
    """Argparse type requiring a finite value greater than zero."""
    try:
        numeric = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "capital must be a number"
        ) from exc

    if numeric <= 0 or numeric == float("inf") or numeric != numeric:
        raise argparse.ArgumentTypeError(
            "capital must be a finite number greater than zero"
        )

    return numeric


def positive_int(value: str) -> int:
    """Argparse type requiring an integer greater than zero."""
    try:
        numeric = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be an integer"
        ) from exc

    if numeric <= 0:
        raise argparse.ArgumentTypeError(
            "value must be greater than zero"
        )

    return numeric


def non_empty_upper_text(value: str) -> str:
    """Argparse type for normalized non-empty text."""
    normalized = value.strip().upper()

    if not normalized:
        raise argparse.ArgumentTypeError(
            "value must be a non-empty string"
        )

    return normalized


def build_output_path(
    universe_key: str,
) -> Path:
    """Build a deterministic JSON output path for a universe."""
    normalized_key = (
        UniverseLoader
        ._normalize_universe_name(
            universe_key
        )
    )

    return (
        DEFAULT_OUTPUT_DIRECTORY
        / f"{normalized_key}_portfolio.json"
    )


def refresh_market_data(
    repository: CandleRepository,
    universe: InvestmentUniverse,
    resolution: str,
    currency: str,
    checked_at: datetime,
) -> UniverseMarketDataRefreshResult:
    historical_market_service = HistoricalMarketService(
        client=YahooFinanceClient(),
        repository=repository,
    )
    freshness_service = MarketDataFreshnessService(
        repository=repository,
    )
    refresh_service = MarketDataRefreshService(
        freshness_service=freshness_service,
        historical_market_service=historical_market_service,
    )
    return refresh_service.ensure_many(
        symbols=universe.symbols,
        resolution=resolution,
        currency=currency,
        checked_at=checked_at,
    )


def require_fresh_market_data(
    result: UniverseMarketDataRefreshResult,
) -> None:
    if result.all_ready:
        return

    failed_symbols = ", ".join(result.failed_symbols)
    raise RuntimeError(
        "Portfolio analysis was stopped because market data did not "
        "satisfy the trading-session freshness policy after refresh. "
        f"Affected symbols: {failed_symbols}."
    )


def print_refresh_result(
    result: UniverseMarketDataRefreshResult,
) -> None:
    print()
    print("=" * 118)
    print("Market Data Freshness")
    print("=" * 118)
    print(f"Checked at      : {result.checked_at.isoformat()}")
    print(f"Universe size   : {result.universe_size}")
    print(f"Ready           : {result.ready_count}")
    print(f"Not ready       : {result.failed_count}")
    print(f"Refresh attempts: {result.refreshed_count}")
    print("-" * 118)
    print(
        f"{'Symbol':<9}"
        f"{'Policy':<18}"
        f"{'Before':<10}"
        f"{'After':<10}"
        f"{'Session':<12}"
        f"{'Expected':<12}"
        f"{'Age h':>9}"
        f"{'Downloaded':>12}"
        f"{'Inserted':>10}"
        f"{'Ready':>8}"
    )
    print("-" * 118)

    for item in result.results:
        freshness = item.freshness_after
        age_hours = (
            f"{freshness.age_hours:.2f}"
            if freshness.age_hours is not None
            else "N/A"
        )
        session = (
            freshness.last_candle_session_date.isoformat()
            if freshness.last_candle_session_date is not None
            else "N/A"
        )
        expected = (
            freshness.expected_session_date.isoformat()
            if freshness.expected_session_date is not None
            else "N/A"
        )
        print(
            f"{item.symbol:<9}"
            f"{freshness.policy:<18}"
            f"{item.freshness_before.status:<10}"
            f"{freshness.status:<10}"
            f"{session:<12}"
            f"{expected:<12}"
            f"{age_hours:>9}"
            f"{item.downloaded:>12}"
            f"{item.inserted:>10}"
            f"{('YES' if item.is_ready else 'NO'):>8}"
        )

    if not result.all_ready:
        print()
        print("Freshness policy failed for: " + ", ".join(result.failed_symbols))


def print_portfolio_result(
    *,
    export_package,
    thesis_result,
    allocation_result: PortfolioAllocationResult,
    saved_path: Path,
) -> None:
    print()
    print("=" * 110)
    print("Investment Terminal Portfolio Ranking and Recommendations")
    print("=" * 110)
    print(f"Universe      : {export_package.universe_name}")
    print(f"Universe size : {export_package.universe_size}")
    print(f"Generated     : {export_package.generated_at.isoformat()}")
    print(f"Market data   : {'READY' if export_package.market_data.all_ready else 'FAILED'}")
    print(f"Data checked  : {export_package.market_data.checked_at.isoformat()}")
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
        candidate = thesis.recommendation.candidate
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
    print(f"Symbol            : {top.symbol}")
    print(f"Rank              : #{top.rank}")
    print(f"Recommendation    : {top.recommendation_label}")
    print(f"Overall Score     : {top.overall_score:.2f}")
    print(f"Technical Score   : {candidate.technical_score:.2f}")
    print(f"Fundamental Score : {candidate.fundamental_score:.2f}")
    print(f"Confidence        : {top.confidence_score:.2f}")
    print(f"Business Quality  : {candidate.business_quality}")
    print(f"Financial Health  : {decision.quality.financial_health}")
    print(f"Growth            : {decision.quality.growth}")
    print(f"Valuation         : {decision.quality.valuation}")
    print(f"Technical State   : {decision.quality.technical_condition}")
    print(f"Risk Level        : {top.risk_level}")

    print("\nHeadline")
    print("-" * 110)
    print(top.headline)
    print("\nInvestment Thesis")
    print("-" * 110)
    print(top.thesis)
    print("\nStrengths")
    print("-" * 110)
    for strength in top.strengths:
        print(f"+ {strength}")

    if top.risks:
        print("\nRisks")
        print("-" * 110)
        for risk in top.risks:
            print(f"- {risk}")

    print("\nAnalytical Action")
    print("-" * 110)
    print(top.action)

    print_allocation_result(
        allocation_result
    )

    print("\nExport")
    print("-" * 110)
    print(f"JSON saved to: {saved_path.resolve()}")
    print()
    print(
        "Note: Recommendations and actions are analytical screening "
        "outputs. They are not personalized financial advice or "
        "automatic trading instructions."
    )


def print_allocation_result(
    result: PortfolioAllocationResult,
) -> None:
    """
    Print the generated target portfolio allocation.
    """
    print()
    print("=" * 110)
    print("Target Portfolio Allocation")
    print("=" * 110)
    print(
        f"Profile          : "
        f"{result.constraints.profile}"
    )
    print(
        f"Total capital    : "
        f"{result.total_capital:,.2f} "
        f"{result.currency}"
    )
    print(
        f"Invested amount  : "
        f"{result.invested_amount:,.2f} "
        f"{result.currency}"
    )
    print(
        f"Cash reserve     : "
        f"{result.cash_amount:,.2f} "
        f"{result.currency} "
        f"({result.cash_weight * 100.0:.2f}%)"
    )
    print(
        f"Maximum position : "
        f"{result.constraints.maximum_position_weight * 100.0:.2f}%"
    )
    print("-" * 110)

    print(
        f"{'Rank':<6}"
        f"{'Symbol':<10}"
        f"{'Recommendation':<18}"
        f"{'Risk':<12}"
        f"{'Weight':>12}"
        f"{'Amount':>18}"
        f"{'Alloc. score':>16}"
    )

    print("-" * 110)

    for position in result.positions:
        print(
            f"{position.rank:<6}"
            f"{position.symbol:<10}"
            f"{position.recommendation_label:<18}"
            f"{position.risk_level:<12}"
            f"{position.target_percent:>11.2f}%"
            f"{position.target_amount:>16,.2f} "
            f"{result.currency:<3}"
            f"{position.allocation_score:>13.2f}"
        )

    print("-" * 110)
    print(
        f"{'CASH':<46}"
        f"{result.cash_weight * 100.0:>11.2f}%"
        f"{result.cash_amount:>16,.2f} "
        f"{result.currency}"
    )

    print()
    print("Allocation Rationale")
    print("-" * 110)

    for position in result.positions:
        print(
            f"- {position.explanation}"
        )


if __name__ == "__main__":
    main()
