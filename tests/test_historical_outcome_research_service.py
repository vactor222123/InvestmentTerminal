"""
Tests for protocol-aware historical outcome research orchestration.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalEvidenceSelectionPolicy,
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)


ORIGIN = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def methodology(
    *,
    methodology_id: str = "ELAPSED_DAYS_EXACT_CLOSE",
    version: int = 1,
    kind: str = "ELAPSED_DAYS",
) -> HistoricalOutcomeMethodology:
    return HistoricalOutcomeMethodology(
        methodology_id=methodology_id,
        version=version,
        window_kind=kind,
        endpoint_policy=HistoricalEndpointPolicy(
            policy_id=(
                "ELAPSED_DURATION_UTC"
                if kind == "ELAPSED_DAYS"
                else "TRADING_SESSION_CLOSE"
            ),
            version=1,
        ),
        evidence_selection_policy=HistoricalEvidenceSelectionPolicy(
            policy_id=(
                "EXACT_TIMESTAMP_CLOSE"
                if kind == "ELAPSED_DAYS"
                else "SESSION_CLOSE_EXACT"
            ),
            version=1,
            price_field="CLOSE",
        ),
    )


def result(
    *,
    status: str,
    movement: float | None = None,
    window_value: int = 5,
    methodology_value: HistoricalOutcomeMethodology | None = None,
    origin_day_offset: int = 0,
) -> HistoricalMethodologyAwareObservationResult:
    selected_methodology = (
        methodology()
        if methodology_value is None
        else methodology_value
    )
    origin = ORIGIN + timedelta(
        days=origin_day_offset
    )
    endpoint = origin + timedelta(
        days=window_value
    )

    evidence = None
    outcome = None

    if status == "COMPLETE":
        assert movement is not None
        origin_price = 100.0
        endpoint_price = origin_price * (
            1.0 + movement
        )
        evidence = HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=origin,
            endpoint_at=endpoint,
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            origin_source="fixture",
            endpoint_source="fixture",
            origin_currency="EUR",
            endpoint_currency="EUR",
            origin_resolution="D",
            endpoint_resolution="D",
        )
        outcome = HistoricalRecommendationOutcome(
            instrument_key="IWDA",
            currency="EUR",
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            price_change=endpoint_price - origin_price,
            price_change_fraction=(
                endpoint_price / origin_price
            ) - 1.0,
            origin_source="fixture",
            endpoint_source="fixture",
        )

    return HistoricalMethodologyAwareObservationResult(
        methodology=selected_methodology,
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=(
                f"11111111-1111-4111-8111-{origin_day_offset + 1:012d}"
            ),
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=origin,
            window=HistoricalObservationWindow(
                kind=selected_methodology.window_kind,
                value=window_value,
            ),
            status=status,
            evidence=evidence,
            warnings=(),
        ),
        outcome=outcome,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def protocol(
    *,
    minimum: int = 2,
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
            "TRADING_SESSIONS_EXACT_CLOSE@1",
        ),
        minimum_complete_sample_size=minimum,
    )


def test_sufficient_cohort_runs_full_research_pipeline() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="COMPLETE",
                movement=0.10,
                origin_day_offset=0,
            ),
            result(
                status="COMPLETE",
                movement=-0.05,
                origin_day_offset=1,
            ),
            result(
                status="PARTIAL",
                origin_day_offset=2,
            ),
        ),
        protocol=protocol(
            minimum=2,
        ),
    )

    assert len(output) == 1
    cohort = output[0]

    assert cohort.coverage.candidate_count == 3
    assert cohort.coverage.eligible_count == 2
    assert cohort.coverage.partial_count == 1
    assert cohort.sample_assessment.status == "SUFFICIENT"

    assert cohort.descriptive_summary is not None
    assert cohort.descriptive_summary.count == 2
    assert (
        cohort.descriptive_summary.mean_price_change_fraction
        == pytest.approx(0.025)
    )

    assert cohort.uncertainty is not None
    assert cohort.uncertainty.standard_error_of_mean is not None

    assert cohort.claim_assessment.descriptive_claims_allowed is True
    assert cohort.claim_assessment.effectiveness_claims_allowed is False


def test_insufficient_cohort_keeps_diagnostics_but_blocks_claims() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="COMPLETE",
                movement=0.05,
            ),
            result(
                status="NOT_MATURE",
                origin_day_offset=1,
            ),
        ),
        protocol=protocol(
            minimum=3,
        ),
    )

    cohort = output[0]

    assert cohort.sample_assessment.status == "INSUFFICIENT"
    assert cohort.sample_assessment.shortfall == 2
    assert cohort.descriptive_summary is not None
    assert cohort.descriptive_summary.count == 1
    assert cohort.uncertainty is not None
    assert cohort.uncertainty.standard_error_of_mean is None
    assert cohort.claim_assessment.descriptive_claims_allowed is False
    assert cohort.claim_assessment.claims_restricted_by_sample_size is True


def test_no_eligible_outcomes_has_no_descriptive_or_uncertainty_summary() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="PARTIAL",
            ),
            result(
                status="NOT_MATURE",
                origin_day_offset=1,
            ),
        ),
        protocol=protocol(
            minimum=2,
        ),
    )

    cohort = output[0]

    assert cohort.coverage.eligible_count == 0
    assert cohort.descriptive_summary is None
    assert cohort.uncertainty is None
    assert cohort.sample_assessment.status == "INSUFFICIENT"


def test_multiple_methodologies_are_never_pooled() -> None:
    sessions = methodology(
        methodology_id="TRADING_SESSIONS_EXACT_CLOSE",
        kind="TRADING_SESSIONS",
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="COMPLETE",
                movement=0.03,
                methodology_value=methodology(),
            ),
            result(
                status="COMPLETE",
                movement=0.04,
                methodology_value=sessions,
                origin_day_offset=1,
            ),
        ),
        protocol=protocol(
            minimum=1,
        ),
    )

    assert len(output) == 2
    identities = [
        item.cohort.value_for(
            "METHODOLOGY_IDENTITY"
        )
        for item in output
    ]
    assert identities == [
        "ELAPSED_DAYS_EXACT_CLOSE@1",
        "TRADING_SESSIONS_EXACT_CLOSE@1",
    ]


def test_different_window_values_are_separate_cohorts() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="COMPLETE",
                movement=0.03,
                window_value=5,
            ),
            result(
                status="COMPLETE",
                movement=0.04,
                window_value=10,
                origin_day_offset=1,
            ),
        ),
        protocol=protocol(
            minimum=1,
        ),
    )

    assert len(output) == 2
    assert {
        item.cohort.value_for(
            "WINDOW_VALUE"
        )
        for item in output
    } == {
        "5",
        "10",
    }


def test_disallowed_methodology_stays_visible_as_excluded_candidate() -> None:
    restricted_protocol = HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            "TRADING_SESSIONS_EXACT_CLOSE@1",
        ),
        minimum_complete_sample_size=1,
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="COMPLETE",
                movement=0.05,
            ),
        ),
        protocol=restricted_protocol,
    )

    cohort = output[0]

    assert cohort.coverage.candidate_count == 1
    assert cohort.coverage.eligible_count == 0
    assert cohort.coverage.excluded_count == 1
    assert cohort.descriptive_summary is None


def test_eligible_observation_without_outcome_is_rejected() -> None:
    broken = HistoricalMethodologyAwareObservationResult(
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
            status="COMPLETE",
            evidence=HistoricalOutcomeEvidence(
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
            ),
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )

    with pytest.raises(
        ValueError,
        match="eligible observation must contain",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=(
                broken,
            ),
            protocol=protocol(
                minimum=1,
            ),
        )


def test_output_is_json_ready_and_keeps_claim_boundary() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            result(
                status="COMPLETE",
                movement=0.05,
            ),
        ),
        protocol=protocol(
            minimum=1,
        ),
    )

    data = output[0].to_dict()

    assert data["protocol_identity"] == (
        "DESCRIPTIVE_OUTCOME_RESEARCH@1"
    )
    assert data["sample_assessment"]["status"] == "SUFFICIENT"
    assert (
        data["claim_assessment"]["effectiveness_claims_allowed"]
        is False
    )
    assert (
        data["claim_assessment"]["predictive_claims_allowed"]
        is False
    )


def test_empty_input_returns_no_cohorts() -> None:
    assert HistoricalOutcomeResearchService().analyze(
        results=(),
        protocol=protocol(),
    ) == ()


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeResearchService()

    with pytest.raises(
        TypeError,
        match="results",
    ):
        service.analyze(
            results=[],  # type: ignore[arg-type]
            protocol=protocol(),
        )

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.analyze(
            results=(),
            protocol=object(),  # type: ignore[arg-type]
        )
