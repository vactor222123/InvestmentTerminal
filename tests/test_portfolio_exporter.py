"""Tests for compact portfolio export with market-data freshness."""

import json
from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from investment_terminal.exporters.portfolio_exporter import PortfolioExporter
from investment_terminal.portfolio.allocation_engine import (
    PortfolioAllocationEngine,
)
from investment_terminal.portfolio.ranking_models import RankingResult
from investment_terminal.portfolio.recommendation_engine import RecommendationEngine
from investment_terminal.portfolio.thesis_generator import InvestmentThesisGenerator
from investment_terminal.services.market_data_freshness_service import (
    MarketDataFreshnessResult,
)
from investment_terminal.services.market_data_refresh_service import (
    MarketDataRefreshResult,
    UniverseMarketDataRefreshResult,
)
from tests.test_ranking_models import create_candidate


GENERATED_AT = datetime(2026, 8, 1, 17, 0, tzinfo=timezone.utc)
CHECKED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def create_ranking() -> RankingResult:
    return RankingResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        candidates=(
            create_candidate(rank=1, symbol="GOOGL"),
            create_candidate(rank=2, symbol="MSFT"),
            create_candidate(rank=3, symbol="AAPL"),
        ),
    )


def create_freshness(symbol: str) -> MarketDataFreshnessResult:
    return MarketDataFreshnessResult(
        symbol=symbol,
        resolution="D",
        checked_at=CHECKED_AT,
        maximum_age_hours=24.0,
        status="FRESH",
        last_candle_at=datetime(
            2026, 7, 31, 4, 0, tzinfo=timezone.utc
        ),
        age_hours=32.0,
        policy="TRADING_SESSION",
        expected_session_date=date(2026, 7, 31),
        last_candle_session_date=date(2026, 7, 31),
    )


def create_market_data(
    symbols=("GOOGL", "MSFT", "AAPL"),
) -> UniverseMarketDataRefreshResult:
    return UniverseMarketDataRefreshResult(
        checked_at=CHECKED_AT,
        results=tuple(
            MarketDataRefreshResult(
                symbol=symbol,
                resolution="D",
                checked_at=CHECKED_AT,
                freshness_before=create_freshness(symbol),
                freshness_after=create_freshness(symbol),
                import_result=None,
            )
            for symbol in symbols
        ),
    )


def create_components():
    ranking = create_ranking()
    recommendations = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )
    theses = InvestmentThesisGenerator().generate(
        recommendations,
        generated_at=GENERATED_AT,
    )
    allocation = PortfolioAllocationEngine().allocate(
        recommendations=recommendations,
        total_capital=100_000.0,
        profile="BALANCED",
        currency="USD",
        generated_at=GENERATED_AT,
    )
    return ranking, recommendations, theses, allocation


def create_package():
    (
        ranking,
        recommendations,
        theses,
        allocation,
    ) = create_components()
    return PortfolioExporter().build_package(
        universe_name="Mega Cap Tech",
        market_data=create_market_data(),
        allocation=allocation,
        ranking=ranking,
        recommendations=recommendations,
        theses=theses,
        generated_at=GENERATED_AT,
    )


def test_build_package_combines_results() -> None:
    package = create_package()
    assert package.schema_version == "1.3"
    assert package.universe_size == 3
    assert package.top_symbol == "GOOGL"
    assert package.market_data.all_ready is True


def test_compact_package_contains_market_data() -> None:
    payload = create_package().to_dict()
    assert payload["schema_version"] == "1.3"
    assert payload["market_data"]["all_ready"] is True
    assert payload["market_data"]["ready_count"] == 3
    assert payload["market_data"]["failed_count"] == 0
    assert payload["market_data"]["refreshed_count"] == 0
    assert len(payload["market_data"]["items"]) == 3

    item = payload["market_data"]["items"][0]
    assert item == {
        "symbol": "GOOGL",
        "resolution": "D",
        "policy": "TRADING_SESSION",
        "status": "FRESH",
        "is_ready": True,
        "last_candle_at": "2026-07-31T04:00:00+00:00",
        "age_hours": 32.0,
        "maximum_age_hours": 24.0,
        "expected_session_date": "2026-07-31",
        "last_candle_session_date": "2026-07-31",
        "refresh_attempted": False,
        "downloaded": 0,
        "inserted": 0,
        "duplicates": 0,
        "stored_total": None,
    }


def test_summary_contains_market_data_status() -> None:
    summary = create_package().to_dict()["summary"]
    assert summary["market_data_ready"] is True
    assert summary["market_data_checked_at"] == CHECKED_AT.isoformat()
    assert summary["allocation_profile"] == "BALANCED"
    assert summary["allocation_total_capital"] == 100_000.0
    assert summary["allocation_cash_weight"] == 0.10




def test_compact_package_contains_allocation() -> None:
    payload = create_package().to_dict()

    allocation = payload["allocation"]

    assert allocation["schema_version"] == "1.0"
    assert allocation["profile"] == "BALANCED"
    assert allocation["currency"] == "USD"
    assert allocation["total_capital"] == 100_000.0
    assert allocation["invested_amount"] == 90_000.0
    assert allocation["cash_amount"] == 10_000.0
    assert allocation["invested_weight"] == 0.90
    assert allocation["cash_weight"] == 0.10
    assert len(allocation["positions"]) == 3

    assert [
        position["symbol"]
        for position in allocation["positions"]
    ] == [
        "GOOGL",
        "MSFT",
        "AAPL",
    ]

    assert sum(
        position["target_weight"]
        for position in allocation["positions"]
    ) == pytest.approx(0.90)


def test_allocation_does_not_repeat_decision_objects() -> None:
    allocation = (
        create_package()
        .to_dict()["allocation"]
    )

    position = allocation["positions"][0]

    assert "decision" not in position
    assert "candidate" not in position
    assert "recommendation_context" not in position


def test_build_package_rejects_invalid_allocation() -> None:
    (
        ranking,
        recommendations,
        theses,
        _,
    ) = create_components()

    with pytest.raises(
        TypeError,
        match="PortfolioAllocationResult",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            market_data=create_market_data(),
            allocation=None,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_market_data_does_not_duplicate_full_freshness_objects() -> None:
    payload = create_package().to_dict()
    item = payload["market_data"]["items"][0]
    assert "freshness_before" not in item
    assert "freshness_after" not in item
    assert "import" not in item


def test_sections_are_connected_by_symbol() -> None:
    payload = create_package().to_dict()
    market_symbols = [
        item["symbol"]
        for item in payload["market_data"]["items"]
    ]
    ranking_symbols = [
        item["symbol"]
        for item in payload["ranking"]["candidates"]
    ]
    recommendation_symbols = [
        item["symbol"]
        for item in payload["recommendations"]["items"]
    ]
    thesis_symbols = [
        item["symbol"]
        for item in payload["theses"]["items"]
    ]

    assert (
        market_symbols
        == ranking_symbols
        == recommendation_symbols
        == thesis_symbols
    )


def test_market_data_input_order_does_not_need_to_match_ranking() -> None:
    (
        ranking,
        recommendations,
        theses,
        allocation,
    ) = create_components()

    package = PortfolioExporter().build_package(
        universe_name="Mega Cap Tech",
        market_data=create_market_data(
            ("MSFT", "AAPL", "GOOGL")
        ),
        allocation=allocation,
        ranking=ranking,
        recommendations=recommendations,
        theses=theses,
        generated_at=GENERATED_AT,
    )

    payload = package.to_dict()

    assert [
        item["symbol"]
        for item in payload["market_data"]["items"]
    ] == [
        "GOOGL",
        "MSFT",
        "AAPL",
    ]


def test_save_json_creates_file(tmp_path) -> None:
    output_path = tmp_path / "exports" / "portfolio.json"
    saved = PortfolioExporter().save_json(create_package(), output_path)
    assert saved == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.3"
    assert payload["market_data"]["items"][0]["policy"] == "TRADING_SESSION"


def test_build_package_rejects_market_symbol_mismatch() -> None:
    (
        ranking,
        recommendations,
        theses,
        allocation,
    ) = create_components()

    with pytest.raises(
        ValueError,
        match="same symbols",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            market_data=create_market_data(
                ("GOOGL", "MSFT", "META")
            ),
            allocation=allocation,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_not_ready_market_data() -> None:
    (
        ranking,
        recommendations,
        theses,
        allocation,
    ) = create_components()
    stale = replace(
        create_freshness("GOOGL"),
        status="STALE",
        last_candle_session_date=date(2026, 7, 30),
    )
    market_data = UniverseMarketDataRefreshResult(
        checked_at=CHECKED_AT,
        results=(
            MarketDataRefreshResult(
                symbol="GOOGL",
                resolution="D",
                checked_at=CHECKED_AT,
                freshness_before=stale,
                freshness_after=stale,
                import_result=__import__(
                    "investment_terminal.services.historical_market_service",
                    fromlist=["HistoricalImportResult"],
                ).HistoricalImportResult(
                    symbol="GOOGL",
                    resolution="D",
                    downloaded=1,
                    inserted=0,
                    duplicates=1,
                    stored_total=100,
                    start=datetime(2026, 7, 23, tzinfo=timezone.utc),
                    end=datetime(2026, 8, 2, tzinfo=timezone.utc),
                ),
            ),
            *create_market_data(("MSFT", "AAPL")).results,
        ),
    )
    with pytest.raises(ValueError, match="must be ready"):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            market_data=market_data,
            allocation=allocation,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_invalid_market_data() -> None:
    (
        ranking,
        recommendations,
        theses,
        allocation,
    ) = create_components()
    with pytest.raises(TypeError, match="UniverseMarketDataRefreshResult"):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            market_data=None,
            allocation=allocation,
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_timestamp_mismatch() -> None:
    (
        ranking,
        recommendations,
        theses,
        allocation,
    ) = create_components()
    with pytest.raises(ValueError, match="same generated_at timestamp"):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            market_data=create_market_data(),
            allocation=allocation,
            ranking=ranking,
            recommendations=recommendations,
            theses=replace(
                theses,
                generated_at=datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc),
            ),
            generated_at=GENERATED_AT,
        )


def test_save_json_rejects_wrong_extension(tmp_path) -> None:
    with pytest.raises(ValueError, match=".json"):
        PortfolioExporter().save_json(create_package(), tmp_path / "portfolio.txt")


def test_save_json_rejects_invalid_package(tmp_path) -> None:
    with pytest.raises(TypeError, match="PortfolioExportPackage"):
        PortfolioExporter().save_json(None, tmp_path / "portfolio.json")