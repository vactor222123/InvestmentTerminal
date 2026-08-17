"""Tests for deterministic external-context Review Package projection."""

from datetime import datetime, timezone

import pytest

from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
    ExternalContextProvenance,
    ExternalContextQualityService,
    ExternalContextRecord,
)
from investment_terminal.review.external_context_review_adapter import (
    ExternalContextReviewAdapter,
)


def evidence(
    context_id: str,
    day: int,
    *,
    source_url: str | None = "https://example.test/context",
) -> ExternalContextEvidence:
    published_at = datetime(2026, 8, day, tzinfo=timezone.utc)
    provenance = ExternalContextProvenance(
        source="official_release",
        source_record_id=f"record-{context_id}",
        published_at=published_at,
        fetched_at=published_at,
        source_url=source_url,
        checksum_sha256="a" * 64,
    )
    return ExternalContextEvidence(
        record=ExternalContextRecord(
            context_id=context_id,
            context_type="NEWS",
            title=f"Title {context_id}",
            summary=f"Summary {context_id}",
            subjects=("EUR",),
            uncertainty_level="NONE",
        ),
        provenance=provenance,
        quality=ExternalContextQualityService.assess(
            provenance,
            checked_at=published_at,
            maximum_age_hours=24,
        ),
    )


def test_adapter_orders_evidence_and_preserves_full_payload() -> None:
    result = ExternalContextReviewAdapter.adapt((
        evidence("later", 12),
        evidence("earlier", 11),
    ))

    assert result["status"] == "READY"
    assert result["item_count"] == 2
    assert result["quality_counts"] == {
        "READY": 2,
        "PARTIAL": 0,
        "STALE": 0,
    }
    assert [
        item["record"]["context_id"]
        for item in result["items"]
    ] == ["earlier", "later"]
    assert result["items"][0]["provenance"]["source"] == (
        "OFFICIAL_RELEASE"
    )


def test_adapter_exposes_partial_quality_and_warning() -> None:
    result = ExternalContextReviewAdapter.adapt((
        evidence("partial", 11, source_url=None),
    ))

    assert result["status"] == "PARTIAL"
    assert result["quality_counts"]["PARTIAL"] == 1
    assert result["warnings"] == [
        ExternalContextQualityService.WARNING_PARTIAL,
    ]


def test_adapter_represents_empty_evidence_explicitly() -> None:
    assert ExternalContextReviewAdapter.adapt(()) == {
        "status": "NO_EVIDENCE",
        "item_count": 0,
        "quality_counts": {
            "READY": 0,
            "PARTIAL": 0,
            "STALE": 0,
        },
        "warnings": [],
        "items": [],
    }


def test_adapter_rejects_invalid_input() -> None:
    with pytest.raises(TypeError, match="tuple"):
        ExternalContextReviewAdapter.adapt([])

    with pytest.raises(TypeError, match="ExternalContextEvidence"):
        ExternalContextReviewAdapter.adapt((object(),))
