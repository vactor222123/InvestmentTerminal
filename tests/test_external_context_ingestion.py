"""Tests for provider-neutral external-context ingestion."""

from datetime import datetime, timezone

import pytest

from investment_terminal.context.external_context_ingestion import (
    ExternalContextIngestionResult,
    ExternalContextIngestionService,
    ExternalContextQuery,
    ExternalContextSourceItem,
)
from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
    ExternalContextProvenance,
    ExternalContextQualityService,
    ExternalContextRecord,
)


def timestamp(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=timezone.utc)


def query(**overrides) -> ExternalContextQuery:
    values = {
        "context_types": ("news", "macroeconomic"),
        "subjects": ("EUR",),
        "published_from": timestamp(10),
        "published_until": timestamp(13),
        "maximum_age_hours": 72,
        "limit": 10,
    }
    values.update(overrides)
    return ExternalContextQuery(**values)


def source_item(
    identity: str,
    *,
    published_at: datetime,
    context_type: str = "NEWS",
    subjects: tuple[str, ...] = ("EUR",),
    source_url: str | None = "https://example.test/item",
) -> ExternalContextSourceItem:
    return ExternalContextSourceItem(
        record=ExternalContextRecord(
            context_id=f"context-{identity}",
            context_type=context_type,
            title=f"Title {identity}",
            summary=f"Summary {identity}",
            subjects=subjects,
            uncertainty_level="NONE",
        ),
        provenance=ExternalContextProvenance(
            source="test_provider",
            source_record_id=identity,
            published_at=published_at,
            fetched_at=published_at,
            source_url=source_url,
            checksum_sha256="a" * 64,
        ),
    )


class StubProvider:
    def __init__(
        self,
        items: tuple[ExternalContextSourceItem, ...],
    ) -> None:
        self.items = items
        self.queries: list[ExternalContextQuery] = []

    def fetch(
        self,
        value: ExternalContextQuery,
    ) -> tuple[ExternalContextSourceItem, ...]:
        self.queries.append(value)
        return self.items


def test_ingestion_assesses_quality_and_sorts_deterministically() -> None:
    later = source_item("later", published_at=timestamp(12))
    earlier = source_item("earlier", published_at=timestamp(11))
    provider = StubProvider((later, earlier))
    request = query()

    result = ExternalContextIngestionService(
        provider,
        clock=lambda: timestamp(13),
    ).ingest(request)

    assert provider.queries == [request]
    assert tuple(
        item.record.context_id for item in result.evidence
    ) == ("context-earlier", "context-later")
    assert result.status_counts == {
        "READY": 2,
        "PARTIAL": 0,
        "STALE": 0,
    }
    assert result.all_ready is True
    assert result.to_dict()["evidence_count"] == 2


def test_ingestion_preserves_partial_and_stale_states() -> None:
    partial = source_item(
        "partial",
        published_at=timestamp(12),
        source_url=None,
    )
    stale = source_item("stale", published_at=timestamp(10))
    result = ExternalContextIngestionService(
        StubProvider((partial, stale)),
        clock=lambda: timestamp(13),
    ).ingest(query(maximum_age_hours=24))

    assert result.status_counts == {
        "READY": 0,
        "PARTIAL": 1,
        "STALE": 1,
    }
    assert result.all_ready is False


def test_empty_provider_result_is_explicitly_not_all_ready() -> None:
    result = ExternalContextIngestionService(
        StubProvider(()),
        clock=lambda: timestamp(13),
    ).ingest(query())

    assert result.evidence == ()
    assert result.all_ready is False


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (
            (source_item("type", published_at=timestamp(11), context_type="EVENT"),),
            "context_type",
        ),
        (
            (source_item("early", published_at=timestamp(9)),),
            "query window",
        ),
        (
            (source_item("late", published_at=timestamp(13)),),
            "query window",
        ),
        (
            (source_item("subject", published_at=timestamp(11), subjects=("USD",)),),
            "subjects",
        ),
    ],
)
def test_ingestion_rejects_provider_items_outside_query(
    items: tuple[ExternalContextSourceItem, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ExternalContextIngestionService(
            StubProvider(items),
            clock=lambda: timestamp(13),
        ).ingest(query())


def test_ingestion_rejects_future_publication() -> None:
    with pytest.raises(ValueError, match="future publication"):
        ExternalContextIngestionService(
            StubProvider((source_item("future", published_at=timestamp(12)),)),
            clock=lambda: timestamp(11),
        ).ingest(query())


def test_ingestion_rejects_duplicate_context_identity() -> None:
    first = source_item("same", published_at=timestamp(11))
    second = ExternalContextSourceItem(
        record=first.record,
        provenance=ExternalContextProvenance(
            source="other_provider",
            source_record_id="other",
            published_at=timestamp(11),
            fetched_at=timestamp(11),
            source_url="https://example.test/other",
            checksum_sha256="b" * 64,
        ),
    )

    with pytest.raises(ValueError, match="duplicate context_id"):
        ExternalContextIngestionService(
            StubProvider((first, second)),
            clock=lambda: timestamp(13),
        ).ingest(query())


def test_ingestion_rejects_duplicate_source_identity() -> None:
    first = source_item("same", published_at=timestamp(11))
    second = ExternalContextSourceItem(
        record=ExternalContextRecord(
            context_id="different-context",
            context_type="NEWS",
            title="Different",
            summary="Different record",
            subjects=("EUR",),
            uncertainty_level="NONE",
        ),
        provenance=first.provenance,
    )

    with pytest.raises(ValueError, match="duplicate source identity"):
        ExternalContextIngestionService(
            StubProvider((first, second)),
            clock=lambda: timestamp(13),
        ).ingest(query())


def test_ingestion_rejects_result_above_explicit_limit() -> None:
    items = (
        source_item("one", published_at=timestamp(11)),
        source_item("two", published_at=timestamp(12)),
    )

    with pytest.raises(ValueError, match="query limit"):
        ExternalContextIngestionService(
            StubProvider(items),
            clock=lambda: timestamp(13),
        ).ingest(query(limit=1))


def test_query_normalizes_types_and_rejects_duplicate_values() -> None:
    value = query(context_types=(" news ",), subjects=(" eur ",))

    assert value.context_types == ("NEWS",)
    assert value.subjects == ("EUR",)

    with pytest.raises(ValueError, match="unique"):
        query(context_types=("news", "NEWS"))

    with pytest.raises(ValueError, match="unique"):
        query(subjects=("eur", "EUR"))


@pytest.mark.parametrize("maximum_age", [0, -1, float("inf"), float("nan")])
def test_query_rejects_invalid_freshness(maximum_age: float) -> None:
    with pytest.raises(ValueError, match="maximum_age_hours"):
        query(maximum_age_hours=maximum_age)


def test_ingestion_rejects_non_tuple_provider_result() -> None:
    provider = StubProvider(())
    provider.fetch = lambda value: []

    with pytest.raises(TypeError, match="provider result"):
        ExternalContextIngestionService(
            provider,
            clock=lambda: timestamp(13),
        ).ingest(query())


def test_result_rejects_inconsistent_quality_timestamp() -> None:
    item = source_item("one", published_at=timestamp(11))
    quality = ExternalContextQualityService.assess(
        item.provenance,
        checked_at=timestamp(12),
        maximum_age_hours=72,
    )

    with pytest.raises(ValueError, match="timestamps"):
        ExternalContextIngestionResult(
            query=query(),
            checked_at=timestamp(13),
            evidence=(ExternalContextEvidence(
                record=item.record,
                provenance=item.provenance,
                quality=quality,
            ),),
        )
