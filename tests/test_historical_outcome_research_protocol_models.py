"""
Tests for canonical historical outcome research-protocol models.
"""

from dataclasses import FrozenInstanceError

import pytest

from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


ELAPSED = "ELAPSED_DAYS_EXACT_CLOSE@1"
SESSIONS = "TRADING_SESSIONS_EXACT_CLOSE@1"


def protocol(
    *,
    version: int = 1,
    minimum: int = 10,
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol(
        protocol_id="descriptive_outcome_research",
        version=version,
        allowed_methodology_identities=(
            ELAPSED,
            SESSIONS,
        ),
        eligible_statuses=(
            "complete",
        ),
        minimum_complete_sample_size=minimum,
        grouping_dimensions=(
            "methodology_identity",
            "window_kind",
            "window_value",
        ),
        missing_evidence_policy="keep_visible",
        uncertainty_policy="sample_standard_error",
        claim_policy="descriptive_only",
    )


def test_protocol_normalizes_and_has_stable_identity() -> None:
    value = protocol()

    assert value.identity_key == (
        "DESCRIPTIVE_OUTCOME_RESEARCH@1"
    )
    assert value.eligible_statuses == (
        "COMPLETE",
    )
    assert value.grouping_dimensions == (
        "METHODOLOGY_IDENTITY",
        "WINDOW_KIND",
        "WINDOW_VALUE",
    )
    assert value.claim_policy == "DESCRIPTIVE_ONLY"


def test_protocol_is_immutable() -> None:
    value = protocol()

    with pytest.raises(
        FrozenInstanceError,
    ):
        value.version = 2  # type: ignore[misc]


def test_protocol_versions_are_distinct() -> None:
    assert protocol(
        version=1
    ).identity_key == "DESCRIPTIVE_OUTCOME_RESEARCH@1"
    assert protocol(
        version=2
    ).identity_key == "DESCRIPTIVE_OUTCOME_RESEARCH@2"
    assert protocol(
        version=1
    ) != protocol(
        version=2
    )


def test_serialization_is_deterministic_and_preserves_policy_identity() -> None:
    value = protocol()

    expected = {
        "protocol_id": "DESCRIPTIVE_OUTCOME_RESEARCH",
        "version": 1,
        "identity_key": "DESCRIPTIVE_OUTCOME_RESEARCH@1",
        "allowed_methodology_identities": [
            ELAPSED,
            SESSIONS,
        ],
        "eligible_statuses": [
            "COMPLETE",
        ],
        "minimum_complete_sample_size": 10,
        "grouping_dimensions": [
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
        ],
        "missing_evidence_policy": "KEEP_VISIBLE",
        "uncertainty_policy": "SAMPLE_STANDARD_ERROR",
        "claim_policy": "DESCRIPTIVE_ONLY",
    }

    assert value.to_dict() == expected
    assert value.to_dict() == expected


def test_descriptive_v1_requires_caller_selected_sample_threshold() -> None:
    value = HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            SESSIONS,
        ),
        minimum_complete_sample_size=12,
    )

    assert value.identity_key == (
        "DESCRIPTIVE_OUTCOME_RESEARCH@1"
    )
    assert value.minimum_complete_sample_size == 12
    assert value.eligible_statuses == (
        "COMPLETE",
    )
    assert value.missing_evidence_policy == "KEEP_VISIBLE"
    assert value.uncertainty_policy == "SAMPLE_STANDARD_ERROR"
    assert value.claim_policy == "DESCRIPTIVE_ONLY"


def test_allows_methodology_is_exact_identity_check() -> None:
    value = protocol()

    assert value.allows_methodology(
        SESSIONS
    )
    assert not value.allows_methodology(
        "TRADING_SESSIONS_EXACT_CLOSE@2"
    )


@pytest.mark.parametrize(
    ("field_name", "replacement", "error_type"),
    [
        ("protocol_id", "", ValueError),
        ("version", 0, ValueError),
        ("version", True, ValueError),
        ("allowed_methodology_identities", (), ValueError),
        ("allowed_methodology_identities", [ELAPSED], TypeError),
        ("eligible_statuses", (), ValueError),
        ("minimum_complete_sample_size", 0, ValueError),
        ("minimum_complete_sample_size", True, ValueError),
        ("grouping_dimensions", (), ValueError),
        ("grouping_dimensions", ["METHODOLOGY_IDENTITY"], TypeError),
        ("missing_evidence_policy", "", ValueError),
        ("uncertainty_policy", "", ValueError),
        ("claim_policy", "", ValueError),
    ],
)
def test_protocol_rejects_invalid_values(
    field_name: str,
    replacement: object,
    error_type: type[Exception],
) -> None:
    kwargs = {
        "protocol_id": "DESCRIPTIVE_OUTCOME_RESEARCH",
        "version": 1,
        "allowed_methodology_identities": (
            ELAPSED,
            SESSIONS,
        ),
        "eligible_statuses": (
            "COMPLETE",
        ),
        "minimum_complete_sample_size": 10,
        "grouping_dimensions": (
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
        ),
        "missing_evidence_policy": "KEEP_VISIBLE",
        "uncertainty_policy": "SAMPLE_STANDARD_ERROR",
        "claim_policy": "DESCRIPTIVE_ONLY",
    }
    kwargs[field_name] = replacement

    with pytest.raises(
        error_type,
    ):
        HistoricalOutcomeResearchProtocol(
            **kwargs,  # type: ignore[arg-type]
        )


def test_protocol_rejects_duplicate_methodology_identity() -> None:
    with pytest.raises(
        ValueError,
        match="unique",
    ):
        HistoricalOutcomeResearchProtocol.descriptive_v1(
            allowed_methodology_identities=(
                ELAPSED,
                ELAPSED,
            ),
            minimum_complete_sample_size=10,
        )


def test_protocol_requires_methodology_and_window_grouping() -> None:
    with pytest.raises(
        ValueError,
        match="must include",
    ):
        HistoricalOutcomeResearchProtocol.descriptive_v1(
            allowed_methodology_identities=(
                ELAPSED,
            ),
            minimum_complete_sample_size=10,
            grouping_dimensions=(
                "METHODOLOGY_IDENTITY",
                "WINDOW_KIND",
            ),
        )


def test_protocol_rejects_unknown_grouping_dimension() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported",
    ):
        HistoricalOutcomeResearchProtocol.descriptive_v1(
            allowed_methodology_identities=(
                ELAPSED,
            ),
            minimum_complete_sample_size=10,
            grouping_dimensions=(
                "METHODOLOGY_IDENTITY",
                "WINDOW_KIND",
                "WINDOW_VALUE",
                "SECTOR",
            ),
        )


def test_optional_grouping_dimensions_are_explicit() -> None:
    value = HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            ELAPSED,
        ),
        minimum_complete_sample_size=10,
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
            "ACTION",
            "SYMBOL",
        ),
    )

    assert value.grouping_dimensions[-2:] == (
        "ACTION",
        "SYMBOL",
    )
