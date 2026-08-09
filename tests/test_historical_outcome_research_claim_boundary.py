"""
Tests for the historical outcome research claim boundary.
"""

import pytest

from investment_terminal.history.historical_outcome_research_claim_boundary import (
    HistoricalOutcomeResearchClaimAssessment,
    HistoricalOutcomeResearchClaimBoundaryService,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_sample_sufficiency import (
    HistoricalOutcomeSampleAssessment,
)


def protocol(
    *,
    claim_policy: str = "DESCRIPTIVE_ONLY",
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol(
        protocol_id="DESCRIPTIVE_OUTCOME_RESEARCH",
        version=1,
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
        ),
        eligible_statuses=(
            "COMPLETE",
        ),
        minimum_complete_sample_size=10,
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
        ),
        missing_evidence_policy="KEEP_VISIBLE",
        uncertainty_policy="SAMPLE_STANDARD_ERROR",
        claim_policy=claim_policy,
    )


def sample(
    *,
    eligible: int,
    minimum: int = 10,
) -> HistoricalOutcomeSampleAssessment:
    sufficient = eligible >= minimum
    return HistoricalOutcomeSampleAssessment(
        status=(
            "SUFFICIENT"
            if sufficient
            else "INSUFFICIENT"
        ),
        eligible_sample_size=eligible,
        minimum_required_sample_size=minimum,
        shortfall=max(
            0,
            minimum - eligible,
        ),
    )


def test_sufficient_sample_allows_descriptive_claims_only() -> None:
    assessment = HistoricalOutcomeResearchClaimBoundaryService().assess(
        protocol=protocol(),
        sample_assessment=sample(
            eligible=10,
        ),
    )

    assert assessment.descriptive_claims_allowed is True
    assert assessment.comparative_claims_allowed is False
    assert assessment.predictive_claims_allowed is False
    assert assessment.causal_claims_allowed is False
    assert assessment.effectiveness_claims_allowed is False
    assert assessment.claims_restricted_by_sample_size is False


def test_insufficient_sample_withholds_research_conclusion() -> None:
    assessment = HistoricalOutcomeResearchClaimBoundaryService().assess(
        protocol=protocol(),
        sample_assessment=sample(
            eligible=9,
        ),
    )

    assert assessment.descriptive_claims_allowed is False
    assert assessment.claims_restricted_by_sample_size is True
    assert "Insufficient eligible sample" in assessment.warning


def test_sufficiency_never_unlocks_predictive_or_effectiveness_claims() -> None:
    assessment = HistoricalOutcomeResearchClaimBoundaryService().assess(
        protocol=protocol(),
        sample_assessment=sample(
            eligible=1000,
        ),
    )

    assert assessment.descriptive_claims_allowed is True
    assert assessment.predictive_claims_allowed is False
    assert assessment.causal_claims_allowed is False
    assert assessment.effectiveness_claims_allowed is False
    assert "do not interpret" in assessment.warning


def test_serialization_is_machine_readable() -> None:
    assessment = HistoricalOutcomeResearchClaimBoundaryService().assess(
        protocol=protocol(),
        sample_assessment=sample(
            eligible=12,
        ),
    )

    assert assessment.to_dict() == {
        "claim_policy": "DESCRIPTIVE_ONLY",
        "sample_status": "SUFFICIENT",
        "descriptive_claims_allowed": True,
        "comparative_claims_allowed": False,
        "predictive_claims_allowed": False,
        "causal_claims_allowed": False,
        "effectiveness_claims_allowed": False,
        "claims_restricted_by_sample_size": False,
        "warning": (
            "Descriptive historical sample only; do not interpret price "
            "movement as recommendation effectiveness, predictive confidence, "
            "or causality"
        ),
    }


def test_unsupported_claim_policy_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported research claim policy",
    ):
        HistoricalOutcomeResearchClaimBoundaryService().assess(
            protocol=protocol(
                claim_policy="PREDICTIVE",
            ),
            sample_assessment=sample(
                eligible=10,
            ),
        )


def test_model_rejects_predictive_permission_under_descriptive_only() -> None:
    with pytest.raises(
        ValueError,
        match="must not allow",
    ):
        HistoricalOutcomeResearchClaimAssessment(
            claim_policy="DESCRIPTIVE_ONLY",
            sample_status="SUFFICIENT",
            descriptive_claims_allowed=True,
            comparative_claims_allowed=False,
            predictive_claims_allowed=True,
            causal_claims_allowed=False,
            effectiveness_claims_allowed=False,
            warning="Not allowed",
        )


def test_model_rejects_descriptive_claim_when_sample_is_insufficient() -> None:
    with pytest.raises(
        ValueError,
        match="sample sufficiency",
    ):
        HistoricalOutcomeResearchClaimAssessment(
            claim_policy="DESCRIPTIVE_ONLY",
            sample_status="INSUFFICIENT",
            descriptive_claims_allowed=True,
            comparative_claims_allowed=False,
            predictive_claims_allowed=False,
            causal_claims_allowed=False,
            effectiveness_claims_allowed=False,
            warning="Not allowed",
        )


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeResearchClaimBoundaryService()

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.assess(
            protocol=object(),  # type: ignore[arg-type]
            sample_assessment=sample(
                eligible=10,
            ),
        )

    with pytest.raises(
        TypeError,
        match="sample_assessment",
    ):
        service.assess(
            protocol=protocol(),
            sample_assessment=object(),  # type: ignore[arg-type]
        )
