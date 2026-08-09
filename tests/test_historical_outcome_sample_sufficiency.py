"""
Tests for historical outcome research sample sufficiency.
"""

import pytest

from investment_terminal.history.historical_outcome_research_coverage import (
    HistoricalOutcomeResearchCoverage,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_sample_sufficiency import (
    HistoricalOutcomeSampleAssessment,
    HistoricalOutcomeSampleSufficiencyService,
)


def coverage(
    *,
    candidates: int,
    eligible: int,
) -> HistoricalOutcomeResearchCoverage:
    return HistoricalOutcomeResearchCoverage(
        candidate_count=candidates,
        eligible_count=eligible,
        complete_count=candidates,
        partial_count=0,
        unavailable_count=0,
        not_mature_count=0,
        excluded_count=candidates - eligible,
        coverage_fraction=(
            0.0
            if candidates == 0
            else eligible / candidates
        ),
    )


def protocol(
    *,
    minimum: int,
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
        ),
        minimum_complete_sample_size=minimum,
    )


def test_below_threshold_is_insufficient() -> None:
    assessment = HistoricalOutcomeSampleSufficiencyService().assess(
        coverage=coverage(
            candidates=10,
            eligible=9,
        ),
        protocol=protocol(
            minimum=10,
        ),
    )

    assert assessment == HistoricalOutcomeSampleAssessment(
        status="INSUFFICIENT",
        eligible_sample_size=9,
        minimum_required_sample_size=10,
        shortfall=1,
    )
    assert assessment.sufficient is False


def test_exact_threshold_is_sufficient() -> None:
    assessment = HistoricalOutcomeSampleSufficiencyService().assess(
        coverage=coverage(
            candidates=10,
            eligible=10,
        ),
        protocol=protocol(
            minimum=10,
        ),
    )

    assert assessment.status == "SUFFICIENT"
    assert assessment.sufficient is True
    assert assessment.shortfall == 0


def test_above_threshold_is_sufficient() -> None:
    assessment = HistoricalOutcomeSampleSufficiencyService().assess(
        coverage=coverage(
            candidates=15,
            eligible=12,
        ),
        protocol=protocol(
            minimum=10,
        ),
    )

    assert assessment.status == "SUFFICIENT"
    assert assessment.eligible_sample_size == 12
    assert assessment.shortfall == 0


def test_zero_eligible_sample_is_insufficient() -> None:
    assessment = HistoricalOutcomeSampleSufficiencyService().assess(
        coverage=coverage(
            candidates=0,
            eligible=0,
        ),
        protocol=protocol(
            minimum=5,
        ),
    )

    assert assessment.status == "INSUFFICIENT"
    assert assessment.shortfall == 5


def test_threshold_comes_from_protocol_not_service_default() -> None:
    service = HistoricalOutcomeSampleSufficiencyService()
    sample = coverage(
        candidates=8,
        eligible=8,
    )

    low_threshold = service.assess(
        coverage=sample,
        protocol=protocol(
            minimum=5,
        ),
    )
    high_threshold = service.assess(
        coverage=sample,
        protocol=protocol(
            minimum=10,
        ),
    )

    assert low_threshold.status == "SUFFICIENT"
    assert high_threshold.status == "INSUFFICIENT"


def test_serialization_is_explicit() -> None:
    assessment = HistoricalOutcomeSampleSufficiencyService().assess(
        coverage=coverage(
            candidates=12,
            eligible=7,
        ),
        protocol=protocol(
            minimum=10,
        ),
    )

    assert assessment.to_dict() == {
        "status": "INSUFFICIENT",
        "sufficient": False,
        "eligible_sample_size": 7,
        "minimum_required_sample_size": 10,
        "shortfall": 3,
    }


def test_assessment_rejects_inconsistent_status() -> None:
    with pytest.raises(
        ValueError,
        match="status does not match",
    ):
        HistoricalOutcomeSampleAssessment(
            status="SUFFICIENT",
            eligible_sample_size=4,
            minimum_required_sample_size=5,
            shortfall=1,
        )


def test_assessment_rejects_inconsistent_shortfall() -> None:
    with pytest.raises(
        ValueError,
        match="shortfall",
    ):
        HistoricalOutcomeSampleAssessment(
            status="INSUFFICIENT",
            eligible_sample_size=4,
            minimum_required_sample_size=5,
            shortfall=0,
        )


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeSampleSufficiencyService()

    with pytest.raises(
        TypeError,
        match="coverage",
    ):
        service.assess(
            coverage=object(),  # type: ignore[arg-type]
            protocol=protocol(
                minimum=5,
            ),
        )

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.assess(
            coverage=coverage(
                candidates=5,
                eligible=5,
            ),
            protocol=object(),  # type: ignore[arg-type]
        )
