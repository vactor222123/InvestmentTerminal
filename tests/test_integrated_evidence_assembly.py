"""Tests for typed integrated investment-review evidence assembly."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import json

import pytest

from investment_terminal.context.external_context_sentiment import (
    ExternalContextSentimentEvidence,
)
from investment_terminal.portfolio.portfolio_snapshot_models import (
    PortfolioSnapshot,
)
from investment_terminal.review.integrated_evidence_assembly import (
    IntegratedInvestmentReviewEvidence,
    IntegratedInvestmentReviewEvidenceAssembler,
)
from investment_terminal.universe.etf_discovery import (
    ETFDiscoveryEvidenceBuilder,
)
from investment_terminal.universe.screening_pipeline import (
    ScreeningPipeline,
)
from investment_terminal.universe.sector_analysis import (
    SectorAnalysisEvidenceBuilder,
)
from tests.test_etf_discovery import (
    EM,
    STOCK,
    WORLD,
    characteristics,
    composition,
    timestamp,
    universe,
)
from tests.test_external_context_review_adapter import (
    evidence as context_evidence,
)
from tests.test_portfolio_exporter import (
    create_package,
)
from tests.test_screening_pipeline import (
    policy,
)


ASSEMBLED_AT = datetime(
    2026,
    8,
    20,
    12,
    tzinfo=timezone.utc,
)


def portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_name="Personal Portfolio",
        base_currency="EUR",
        total_value=0.0,
        invested_value=0.0,
        cash_value=0.0,
        monthly_contribution=0.0,
        asset_breakdown=(),
        sleeve_breakdown=(),
        strategy_breakdown=(),
    )


def discovery_evidence():
    maintained = universe(
        WORLD,
        STOCK,
        EM,
    )
    etf = ETFDiscoveryEvidenceBuilder.build(
        maintained,
        assessed_at=timestamp(12),
        characteristics=(
            characteristics(WORLD),
            characteristics(EM),
        ),
        compositions=(
            composition(WORLD),
            composition(EM),
        ),
    )
    sector = SectorAnalysisEvidenceBuilder.build(
        maintained,
        (),
        assessed_at=timestamp(12),
    )
    screening = ScreeningPipeline.evaluate(
        maintained,
        policy(),
        (),
        evaluated_at=timestamp(12),
    )
    return etf, sector, screening


def assemble(
    **overrides,
) -> IntegratedInvestmentReviewEvidence:
    values = {
        "assembled_at": ASSEMBLED_AT,
        "portfolio": portfolio(),
        "current_state_market": create_package(),
    }
    values.update(
        overrides
    )
    return IntegratedInvestmentReviewEvidenceAssembler.assemble(
        **values
    )


def test_assembly_preserves_typed_evidence_and_is_json_ready() -> None:
    etf, sector, screening = discovery_evidence()
    first = context_evidence(
        "first",
        11,
    )
    second = context_evidence(
        "second",
        12,
    )
    sentiment = ExternalContextSentimentEvidence(
        context_id="second",
        label="NEGATIVE",
        assessed_at=timestamp(12),
        method="rules",
        method_version="1",
    )

    result = assemble(
        external_context=(
            second,
            first,
        ),
        context_sentiment=(
            sentiment,
        ),
        etf_discovery=etf,
        sector_analysis=sector,
        screening=screening,
    )

    assert result.coverage_status == "COMPLETE"
    assert result.missing_evidence == ()
    assert result.universe_key == "GLOBAL@1"
    assert tuple(
        item.record.context_id
        for item in result.external_context
    ) == (
        "first",
        "second",
    )
    payload = result.to_dict()
    assert payload["portfolio"]["portfolio_name"] == (
        "Personal Portfolio"
    )
    assert payload["current_state_market"]["schema_version"] == (
        "1.3"
    )
    assert json.dumps(
        payload,
        allow_nan=False,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        result.schema_version = "2"  # type: ignore[misc]


def test_missing_optional_evidence_remains_explicit() -> None:
    result = assemble()

    assert result.coverage_status == "PARTIAL"
    assert result.missing_evidence == (
        "EXTERNAL_CONTEXT",
        "ETF_DISCOVERY",
        "SECTOR_ANALYSIS",
        "SCREENING",
    )
    assert result.to_dict()["etf_discovery"] is None


def test_context_and_sentiment_must_be_unique_and_associated() -> None:
    item = context_evidence(
        "context-1",
        11,
    )
    assessment = ExternalContextSentimentEvidence(
        context_id="missing",
        label="NEUTRAL",
        assessed_at=timestamp(12),
        method="rules",
        method_version="1",
    )

    with pytest.raises(
        ValueError,
        match="unique context_id",
    ):
        assemble(
            external_context=(
                item,
                item,
            )
        )

    with pytest.raises(
        ValueError,
        match="unknown context_id",
    ):
        assemble(
            external_context=(
                item,
            ),
            context_sentiment=(
                assessment,
            ),
        )


def test_future_evidence_fails_closed() -> None:
    future_market = replace(
        create_package(),
        generated_at=datetime(
            2026,
            8,
            21,
            tzinfo=timezone.utc,
        ),
    )

    with pytest.raises(
        ValueError,
        match="current_state_market cannot be later",
    ):
        assemble(
            current_state_market=future_market
        )

    with pytest.raises(
        ValueError,
        match="external_context cannot be later",
    ):
        assemble(
            assembled_at=datetime(
                2026,
                8,
                11,
                1,
                tzinfo=timezone.utc,
            ),
            external_context=(
                context_evidence(
                    "future",
                    12,
                ),
            ),
        )


def test_discovery_evidence_must_share_universe_identity() -> None:
    etf, _, _ = discovery_evidence()
    other_universe = universe(
        WORLD,
    )
    object.__setattr__(
        other_universe.universe,
        "universe_id",
        "OTHER",
    )
    sector = SectorAnalysisEvidenceBuilder.build(
        other_universe,
        (),
        assessed_at=timestamp(12),
    )

    with pytest.raises(
        ValueError,
        match="one universe identity",
    ):
        assemble(
            etf_discovery=etf,
            sector_analysis=sector,
        )


def test_current_state_market_must_be_ready() -> None:
    market = create_package()
    object.__setattr__(
        market.market_data.results[0].freshness_after,
        "status",
        "STALE",
    )

    with pytest.raises(
        ValueError,
        match="requires ready market data",
    ):
        assemble(
            current_state_market=market
        )


def test_rejects_untyped_evidence() -> None:
    with pytest.raises(
        TypeError,
        match="PortfolioSnapshot",
    ):
        assemble(
            portfolio=object()
        )

    with pytest.raises(
        TypeError,
        match="external_context must be a tuple",
    ):
        assemble(
            external_context=[]
        )


def test_rejects_unsupported_schema_version() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported integrated evidence schema_version",
    ):
        IntegratedInvestmentReviewEvidence(
            schema_version="2.0",
            assembled_at=ASSEMBLED_AT,
            portfolio=portfolio(),
            current_state_market=create_package(),
        )
