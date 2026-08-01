"""
Tests for compact portfolio JSON export.
"""

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.exporters.portfolio_exporter import (
    PortfolioExporter,
)
from investment_terminal.portfolio.ranking_models import (
    RankingResult,
)
from investment_terminal.portfolio.recommendation_engine import (
    RecommendationEngine,
)
from investment_terminal.portfolio.thesis_generator import (
    InvestmentThesisGenerator,
)
from tests.test_ranking_models import (
    create_candidate,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    17,
    0,
    tzinfo=timezone.utc,
)


def create_ranking() -> RankingResult:
    return RankingResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        candidates=(
            create_candidate(
                rank=1,
                symbol="GOOGL",
            ),
            create_candidate(
                rank=2,
                symbol="MSFT",
            ),
            create_candidate(
                rank=3,
                symbol="AAPL",
            ),
        ),
    )


def create_components():
    ranking = create_ranking()

    recommendations = (
        RecommendationEngine().recommend(
            ranking,
            generated_at=GENERATED_AT,
        )
    )

    theses = (
        InvestmentThesisGenerator().generate(
            recommendations,
            generated_at=GENERATED_AT,
        )
    )

    return ranking, recommendations, theses


def create_package():
    ranking, recommendations, theses = (
        create_components()
    )

    return PortfolioExporter().build_package(
        universe_name="Mega Cap Tech",
        ranking=ranking,
        recommendations=recommendations,
        theses=theses,
        generated_at=GENERATED_AT,
    )


def test_build_package_combines_results() -> None:
    package = create_package()

    assert package.schema_version == "1.1"
    assert package.generated_at == GENERATED_AT
    assert package.universe_name == "Mega Cap Tech"
    assert package.universe_size == 3
    assert package.top_symbol == "GOOGL"

    assert (
        package.ranking.top_candidate.symbol
        == "GOOGL"
    )
    assert (
        package.recommendations
        .top_recommendation
        .symbol
        == "GOOGL"
    )
    assert (
        package.theses.top_thesis.symbol
        == "GOOGL"
    )


def test_build_package_normalizes_universe_name() -> None:
    ranking, recommendations, theses = (
        create_components()
    )

    package = PortfolioExporter().build_package(
        universe_name="  Mega Cap Tech  ",
        ranking=ranking,
        recommendations=recommendations,
        theses=theses,
        generated_at=GENERATED_AT,
    )

    assert package.universe_name == "Mega Cap Tech"


def test_compact_package_is_json_serializable() -> None:
    package = create_package()

    payload = package.to_dict()

    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert payload["schema_version"] == "1.1"
    assert (
        payload["generated_at"]
        == GENERATED_AT.isoformat()
    )

    assert payload["universe"] == {
        "name": "Mega Cap Tech",
        "size": 3,
        "symbols": [
            "GOOGL",
            "MSFT",
            "AAPL",
        ],
    }

    assert (
        payload["summary"]["top_symbol"]
        == "GOOGL"
    )
    assert (
        payload["summary"]["top_rank"]
        == 1
    )
    assert (
        payload["summary"]
        ["top_recommendation"]
        == package.recommendations
        .top_recommendation
        .recommendation
    )

    assert isinstance(
        payload["ranking"]["candidates"],
        list,
    )
    assert isinstance(
        payload["recommendations"]["items"],
        list,
    )
    assert isinstance(
        payload["theses"]["items"],
        list,
    )

    assert '"top_headline"' in serialized
    assert '"top_action"' in serialized


def test_ranking_contains_decision_data_once() -> None:
    payload = create_package().to_dict()

    candidate = (
        payload["ranking"]["candidates"][0]
    )

    assert candidate["symbol"] == "GOOGL"
    assert candidate["rank"] == 1

    assert "scores" in candidate
    assert "quality" in candidate
    assert "confidence" in candidate
    assert "positive_factors" in candidate
    assert "risk_factors" in candidate
    assert "missing_data" in candidate
    assert "summary" in candidate

    assert "decision" not in candidate


def test_recommendations_do_not_repeat_candidates() -> None:
    payload = create_package().to_dict()

    recommendation = (
        payload["recommendations"]["items"][0]
    )

    assert recommendation["symbol"] == "GOOGL"
    assert "recommendation" in recommendation
    assert "rationale" in recommendation
    assert "cautions" in recommendation

    assert "candidate" not in recommendation
    assert "decision" not in recommendation
    assert "scores" not in recommendation


def test_theses_do_not_repeat_recommendation_context() -> None:
    payload = create_package().to_dict()

    thesis = payload["theses"]["items"][0]

    assert thesis["symbol"] == "GOOGL"
    assert "headline" in thesis
    assert "thesis" in thesis
    assert "strengths" in thesis
    assert "risks" in thesis
    assert "action" in thesis

    assert (
        "recommendation_context"
        not in thesis
    )
    assert "candidate" not in thesis
    assert "decision" not in thesis


def test_sections_are_connected_by_symbol_and_rank() -> None:
    payload = create_package().to_dict()

    ranking_items = (
        payload["ranking"]["candidates"]
    )
    recommendation_items = (
        payload["recommendations"]["items"]
    )
    thesis_items = payload["theses"]["items"]

    for (
        ranking_item,
        recommendation_item,
        thesis_item,
    ) in zip(
        ranking_items,
        recommendation_items,
        thesis_items,
        strict=True,
    ):
        assert (
            ranking_item["symbol"]
            == recommendation_item["symbol"]
            == thesis_item["symbol"]
        )

        assert (
            ranking_item["rank"]
            == recommendation_item["rank"]
            == thesis_item["rank"]
        )


def test_save_json_creates_compact_file(
    tmp_path,
) -> None:
    package = create_package()

    output_path = (
        tmp_path
        / "exports"
        / "mega_cap_tech_portfolio.json"
    )

    saved_path = PortfolioExporter().save_json(
        package=package,
        output_path=output_path,
    )

    assert saved_path == output_path
    assert output_path.exists()

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )

    assert (
        payload["universe"]["name"]
        == "Mega Cap Tech"
    )
    assert payload["universe"]["size"] == 3

    assert (
        payload["summary"]["top_symbol"]
        == "GOOGL"
    )

    assert len(
        payload["ranking"]["candidates"]
    ) == 3
    assert len(
        payload["recommendations"]["items"]
    ) == 3
    assert len(
        payload["theses"]["items"]
    ) == 3

    serialized = output_path.read_text(
        encoding="utf-8",
    )

    assert (
        serialized.count(
            '"summary": "Overall condition'
        )
        == 3
    )


def test_build_package_rejects_symbol_order_mismatch() -> None:
    ranking, recommendations, theses = (
        create_components()
    )

    first = recommendations.recommendations[0]
    second = recommendations.recommendations[1]
    third = recommendations.recommendations[2]

    reordered_recommendations = replace(
        recommendations,
        recommendations=(
            replace(
                second,
                candidate=replace(
                    second.candidate,
                    rank=1,
                ),
            ),
            replace(
                first,
                candidate=replace(
                    first.candidate,
                    rank=2,
                ),
            ),
            third,
        ),
    )

    with pytest.raises(
        ValueError,
        match="same symbols in the same order",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            ranking=ranking,
            recommendations=(
                reordered_recommendations
            ),
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_thesis_label_mismatch() -> None:
    ranking, recommendations, theses = (
        create_components()
    )

    first_thesis = theses.theses[0]

    mismatched_recommendation = replace(
        first_thesis.recommendation,
        recommendation="HOLD",
    )

    mismatched_thesis = replace(
        first_thesis,
        recommendation=mismatched_recommendation,
    )

    mismatched_theses = replace(
        theses,
        theses=(
            mismatched_thesis,
            *theses.theses[1:],
        ),
    )

    with pytest.raises(
        ValueError,
        match="recommendation labels",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            ranking=ranking,
            recommendations=recommendations,
            theses=mismatched_theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_timestamp_mismatch() -> None:
    ranking, recommendations, theses = (
        create_components()
    )

    different_time = datetime(
        2026,
        8,
        1,
        18,
        0,
        tzinfo=timezone.utc,
    )

    mismatched_theses = replace(
        theses,
        generated_at=different_time,
    )

    with pytest.raises(
        ValueError,
        match="same generated_at timestamp",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            ranking=ranking,
            recommendations=recommendations,
            theses=mismatched_theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_empty_universe_name() -> None:
    ranking, recommendations, theses = (
        create_components()
    )

    with pytest.raises(
        ValueError,
        match="universe_name",
    ):
        PortfolioExporter().build_package(
            universe_name=" ",
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_invalid_ranking() -> None:
    _, recommendations, theses = (
        create_components()
    )

    with pytest.raises(
        TypeError,
        match="RankingResult",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            ranking=None,
            recommendations=recommendations,
            theses=theses,
            generated_at=GENERATED_AT,
        )


def test_build_package_rejects_invalid_generated_at() -> None:
    ranking, recommendations, theses = (
        create_components()
    )

    with pytest.raises(
        TypeError,
        match="generated_at",
    ):
        PortfolioExporter().build_package(
            universe_name="Mega Cap Tech",
            ranking=ranking,
            recommendations=recommendations,
            theses=theses,
            generated_at="2026-08-01",
        )


def test_save_json_rejects_wrong_extension(
    tmp_path,
) -> None:
    package = create_package()

    with pytest.raises(
        ValueError,
        match=".json",
    ):
        PortfolioExporter().save_json(
            package=package,
            output_path=(
                tmp_path / "portfolio.txt"
            ),
        )


def test_save_json_rejects_invalid_package(
    tmp_path,
) -> None:
    with pytest.raises(
        TypeError,
        match="PortfolioExportPackage",
    ):
        PortfolioExporter().save_json(
            package=None,
            output_path=(
                tmp_path / "portfolio.json"
            ),
        )