"""
Tests for combined analysis export.
"""

import json
from datetime import datetime, timezone

import pytest

from investment_terminal.exporters.analysis_exporter import (
    AnalysisExporter,
)
from investment_terminal.models.fundamental_snapshot import (
    FundamentalDataQuality,
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreBreakdown,
    FundamentalScoreResult,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisResult,
    TechnicalDataQuality,
)
from investment_terminal.services.technical_score_service import (
    TechnicalScoreBreakdown,
    TechnicalScoreResult,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_technical_analysis(
    symbol: str = "MSFT",
) -> TechnicalAnalysisResult:
    return TechnicalAnalysisResult(
        symbol=symbol,
        resolution="D",
        timestamp=GENERATED_AT,
        latest_price=464.72,
        currency="USD",
        sma20=396.87,
        sma50=399.40,
        sma200=433.58,
        ema20=402.19,
        rsi14=74.50,
        macd_line=9.30,
        macd_signal=1.83,
        macd_histogram=7.47,
        atr14=16.02,
        atr_percent=3.45,
        bollinger_upper=439.40,
        bollinger_middle=396.87,
        bollinger_lower=354.33,
        bollinger_bandwidth=21.43,
        price_above_sma20=True,
        price_above_sma50=True,
        price_above_sma200=True,
        sma50_above_sma200=False,
        trend="UPTREND",
        bollinger_position="ABOVE_UPPER_BAND",
        volatility_status="MODERATE",
        data_quality=TechnicalDataQuality(
            candle_count=251,
            recommended_candle_count=200,
            completeness_percent=100.0,
            missing_indicators=(),
            sufficient_for_long_term=True,
        ),
    )


def create_technical_score(
    symbol: str = "MSFT",
) -> TechnicalScoreResult:
    return TechnicalScoreResult(
        symbol=symbol,
        resolution="D",
        raw_score=65.0,
        data_quality_factor=1.0,
        final_score=65.0,
        classification="POSITIVE",
        breakdown=TechnicalScoreBreakdown(
            trend=30.0,
            momentum=22.0,
            volatility=11.0,
            price_position=2.0,
        ),
        positive_factors=(
            "Price remains above SMA200.",
        ),
        risk_factors=(
            "RSI indicates an overbought market.",
        ),
    )


def create_fundamental_snapshot(
    symbol: str = "MSFT",
) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol=symbol,
        currency="USD",
        generated_at=GENERATED_AT,
        market_cap=3_450_000_000_000,
        forward_pe=19.96,
        revenue_growth=0.177,
        earnings_growth=0.317,
        gross_margin=0.6794,
        operating_margin=0.4511,
        net_margin=0.4030,
        return_on_equity=0.3404,
        debt_to_equity=0.29118,
        current_ratio=1.23,
        quick_ratio=1.098,
        operating_cash_flow=182_930_000_000,
        free_cash_flow=16_360_000_000,
        dividend_yield=0.0081,
        payout_ratio=0.1983,
        data_quality=FundamentalDataQuality(
            available_fields=27,
            total_fields=28,
            completeness_percent=96.43,
            missing_fields=(
                "return_on_invested_capital",
            ),
            source="Yahoo Finance",
            fetched_at=GENERATED_AT,
        ),
    )


def create_fundamental_score(
    symbol: str = "MSFT",
) -> FundamentalScoreResult:
    return FundamentalScoreResult(
        symbol=symbol,
        currency="USD",
        raw_score=88.85,
        data_quality_factor=0.9643,
        final_score=85.68,
        classification="EXCELLENT",
        breakdown=FundamentalScoreBreakdown(
            growth=18.0,
            profitability=25.0,
            balance_sheet=15.0,
            cash_flow=15.0,
            valuation=11.85,
            shareholder_returns=4.0,
        ),
        positive_factors=(
            "Revenue growth is strong.",
        ),
        risk_factors=(
            "Some fundamental metrics are unavailable.",
        ),
        missing_fields=(
            "return_on_invested_capital",
        ),
    )


def test_build_package_combines_analysis() -> None:
    package = AnalysisExporter().build_package(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    assert package.schema_version == "1.0"
    assert package.symbol == "MSFT"
    assert package.currency == "USD"

    assert (
        package.data_quality.technical_percent
        == 100.0
    )
    assert (
        package.data_quality.fundamental_percent
        == 96.43
    )
    assert (
        package.data_quality.overall_percent
        == pytest.approx(98.22, abs=0.01)
    )


def test_package_is_json_serializable() -> None:
    package = AnalysisExporter().build_package(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    payload = package.to_dict()
    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert '"schema_version": "1.0"' in serialized
    assert (
        payload["technical"]["analysis"]["timestamp"]
        == GENERATED_AT.isoformat()
    )
    assert isinstance(
        payload["technical"]["score"]
        ["positive_factors"],
        list,
    )
    assert isinstance(
        payload["data_quality"]
        ["fundamental_missing"],
        list,
    )


def test_save_json_creates_file(
    tmp_path,
) -> None:
    package = AnalysisExporter().build_package(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    output_path = (
        tmp_path
        / "exports"
        / "MSFT_analysis.json"
    )

    saved_path = AnalysisExporter().save_json(
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

    assert payload["symbol"] == "MSFT"
    assert (
        payload["fundamental"]
        ["score"]
        ["final_score"]
        == 85.68
    )


def test_build_package_rejects_symbol_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="same symbol",
    ):
        AnalysisExporter().build_package(
            technical_analysis=(
                create_technical_analysis()
            ),
            technical_score=(
                create_technical_score(
                    symbol="AAPL"
                )
            ),
            fundamental_snapshot=(
                create_fundamental_snapshot()
            ),
            fundamental_score=(
                create_fundamental_score()
            ),
            generated_at=GENERATED_AT,
        )


def test_save_json_rejects_wrong_extension(
    tmp_path,
) -> None:
    package = AnalysisExporter().build_package(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    with pytest.raises(
        ValueError,
        match=".json",
    ):
        AnalysisExporter().save_json(
            package=package,
            output_path=(
                tmp_path / "analysis.txt"
            ),
        )