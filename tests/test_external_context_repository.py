"""Tests for append-only external-context repository semantics."""

from datetime import datetime, timezone

import pytest

from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
    ExternalContextProvenance,
    ExternalContextQualityService,
    ExternalContextRecord,
)
from investment_terminal.context.external_context_repository import (
    ExternalContextRepository,
    InMemoryExternalContextRepository,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def evidence(identity: str, day: int, subjects=("EUR",)) -> ExternalContextEvidence:
    provenance = ExternalContextProvenance(
        source="test", source_record_id=identity,
        published_at=timestamp(day), fetched_at=timestamp(day),
        source_url=f"https://example.test/{identity}", checksum_sha256="a" * 64,
    )
    return ExternalContextEvidence(
        record=ExternalContextRecord(
            context_id=f"context-{identity}", context_type="NEWS",
            title=identity, summary=f"Summary {identity}", subjects=subjects,
            uncertainty_level="NONE",
        ),
        provenance=provenance,
        quality=ExternalContextQualityService.assess(
            provenance, checked_at=timestamp(day), maximum_age_hours=24,
        ),
    )


def repository() -> InMemoryExternalContextRepository:
    value = InMemoryExternalContextRepository()
    assert isinstance(value, ExternalContextRepository)
    return value


def test_add_get_require_and_deterministic_order() -> None:
    repo = repository()
    later = evidence("later", 12)
    earlier = evidence("earlier", 11)
    repo.add(later)
    repo.add(earlier)

    assert repo.get(" context-earlier ") is earlier
    assert repo.require("context-later") is later
    assert repo.list_all() == (earlier, later)


def test_missing_and_duplicate_identities_fail_closed() -> None:
    repo = repository()
    original = evidence("one", 11)
    repo.add(original)
    with pytest.raises(KeyError, match="No external context"):
        repo.require("missing")
    with pytest.raises(ValueError, match="context identity"):
        repo.add(original)

    duplicate_source = evidence("one", 12)
    duplicate_source = ExternalContextEvidence(
        record=ExternalContextRecord(
            context_id="different", context_type="NEWS", title="Different",
            summary="Different", subjects=("EUR",), uncertainty_level="NONE",
        ),
        provenance=duplicate_source.provenance,
        quality=duplicate_source.quality,
    )
    with pytest.raises(ValueError, match="source identity"):
        repo.add(duplicate_source)


def test_half_open_time_and_subject_queries() -> None:
    repo = repository()
    first = evidence("one", 10, ("EUR", "ECB"))
    second = evidence("two", 11, ("USD",))
    third = evidence("three", 12, ("EUR",))
    for item in (third, first, second):
        repo.add(item)

    assert repo.list_between(timestamp(10), timestamp(12)) == (first, second)
    assert repo.list_by_subject(" eur ") == (first, third)
    with pytest.raises(ValueError, match="later than"):
        repo.list_between(timestamp(12), timestamp(10))


def test_add_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="ExternalContextEvidence"):
        repository().add(object())
