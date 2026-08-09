"""
Tests for historical outcome research coverage accounting.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_research_coverage import (
    HistoricalOutcomeResearchCoverage,
    HistoricalOutcomeResearchCoverageService,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


ORIGIN = datetime(
    2026,
    8,
    7,
    15,
    30,
    tzinfo=timezone.utc,
)


def methodology() -> HistoricalOutcomeMethodology:
    return HistoricalOutcomeMethodology.sprint_14_exact_close_v1()


def result(
    status: str,
) -> HistoricalMethodologyAwareObservationResult:
    evidence = None
    if status == "COMPLETE":
        evidence = HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=ORIGIN + timedelta(days=5),
            origin_price=100.0,
            endpoint_price=105.0,
            origin_source="fixture",
            endpoint_source="fixture",
            origin_currency="EUR",
            endpoint_currency="EUR",
            origin_resolution="D",
            endpoint_resolution="D",
        )

    return HistoricalMethodologyAwareObservationResult(
        methodology=methodology(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id="11111111-1111-4111-8111-111111111111",
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=5,
            ),
            status=status,
            evidence=evidence,
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def protocol(
    *,
    allowed: tuple[str, ...] | None = None,
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            (
                methodology().identity_key,
            )
            if allowed is None
            else allowed
        ),
        minimum_complete_sample_size=10,
    )


def test_mixed_statuses_are_all_counted() -> None:
    summary = HistoricalOutcomeResearchCoverageService().summarize(
        results=(
            result("COMPLETE"),
            result("COMPLETE"),
            result("PARTIAL"),
            result("UNAVAILABLE"),
            result("NOT_MATURE"),
        ),
        protocol=protocol(),
    )

    assert summary == HistoricalOutcomeResearchCoverage(
        candidate_count=5,
        eligible_count=2,
        complete_count=2,
        partial_count=1,
        unavailable_count=1,
        not_mature_count=1,
        excluded_count=3,
        coverage_fraction=0.4,
    )


def test_zero_candidates_has_zero_coverage() -> None:
    summary = HistoricalOutcomeResearchCoverageService().summarize(
        results=(),
        protocol=protocol(),
    )

    assert summary.candidate_count == 0
    assert summary.eligible_count == 0
    assert summary.excluded_count == 0
    assert summary.coverage_fraction == 0.0


def test_disallowed_methodology_remains_candidate_but_is_excluded() -> None:
    summary = HistoricalOutcomeResearchCoverageService().summarize(
        results=(
            result("COMPLETE"),
            result("PARTIAL"),
        ),
        protocol=protocol(
            allowed=(
                "TRADING_SESSIONS_EXACT_CLOSE@1",
            )
        ),
    )

    assert summary.candidate_count == 2
    assert summary.complete_count == 1
    assert summary.partial_count == 1
    assert summary.eligible_count == 0
    assert summary.excluded_count == 2
    assert summary.coverage_fraction == 0.0


def test_coverage_is_not_complete_status_fraction_when_protocol_excludes_complete() -> None:
    custom = HistoricalOutcomeResearchProtocol(
        protocol_id="CUSTOM_RESEARCH",
        version=1,
        allowed_methodology_identities=(
            methodology().identity_key,
        ),
        eligible_statuses=(
            "PARTIAL",
        ),
        minimum_complete_sample_size=10,
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
        ),
        missing_evidence_policy="KEEP_VISIBLE",
        uncertainty_policy="SAMPLE_STANDARD_ERROR",
        claim_policy="DESCRIPTIVE_ONLY",
    )

    summary = HistoricalOutcomeResearchCoverageService().summarize(
        results=(
            result("COMPLETE"),
            result("PARTIAL"),
        ),
        protocol=custom,
    )

    assert summary.complete_count == 1
    assert summary.partial_count == 1
    assert summary.eligible_count == 1
    assert summary.coverage_fraction == 0.5


def test_serialization_preserves_all_denominators() -> None:
    summary = HistoricalOutcomeResearchCoverageService().summarize(
        results=(
            result("COMPLETE"),
            result("PARTIAL"),
            result("NOT_MATURE"),
        ),
        protocol=protocol(),
    )

    assert summary.to_dict() == {
        "candidate_count": 3,
        "eligible_count": 1,
        "complete_count": 1,
        "partial_count": 1,
        "unavailable_count": 0,
        "not_mature_count": 1,
        "excluded_count": 2,
        "coverage_fraction": pytest.approx(
            1 / 3
        ),
    }


def test_summary_model_rejects_inconsistent_counts() -> None:
    with pytest.raises(
        ValueError,
        match="status counts",
    ):
        HistoricalOutcomeResearchCoverage(
            candidate_count=2,
            eligible_count=1,
            complete_count=1,
            partial_count=0,
            unavailable_count=0,
            not_mature_count=0,
            excluded_count=1,
            coverage_fraction=0.5,
        )


def test_summary_model_rejects_wrong_coverage_fraction() -> None:
    with pytest.raises(
        ValueError,
        match="coverage_fraction",
    ):
        HistoricalOutcomeResearchCoverage(
            candidate_count=2,
            eligible_count=1,
            complete_count=1,
            partial_count=1,
            unavailable_count=0,
            not_mature_count=0,
            excluded_count=1,
            coverage_fraction=0.75,
        )


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeResearchCoverageService()

    with pytest.raises(
        TypeError,
        match="results",
    ):
        service.summarize(
            results=[],  # type: ignore[arg-type]
            protocol=protocol(),
        )

    with pytest.raises(
        TypeError,
        match="contain only",
    ):
        service.summarize(
            results=(
                object(),  # type: ignore[arg-type]
            ),
            protocol=protocol(),
        )

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.summarize(
            results=(),
            protocol=object(),  # type: ignore[arg-type]
        )
