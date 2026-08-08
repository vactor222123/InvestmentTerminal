"""
Tests for historical outcome methodology identity contracts.
"""

from dataclasses import FrozenInstanceError

import pytest

from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEndpointPolicy,
    HistoricalEvidenceSelectionPolicy,
    HistoricalOutcomeMethodology,
)


def test_endpoint_policy_normalizes_identity() -> None:
    policy = HistoricalEndpointPolicy(
        policy_id=" elapsed_duration_utc ",
        version=1,
    )

    assert policy.policy_id == "ELAPSED_DURATION_UTC"
    assert policy.version == 1
    assert policy.identity_key == "ELAPSED_DURATION_UTC@1"


def test_evidence_selection_policy_preserves_price_field() -> None:
    policy = HistoricalEvidenceSelectionPolicy(
        policy_id=" exact_timestamp_close ",
        version=1,
        price_field=" close ",
    )

    assert policy.policy_id == "EXACT_TIMESTAMP_CLOSE"
    assert policy.price_field == "CLOSE"
    assert policy.identity_key == "EXACT_TIMESTAMP_CLOSE@1"


def test_sprint_14_methodology_names_existing_behavior() -> None:
    methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()

    assert methodology.methodology_id == "ELAPSED_DAYS_EXACT_CLOSE"
    assert methodology.version == 1
    assert methodology.identity_key == "ELAPSED_DAYS_EXACT_CLOSE@1"
    assert methodology.window_kind == "ELAPSED_DAYS"
    assert (
        methodology.endpoint_policy.policy_id
        == "ELAPSED_DURATION_UTC"
    )
    assert (
        methodology.evidence_selection_policy.policy_id
        == "EXACT_TIMESTAMP_CLOSE"
    )
    assert methodology.evidence_selection_policy.price_field == "CLOSE"


def test_methodology_is_json_ready() -> None:
    methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()

    assert methodology.to_dict() == {
        "methodology_id": "ELAPSED_DAYS_EXACT_CLOSE",
        "version": 1,
        "identity_key": "ELAPSED_DAYS_EXACT_CLOSE@1",
        "window_kind": "ELAPSED_DAYS",
        "endpoint_policy": {
            "policy_id": "ELAPSED_DURATION_UTC",
            "version": 1,
            "identity_key": "ELAPSED_DURATION_UTC@1",
        },
        "evidence_selection_policy": {
            "policy_id": "EXACT_TIMESTAMP_CLOSE",
            "version": 1,
            "price_field": "CLOSE",
            "identity_key": "EXACT_TIMESTAMP_CLOSE@1",
        },
    }


@pytest.mark.parametrize(
    "version",
    (
        0,
        -1,
        True,
        1.5,
        "1",
    ),
)
def test_endpoint_policy_requires_positive_integer_version(
    version: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        HistoricalEndpointPolicy(
            policy_id="ELAPSED_DURATION_UTC",
            version=version,  # type: ignore[arg-type]
        )


def test_methodology_requires_typed_endpoint_policy() -> None:
    with pytest.raises(
        TypeError,
        match="endpoint_policy",
    ):
        HistoricalOutcomeMethodology(
            methodology_id="TEST",
            version=1,
            window_kind="ELAPSED_DAYS",
            endpoint_policy="ELAPSED_DURATION_UTC",  # type: ignore[arg-type]
            evidence_selection_policy=HistoricalEvidenceSelectionPolicy(
                policy_id="EXACT_TIMESTAMP_CLOSE",
                version=1,
                price_field="CLOSE",
            ),
        )


def test_methodology_requires_typed_evidence_selection_policy() -> None:
    with pytest.raises(
        TypeError,
        match="evidence_selection_policy",
    ):
        HistoricalOutcomeMethodology(
            methodology_id="TEST",
            version=1,
            window_kind="ELAPSED_DAYS",
            endpoint_policy=HistoricalEndpointPolicy(
                policy_id="ELAPSED_DURATION_UTC",
                version=1,
            ),
            evidence_selection_policy="EXACT_TIMESTAMP_CLOSE",  # type: ignore[arg-type]
        )


def test_models_are_frozen() -> None:
    methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()

    with pytest.raises(
        FrozenInstanceError,
    ):
        methodology.version = 2  # type: ignore[misc]


def test_methodology_factory_is_deterministic() -> None:
    first = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
    second = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()

    assert first == second
    assert first.to_dict() == second.to_dict()
