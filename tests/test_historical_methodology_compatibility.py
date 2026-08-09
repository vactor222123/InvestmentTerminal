"""
Tests for structural methodology compatibility.
"""

from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalEvidenceSelectionPolicy,
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_methodology_compatibility import (
    HistoricalMethodologyCompatibility,
    HistoricalMethodologyCompatibilityService,
)


def methodology(
    *,
    methodology_id: str,
    version: int = 1,
    window_kind: str = "ELAPSED_DAYS",
    endpoint_policy: str = "ELAPSED_DURATION_UTC",
    endpoint_version: int = 1,
    selection_policy: str = "EXACT_TIMESTAMP_CLOSE",
    selection_version: int = 1,
    price_field: str = "CLOSE",
) -> HistoricalOutcomeMethodology:
    return HistoricalOutcomeMethodology(
        methodology_id=methodology_id,
        version=version,
        window_kind=window_kind,
        endpoint_policy=HistoricalEndpointPolicy(
            policy_id=endpoint_policy,
            version=endpoint_version,
        ),
        evidence_selection_policy=HistoricalEvidenceSelectionPolicy(
            policy_id=selection_policy,
            version=selection_version,
            price_field=price_field,
        ),
    )


def test_identical_identity_is_compatible() -> None:
    service = HistoricalMethodologyCompatibilityService()
    left = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
    right = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()

    result = service.assess(
        left=left,
        right=right,
    )

    assert result.status == HistoricalMethodologyCompatibility.COMPATIBLE
    assert result.reasons == (
        "Methodology identity is identical",
    )


def test_same_window_and_price_field_with_different_policy_is_partial() -> None:
    service = HistoricalMethodologyCompatibilityService()

    result = service.assess(
        left=methodology(
            methodology_id="A",
        ),
        right=methodology(
            methodology_id="B",
            endpoint_policy="ELAPSED_DURATION_LOCAL",
        ),
    )

    assert result.status == (
        HistoricalMethodologyCompatibility.PARTIALLY_COMPATIBLE
    )
    assert "Endpoint policies differ" in result.reasons


def test_different_methodology_versions_are_partial() -> None:
    service = HistoricalMethodologyCompatibilityService()

    result = service.assess(
        left=methodology(
            methodology_id="TEST",
            version=1,
        ),
        right=methodology(
            methodology_id="TEST",
            version=2,
        ),
    )

    assert result.status == (
        HistoricalMethodologyCompatibility.PARTIALLY_COMPATIBLE
    )
    assert "Methodology versions differ" in result.reasons


def test_different_window_kind_is_incompatible() -> None:
    service = HistoricalMethodologyCompatibilityService()

    result = service.assess(
        left=methodology(
            methodology_id="ELAPSED",
            window_kind="ELAPSED_DAYS",
        ),
        right=methodology(
            methodology_id="SESSIONS",
            window_kind="TRADING_SESSIONS",
            endpoint_policy="TRADING_SESSION_CLOSE",
            selection_policy="SESSION_CLOSE_EXACT",
        ),
    )

    assert result.status == (
        HistoricalMethodologyCompatibility.INCOMPATIBLE
    )
    assert result.reasons == (
        "Observation window kinds differ",
    )


def test_different_price_field_is_incompatible() -> None:
    service = HistoricalMethodologyCompatibilityService()

    result = service.assess(
        left=methodology(
            methodology_id="CLOSE",
            price_field="CLOSE",
        ),
        right=methodology(
            methodology_id="OPEN",
            price_field="OPEN",
        ),
    )

    assert result.status == (
        HistoricalMethodologyCompatibility.INCOMPATIBLE
    )
    assert result.reasons == (
        "Price fields differ",
    )


def test_output_is_json_ready_and_explicitly_non_statistical() -> None:
    result = HistoricalMethodologyCompatibilityService().assess(
        left=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        right=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
    )

    data = result.to_dict()

    assert data["status"] == "COMPATIBLE"
    assert "not statistical comparability" in data[
        "semantics"
    ]
    assert "effectiveness" in data[
        "semantics"
    ]
