"""
Contract tests for optional archive-gap provenance in research CLI output.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.cli.outcome_research import _print_human


NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def base_cohort() -> dict:
    return {
        "cohort": {"identity_key": "cohort-1"},
        "population": {
            "selection_basis": "ARCHIVED_OBSERVATIONS",
            "prefiltered": True,
            "warnings": [],
        },
        "coverage": {
            "eligible_count": 0,
            "candidate_count": 1,
            "coverage_fraction": 0.0,
            "complete_count": 0,
            "partial_count": 1,
            "unavailable_count": 0,
            "not_mature_count": 0,
        },
        "sample_assessment": {
            "status": "INSUFFICIENT",
            "eligible_sample_size": 0,
            "minimum_required_sample_size": 1,
            "shortfall": 1,
        },
        "descriptive_summary": None,
        "uncertainty": None,
        "claim_assessment": {
            "claim_policy": "DESCRIPTIVE_ONLY",
            "sample_status": "INSUFFICIENT",
            "warning": "insufficient",
        },
    }


def base_report(cohort: dict) -> dict:
    return {
        "recommendation_key": "WORLD",
        "protocol": {
            "identity_key": "DESCRIPTIVE_OUTCOME_RESEARCH@1",
        },
        "methodology": {
            "identity_key": "ELAPSED_DAYS_EXACT_CLOSE@1",
        },
        "window": {
            "kind": "ELAPSED_DAYS",
            "value": 5,
        },
        "as_of": NOW.isoformat(),
        "resolution": "D",
        "candidate_count": 1,
        "produced_observation_count": 1,
        "cohort_count": 1,
        "cohorts": [cohort],
    }


def provenance(
    *,
    gap: dict | None,
) -> dict:
    return {
        "population_frame": {
            "source_observation_count": 1,
            "selected_candidate_count": 1,
            "excluded_by_selection_count": 0,
            "selection_fraction": 1.0,
        },
        "selection_accounting": {
            "source_observation_count": 1,
            "selected_candidate_count": 1,
            "excluded_observation_count": 0,
            "reason_counts": [],
            "total_reason_failures": 0,
            "reason_counts_are_exclusive": False,
        },
        "population_completeness": {
            "status": "COVERED",
            "source_observation_count": 1,
            "observed_origin_start": NOW.isoformat(),
            "observed_origin_end": NOW.isoformat(),
            "requested_origin_start": NOW.isoformat(),
            "requested_origin_end": NOW.isoformat(),
            "covers_requested_start": True,
            "covers_requested_end": True,
            "internal_continuity_status": (
                "NOT_ASSESSED"
                if gap is None
                else gap["status"]
            ),
            "warning": "continuity warning",
        },
        "source_import_quality": {
            "status": "COMPLETE",
            "source_observation_count": 1,
            "unique_snapshot_count": 1,
            "imported_snapshot_count": 1,
            "non_imported_snapshot_count": 0,
            "missing_state_snapshot_count": 0,
            "imported_fraction": 1.0,
            "status_counts": {"IMPORTED": 1},
            "warning": None,
        },
        "archive_gap_assessment": gap,
        "available_components": [
            "SOURCE_IMPORT_QUALITY",
            "POPULATION_COMPLETENESS",
            "POPULATION_FRAME",
            "SELECTION_ACCOUNTING",
        ],
        "missing_components": [],
        "available_optional_components": (
            []
            if gap is None
            else ["ARCHIVE_GAP_ASSESSMENT"]
        ),
        "complete_component_set": True,
    }


def gap(status: str) -> dict:
    if status == "COMPLETE":
        return {
            "status": "COMPLETE",
            "expected_count": 3,
            "observed_expected_count": 3,
            "missing_count": 0,
            "unexpected_observed_count": 0,
            "expected_coverage_fraction": 1.0,
            "missing_timestamps": [],
            "unexpected_observed_timestamps": [],
        }
    return {
        "status": "GAPS",
        "expected_count": 3,
        "observed_expected_count": 2,
        "missing_count": 1,
        "unexpected_observed_count": 0,
        "expected_coverage_fraction": 2 / 3,
        "missing_timestamps": [
            "2026-08-02T12:00:00+00:00",
        ],
        "unexpected_observed_timestamps": [],
    }


def test_human_output_preserves_4_of_4_core_without_optional_gap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cohort = base_cohort()
    cohort["provenance"] = provenance(
        gap=None,
    )

    _print_human(
        base_report(cohort)
    )
    output = capsys.readouterr().out

    assert "Provenance   : 4/4 components; complete=True" in output
    assert "Completeness : COVERED / internal=NOT_ASSESSED" in output
    assert "Archive gaps :" not in output


def test_human_output_adds_optional_gap_without_changing_core_denominator(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cohort = base_cohort()
    cohort["provenance"] = provenance(
        gap=gap("GAPS"),
    )

    _print_human(
        base_report(cohort)
    )
    output = capsys.readouterr().out

    assert "Provenance   : 4/4 components; complete=True" in output
    assert "Completeness : COVERED / internal=GAPS" in output
    assert "Archive gaps : GAPS / missing=1 / unexpected=0" in output


def test_human_output_renders_complete_optional_gap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cohort = base_cohort()
    cohort["provenance"] = provenance(
        gap=gap("COMPLETE"),
    )

    _print_human(
        base_report(cohort)
    )
    output = capsys.readouterr().out

    assert "Provenance   : 4/4 components; complete=True" in output
    assert "Completeness : COVERED / internal=COMPLETE" in output
    assert "Archive gaps : COMPLETE / missing=0 / unexpected=0" in output


def test_json_contract_keeps_optional_gap_inside_provenance() -> None:
    payload = provenance(
        gap=gap("GAPS"),
    )

    assert payload["complete_component_set"] is True
    assert payload["available_components"] == [
        "SOURCE_IMPORT_QUALITY",
        "POPULATION_COMPLETENESS",
        "POPULATION_FRAME",
        "SELECTION_ACCOUNTING",
    ]
    assert payload["available_optional_components"] == [
        "ARCHIVE_GAP_ASSESSMENT",
    ]
    assert payload["archive_gap_assessment"]["status"] == "GAPS"
    assert payload["archive_gap_assessment"]["missing_count"] == 1


def test_legacy_fixture_with_top_level_gap_keeps_4_component_core(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cohort = base_cohort()
    cohort.update(
        {
            "population_frame": {
                "source_observation_count": 1,
                "selected_candidate_count": 1,
                "excluded_by_selection_count": 0,
                "selection_fraction": 1.0,
            },
            "selection_accounting": None,
            "population_completeness": {
                "status": "COVERED",
                "source_observation_count": 1,
                "observed_origin_start": NOW.isoformat(),
                "observed_origin_end": NOW.isoformat(),
                "requested_origin_start": NOW.isoformat(),
                "requested_origin_end": NOW.isoformat(),
                "covers_requested_start": True,
                "covers_requested_end": True,
                "internal_continuity_status": "GAPS",
                "warning": "continuity warning",
            },
            "source_import_quality": None,
            "archive_gap_assessment": gap("GAPS"),
        }
    )

    _print_human(
        base_report(cohort)
    )
    output = capsys.readouterr().out

    assert "Provenance   : 2/4 components; complete=False" in output
    assert "Archive gaps : GAPS / missing=1 / unexpected=0" in output
