"""Tests for integrated Review Package generation and atomic export."""

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from investment_terminal.context.external_context_sentiment import (
    ExternalContextSentimentEvidence,
)
from investment_terminal.review.integrated_review_package_service import (
    IntegratedReviewPackageService,
)
from tests.test_external_context_review_adapter import (
    evidence as context_evidence,
)
from tests.test_integrated_evidence_assembly import (
    assemble,
    discovery_evidence,
)


def complete_evidence():
    etf, sector, screening = discovery_evidence()
    context = context_evidence(
        "context-1",
        12,
    )
    sentiment = ExternalContextSentimentEvidence(
        context_id="context-1",
        label="NEGATIVE",
        assessed_at=datetime(
            2026,
            8,
            12,
            tzinfo=timezone.utc,
        ),
        method="rules",
        method_version="1",
    )
    return assemble(
        external_context=(
            context,
        ),
        context_sentiment=(
            sentiment,
        ),
        etf_discovery=etf,
        sector_analysis=sector,
        screening=screening,
    )


def test_generate_reuses_existing_review_contract() -> None:
    evidence = complete_evidence()

    package = IntegratedReviewPackageService.generate(
        evidence
    )

    assert package.schema_version == "1.0"
    assert package.generated_at == evidence.assembled_at
    assert package.portfolio_name == "Personal Portfolio"
    assert tuple(
        section.name
        for section in package.sections
    ) == package.REQUIRED_SECTIONS


def test_generate_projects_all_integrated_evidence() -> None:
    package = IntegratedReviewPackageService.generate(
        complete_evidence()
    )

    market = package.section(
        "market_analysis"
    ).payload
    assert market["status"] == "CONNECTED"
    assert market[
        "integrated_evidence"
    ]["coverage_status"] == "COMPLETE"
    assert market[
        "market_discovery"
    ]["status"] == "COMPLETE"
    assert market[
        "market_discovery"
    ]["recommendation_authorized"] is False
    assert market[
        "market_discovery"
    ]["screening"]["ranking_authorized"] is False

    etf = package.section(
        "etf_analysis"
    ).payload
    assert etf["status"] == "CONNECTED"
    assert etf["recommendation_authorized"] is False
    assert etf["evidence"]["candidate_count"] == 2

    context = package.section(
        "external_context"
    ).payload
    assert context["status"] == "READY"
    assert context["sentiment_counts"]["NEGATIVE"] == 1


def test_generate_preserves_missing_evidence_and_warnings() -> None:
    package = IntegratedReviewPackageService.generate(
        assemble()
    )

    market = package.section(
        "market_analysis"
    ).payload
    assert market[
        "integrated_evidence"
    ]["missing_evidence"] == [
        "EXTERNAL_CONTEXT",
        "ETF_DISCOVERY",
        "SECTOR_ANALYSIS",
        "SCREENING",
    ]
    assert market[
        "market_discovery"
    ]["status"] == "PARTIAL"
    assert package.section(
        "etf_analysis"
    ).payload == {
        "status": "NO_EVIDENCE",
        "evidence": None,
    }
    assert package.section(
        "external_context"
    ).payload["status"] == "NO_EVIDENCE"
    assert (
        "ETF discovery evidence is not available."
        in package.warnings
    )


def test_portfolio_is_explicitly_cost_basis_only() -> None:
    package = IntegratedReviewPackageService.generate(
        complete_evidence()
    )

    portfolio = package.section(
        "portfolio"
    ).payload
    assert portfolio["status"] == "COST_BASIS_ONLY"
    assert portfolio["market_value"] is None
    assert (
        "Portfolio market-value evidence is not included."
        in package.warnings
    )


def test_generate_and_export_writes_complete_json(
    tmp_path: Path,
) -> None:
    output = tmp_path / "review.json"

    result = IntegratedReviewPackageService.generate_and_export(
        complete_evidence(),
        output,
    )

    payload = json.loads(
        output.read_text(
            encoding="utf-8",
        )
    )
    assert result.output_path == output
    assert result.package.to_dict() == payload
    assert payload["schema_version"] == "1.0"
    assert len(payload["sections"]) == 9


def test_export_failure_preserves_previous_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "review.json"
    output.write_text(
        '{"state":"previous"}\n',
        encoding="utf-8",
    )

    def fail_replace(
        source: object,
        destination: object,
    ) -> None:
        raise OSError(
            "replace failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        fail_replace,
    )

    with pytest.raises(
        OSError,
        match="replace failed",
    ):
        IntegratedReviewPackageService.generate_and_export(
            complete_evidence(),
            output,
        )

    assert output.read_text(
        encoding="utf-8",
    ) == '{"state":"previous"}\n'
    assert list(
        tmp_path.glob(
            ".review.json.*.tmp"
        )
    ) == []


def test_generate_rejects_untyped_input() -> None:
    with pytest.raises(
        TypeError,
        match="IntegratedInvestmentReviewEvidence",
    ):
        IntegratedReviewPackageService.generate(
            object()
        )
