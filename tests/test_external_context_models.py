"""Tests for provider-independent external-context evidence contracts."""

from datetime import datetime, timezone

import pytest

from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
    ExternalContextProvenance,
    ExternalContextQualityService,
    ExternalContextRecord,
)


def timestamp(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=timezone.utc)


def provenance(**overrides) -> ExternalContextProvenance:
    values = {
        "source": "official_release",
        "source_record_id": "release-42",
        "published_at": timestamp(10),
        "fetched_at": timestamp(10, 13),
        "source_url": "https://example.test/releases/42",
        "checksum_sha256": "a" * 64,
    }
    values.update(overrides)
    return ExternalContextProvenance(**values)


def record(**overrides) -> ExternalContextRecord:
    values = {
        "context_id": "context-42",
        "context_type": "macroeconomic",
        "title": "Policy rate unchanged",
        "summary": "The central bank kept its policy rate unchanged.",
        "subjects": ("EUR", "MONETARY_POLICY"),
        "uncertainty_level": "low",
        "uncertainty_reasons": (
            "The future policy path remains conditional.",
        ),
        "event_at": timestamp(10),
    }
    values.update(overrides)
    return ExternalContextRecord(**values)


def test_complete_fresh_context_is_ready_and_json_ready() -> None:
    source = provenance()
    quality = ExternalContextQualityService.assess(
        source,
        checked_at=timestamp(11),
        maximum_age_hours=48,
    )
    evidence = ExternalContextEvidence(
        record=record(),
        provenance=source,
        quality=quality,
    )

    payload = evidence.to_dict()

    assert quality.status == "READY"
    assert quality.is_ready is True
    assert payload["record"]["context_type"] == "MACROECONOMIC"
    assert payload["record"]["uncertainty_level"] == "LOW"
    assert payload["provenance"]["source"] == "OFFICIAL_RELEASE"
    assert payload["quality"]["age_hours"] == 24.0


def test_missing_optional_lineage_is_explicitly_partial() -> None:
    quality = ExternalContextQualityService.assess(
        provenance(source_url=None, checksum_sha256=None),
        checked_at=timestamp(11),
        maximum_age_hours=48,
    )

    assert quality.status == "PARTIAL"
    assert quality.missing_provenance_fields == (
        "source_url",
        "checksum_sha256",
    )
    assert quality.warnings == (
        ExternalContextQualityService.WARNING_PARTIAL,
    )


def test_stale_context_preserves_partial_lineage_warning() -> None:
    quality = ExternalContextQualityService.assess(
        provenance(source_url=None),
        checked_at=timestamp(13),
        maximum_age_hours=24,
    )

    assert quality.status == "STALE"
    assert quality.warnings == (
        ExternalContextQualityService.WARNING_STALE,
        ExternalContextQualityService.WARNING_PARTIAL,
    )


@pytest.mark.parametrize(
    "context_type",
    ["NEWS", "MACROECONOMIC", "GEOPOLITICAL", "EVENT"],
)
def test_supported_context_types_are_preserved(context_type: str) -> None:
    assert record(context_type=context_type).context_type == context_type


def test_non_none_uncertainty_requires_explanation() -> None:
    with pytest.raises(ValueError, match="uncertainty_reasons"):
        record(
            uncertainty_level="UNKNOWN",
            uncertainty_reasons=(),
        )


def test_none_uncertainty_accepts_no_reasons() -> None:
    value = record(
        uncertainty_level="NONE",
        uncertainty_reasons=(),
    )

    assert value.uncertainty_reasons == ()


def test_provenance_rejects_fetch_before_publication() -> None:
    with pytest.raises(ValueError, match="fetched_at"):
        provenance(fetched_at=timestamp(9))


def test_quality_rejects_check_before_publication() -> None:
    with pytest.raises(ValueError, match="checked_at"):
        ExternalContextQualityService.assess(
            provenance(),
            checked_at=timestamp(9),
            maximum_age_hours=24,
        )


@pytest.mark.parametrize("checksum", ["a" * 63, "g" * 64])
def test_provenance_rejects_invalid_checksum(checksum: str) -> None:
    with pytest.raises(ValueError, match="checksum_sha256"):
        provenance(checksum_sha256=checksum)


def test_record_rejects_naive_event_time() -> None:
    with pytest.raises(ValueError, match="event_at"):
        record(event_at=datetime(2026, 8, 10, 12))


def test_evidence_rejects_mismatched_component_types() -> None:
    source = provenance()
    quality = ExternalContextQualityService.assess(
        source,
        checked_at=timestamp(11),
        maximum_age_hours=48,
    )

    with pytest.raises(TypeError, match="record"):
        ExternalContextEvidence(
            record=None,
            provenance=source,
            quality=quality,
        )
