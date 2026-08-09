"""
Tests for exact historical research cohort identity.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_cohort import (
    HistoricalOutcomeCohortService,
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


ORIGIN = datetime(
    2026,
    8,
    7,
    15,
    30,
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
    methodology_value: HistoricalOutcomeMethodology | None = None,
    window_value: int = 5,
    recommendation_key: str = "WORLD",
    symbol: str | None = "IWDA",
    action: str | None = "BUY",
) -> HistoricalMethodologyAwareObservationResult:
    selected_methodology = (
        methodology()
        if methodology_value is None
        else methodology_value
    )
    endpoint = ORIGIN + timedelta(
        days=window_value
    )
    evidence = HistoricalOutcomeEvidence(
        instrument_key=(
            symbol
            if symbol is not None
            else recommendation_key
        ),
        origin_at=ORIGIN,
        endpoint_at=endpoint,
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
        methodology=selected_methodology,
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id="11111111-1111-4111-8111-111111111111",
            recommendation_key=recommendation_key,
            symbol=symbol,
            action=action,
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind=selected_methodology.window_kind,
                value=window_value,
            ),
            status="COMPLETE",
            evidence=evidence,
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def protocol(
    *,
    grouping_dimensions: tuple[str, ...] | None = None,
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
            "ELAPSED_DAYS_EXACT_CLOSE@2",
            "TRADING_SESSIONS_EXACT_CLOSE@1",
        ),
        minimum_complete_sample_size=10,
        grouping_dimensions=grouping_dimensions,
    )


def test_required_dimensions_create_stable_identity() -> None:
    key = HistoricalOutcomeCohortService().build(
        result=result(),
        protocol=protocol(),
    )

    assert key.identity_key == (
        "DESCRIPTIVE_OUTCOME_RESEARCH@1"
        "::METHODOLOGY_IDENTITY=ELAPSED_DAYS_EXACT_CLOSE@1"
        "|WINDOW_KIND=ELAPSED_DAYS"
        "|WINDOW_VALUE=5"
    )
    assert key.value_for(
        "methodology_identity"
    ) == "ELAPSED_DAYS_EXACT_CLOSE@1"


def test_different_methodology_version_is_different_cohort() -> None:
    service = HistoricalOutcomeCohortService()

    v1 = service.build(
        result=result(
            methodology_value=methodology(
                version=1
            )
        ),
        protocol=protocol(),
    )
    v2 = service.build(
        result=result(
            methodology_value=methodology(
                version=2
            )
        ),
        protocol=protocol(),
    )

    assert v1.identity_key != v2.identity_key


def test_different_window_value_is_different_cohort() -> None:
    service = HistoricalOutcomeCohortService()

    five = service.build(
        result=result(
            window_value=5
        ),
        protocol=protocol(),
    )
    ten = service.build(
        result=result(
            window_value=10
        ),
        protocol=protocol(),
    )

    assert five.identity_key != ten.identity_key


def test_different_window_kind_is_different_cohort() -> None:
    service = HistoricalOutcomeCohortService()

    elapsed = service.build(
        result=result(),
        protocol=protocol(),
    )
    sessions = service.build(
        result=result(
            methodology_value=methodology(
                methodology_id="TRADING_SESSIONS_EXACT_CLOSE",
                kind="TRADING_SESSIONS",
            )
        ),
        protocol=protocol(),
    )

    assert elapsed.identity_key != sessions.identity_key


def test_optional_action_and_symbol_dimensions_are_explicit() -> None:
    custom_protocol = protocol(
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
            "ACTION",
            "SYMBOL",
        )
    )
    service = HistoricalOutcomeCohortService()

    buy = service.build(
        result=result(
            action="BUY",
            symbol="IWDA",
        ),
        protocol=custom_protocol,
    )
    hold = service.build(
        result=result(
            action="HOLD",
            symbol="IWDA",
        ),
        protocol=custom_protocol,
    )
    other_symbol = service.build(
        result=result(
            action="BUY",
            symbol="EUNL",
        ),
        protocol=custom_protocol,
    )

    assert buy.identity_key != hold.identity_key
    assert buy.identity_key != other_symbol.identity_key
    assert [
        item["name"]
        for item in buy.to_dict()[
            "dimensions"
        ]
    ] == [
        "METHODOLOGY_IDENTITY",
        "WINDOW_KIND",
        "WINDOW_VALUE",
        "ACTION",
        "SYMBOL",
    ]


def test_recommendation_key_grouping_is_protocol_controlled() -> None:
    without_key = protocol()
    with_key = protocol(
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
            "RECOMMENDATION_KEY",
        )
    )
    service = HistoricalOutcomeCohortService()

    world_without = service.build(
        result=result(
            recommendation_key="WORLD"
        ),
        protocol=without_key,
    )
    tech_without = service.build(
        result=result(
            recommendation_key="TECH"
        ),
        protocol=without_key,
    )
    world_with = service.build(
        result=result(
            recommendation_key="WORLD"
        ),
        protocol=with_key,
    )
    tech_with = service.build(
        result=result(
            recommendation_key="TECH"
        ),
        protocol=with_key,
    )

    assert world_without == tech_without
    assert world_with != tech_with


def test_missing_optional_grouping_value_is_explicit_error() -> None:
    custom_protocol = protocol(
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
            "ACTION",
        )
    )

    with pytest.raises(
        ValueError,
        match="ACTION is unavailable",
    ):
        HistoricalOutcomeCohortService().build(
            result=result(
                action=None
            ),
            protocol=custom_protocol,
        )


def test_group_separates_exact_cohorts_and_is_deterministic() -> None:
    service = HistoricalOutcomeCohortService()
    grouped = service.group(
        results=(
            result(
                window_value=10,
            ),
            result(
                window_value=5,
                recommendation_key="WORLD",
            ),
            result(
                window_value=5,
                recommendation_key="TECH",
            ),
        ),
        protocol=protocol(),
    )

    assert len(grouped) == 2
    assert [
        key.value_for(
            "WINDOW_VALUE"
        )
        for key, _ in grouped
    ] == [
        "10",
        "5",
    ]
    assert [
        len(items)
        for _, items in grouped
    ] == [
        1,
        2,
    ]


def test_protocol_identity_is_part_of_cohort_identity() -> None:
    first = protocol()
    second = HistoricalOutcomeResearchProtocol(
        protocol_id="DESCRIPTIVE_OUTCOME_RESEARCH",
        version=2,
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
        claim_policy="DESCRIPTIVE_ONLY",
    )
    service = HistoricalOutcomeCohortService()

    first_key = service.build(
        result=result(),
        protocol=first,
    )
    second_key = service.build(
        result=result(),
        protocol=second,
    )

    assert first_key.identity_key != second_key.identity_key


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeCohortService()

    with pytest.raises(
        TypeError,
        match="result",
    ):
        service.build(
            result=object(),  # type: ignore[arg-type]
            protocol=protocol(),
        )

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.build(
            result=result(),
            protocol=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(
        TypeError,
        match="results",
    ):
        service.group(
            results=[],  # type: ignore[arg-type]
            protocol=protocol(),
        )
