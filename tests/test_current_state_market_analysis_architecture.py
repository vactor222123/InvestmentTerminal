from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_state_contract_does_not_duplicate_analysis_engines() -> None:
    source = (
        ROOT
        / "investment_terminal"
        / "analysis"
        / "current_state_market_analysis.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "RankingEngine",
        "CoverageAwareRecommendationEngine",
        "InvestmentThesisGenerator",
        "PortfolioAllocationEngine",
        "TechnicalAnalysisService",
        "SectorAwareFundamentalScoreService",
        "YahooFinanceClient",
        "YahooFundamentalClient",
    )

    for name in forbidden:
        assert name not in source


def test_portfolio_ranking_remains_existing_live_pipeline_owner() -> None:
    source = (
        ROOT
        / "investment_terminal"
        / "cli"
        / "portfolio_ranking.py"
    ).read_text(
        encoding="utf-8"
    )

    for required in (
        "refresh_market_data(",
        "require_fresh_market_data(",
        "RankingEngine().rank(",
        "CoverageAwareRecommendationEngine()",
        "InvestmentThesisGenerator().generate(",
        "PortfolioAllocationEngine().allocate(",
        "PortfolioExporter()",
        "exporter.build_package(",
    ):
        assert required in source
