"""
Tests for the unified investment review package.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.investment_review_package import (
    main,
)
from investment_terminal.review.review_package_builder import (
    InvestmentReviewPackageBuilder,
)
from investment_terminal.review.review_package_exporter import (
    InvestmentReviewPackageExporter,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    18,
    0,
    tzinfo=timezone.utc,
)


def create_package():
    return InvestmentReviewPackageBuilder().build(
        portfolio_name="Test Portfolio",
        data_freshness={"ready": True},
        market_analysis={"regime": "BALANCED"},
        portfolio={"total_value": 10000.0},
        stock_analysis={"items": []},
        etf_analysis={"items": []},
        watchlist={"items": []},
        opportunities={"items": []},
        machine_recommendations={"items": []},
        generated_at=GENERATED_AT,
        warnings=(
            "External news context is not included.",
        ),
    )


def test_builder_creates_required_sections() -> None:
    package = create_package()

    assert package.schema_version == "1.0"
    assert len(package.sections) == 8
    assert package.section(
        "portfolio"
    ).payload["total_value"] == 10000.0


def test_package_is_json_ready() -> None:
    payload = create_package().to_dict()
    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert payload["generated_at"] == (
        GENERATED_AT.isoformat()
    )
    assert (
        "machine_recommendations"
        in payload["sections"]
    )
    assert serialized


def test_exporter_writes_json(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "review.json"
    )

    result = (
        InvestmentReviewPackageExporter()
        .export(
            create_package(),
            path,
        )
    )

    payload = json.loads(
        result.read_text(
            encoding="utf-8",
        )
    )

    assert result == path
    assert payload["portfolio_name"] == (
        "Test Portfolio"
    )


def test_exporter_rejects_invalid_package(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="InvestmentReviewPackage",
    ):
        InvestmentReviewPackageExporter().export(
            None,
            tmp_path / "review.json",
        )


def test_cli_generates_default_package(
    tmp_path: Path,
    capsys,
) -> None:
    output = (
        tmp_path
        / "review.json"
    )

    main(
        [
            "--output",
            str(output),
        ]
    )

    text = capsys.readouterr().out
    payload = json.loads(
        output.read_text(
            encoding="utf-8",
        )
    )

    assert "Investment Review Package" in text
    assert output.exists()
    assert (
        payload["portfolio_name"]
        == "Viktor Investment Portfolio"
    )
    assert (
        payload["sections"]["portfolio"]
        ["cash_value"]
        == 1600.0
    )


def test_cli_prints_json(
    tmp_path: Path,
    capsys,
) -> None:
    output = (
        tmp_path
        / "review.json"
    )

    main(
        [
            "--output",
            str(output),
            "--print-json",
        ]
    )

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload["schema_version"] == "1.0"
    assert len(payload["sections"]) == 8