"""
Tests for explicit historical outcome research eligibility.
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
from investment_terminal.history.historical_outcome_research_eligibility import (
    HistoricalOutcomeEligibilityAssessment,
    HistoricalOutcomeEligibilityService,
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


def evidence_for_status(
    status: str,
) -> HistoricalOutcomeEvidence | None:
    if status != "COMPLETE":
        return None

    return HistoricalOutcomeEvidence(
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


def result(
    status: str,
) -> HistoricalMethodologyAwareObservationResult:
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
            evidence=evidence_for_status(status),
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


def test_complete_observation_is_eligible() -> None:
    assessment = HistoricalOutcomeEligibilityService().assess(
        result=result("COMPLETE"),
        protocol=protocol(),
    )

    assert assessment == HistoricalOutcomeEligibilityAssessment(
        eligible=True,
        reason="ELIGIBLE",
    )


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("PARTIAL", "STATUS_PARTIAL"),
        ("UNAVAILABLE", "STATUS_UNAVAILABLE"),
        ("NOT_MATURE", "STATUS_NOT_MATURE"),
    ],
)
def test_incomplete_statuses_remain_visible_with_reason(
    status: str,
    reason: str,
) -> None:
    assessment = HistoricalOutcomeEligibilityService().assess(
        result=result(status),
        protocol=protocol(),
    )

    assert assessment.eligible is False
    assert assessment.reason == reason
    assert assessment.to_dict() == {
        "eligible": False,
        "reason": reason,
    }


def test_disallowed_methodology_has_explicit_reason() -> None:
    assessment = HistoricalOutcomeEligibilityService().assess(
        result=result("COMPLETE"),
        protocol=protocol(
            allowed=(
                "TRADING_SESSIONS_EXACT_CLOSE@1",
            )
        ),
    )

    assert assessment == HistoricalOutcomeEligibilityAssessment(
        eligible=False,
        reason="METHODOLOGY_NOT_ALLOWED",
    )


def test_methodology_exclusion_precedes_status_exclusion() -> None:
    assessment = HistoricalOutcomeEligibilityService().assess(
        result=result("PARTIAL"),
        protocol=protocol(
            allowed=(
                "TRADING_SESSIONS_EXACT_CLOSE@1",
            )
        ),
    )

    assert assessment.reason == "METHODOLOGY_NOT_ALLOWED"


def test_protocol_can_explicitly_make_complete_ineligible() -> None:
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

    assessment = HistoricalOutcomeEligibilityService().assess(
        result=result("COMPLETE"),
        protocol=custom,
    )

    assert assessment.eligible is False
    assert assessment.reason == "STATUS_NOT_ELIGIBLE"


def test_assess_many_preserves_input_order_and_exclusions() -> None:
    service = HistoricalOutcomeEligibilityService()
    assessments = service.assess_many(
        results=(
            result("COMPLETE"),
            result("PARTIAL"),
            result("NOT_MATURE"),
        ),
        protocol=protocol(),
    )

    assert tuple(
        item.reason
        for item in assessments
    ) == (
        "ELIGIBLE",
        "STATUS_PARTIAL",
        "STATUS_NOT_MATURE",
    )


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeEligibilityService()

    with pytest.raises(
        TypeError,
        match="result",
    ):
        service.assess(
            result=object(),  # type: ignore[arg-type]
            protocol=protocol(),
        )

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.assess(
            result=result("COMPLETE"),
            protocol=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(
        TypeError,
        match="results",
    ):
        service.assess_many(
            results=[],  # type: ignore[arg-type]
            protocol=protocol(),
        )


def test_assessment_rejects_inconsistent_state() -> None:
    with pytest.raises(
        ValueError,
        match="eligible",
    ):
        HistoricalOutcomeEligibilityAssessment(
            eligible=True,
            reason="STATUS_PARTIAL",
        )
