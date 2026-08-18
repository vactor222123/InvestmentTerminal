"""Provider-neutral maintained asset-universe ingestion boundary."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Integral
from typing import Any, Protocol

from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityService,
)
from investment_terminal.universe.maintained_universe_models import (
    MaintainedAssetUniverse,
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class MaintainedAssetUniverseQuery:
    """Provider-independent request for bounded universe snapshots."""

    universe_ids: tuple[str, ...]
    observed_from: datetime
    observed_until: datetime
    maximum_age_days: float
    limit: int

    def __post_init__(self) -> None:
        if not isinstance(self.universe_ids, tuple):
            raise TypeError("universe_ids must be a tuple")
        if not self.universe_ids:
            raise ValueError("universe_ids must not be empty")
        universe_ids = tuple(
            normalize_required_text(
                value,
                field_name="universe_ids item",
                uppercase=True,
            )
            for value in self.universe_ids
        )
        if len(universe_ids) != len(set(universe_ids)):
            raise ValueError("universe_ids must contain unique values")
        validate_aware_datetime(
            self.observed_from,
            field_name="observed_from",
        )
        validate_aware_datetime(
            self.observed_until,
            field_name="observed_until",
        )
        if self.observed_until <= self.observed_from:
            raise ValueError(
                "observed_until must be later than observed_from"
            )
        maximum_age = validate_finite_number(
            self.maximum_age_days,
            field_name="maximum_age_days",
        )
        if maximum_age <= 0:
            raise ValueError("maximum_age_days must be a positive number")
        if (
            isinstance(self.limit, bool)
            or not isinstance(self.limit, Integral)
            or self.limit <= 0
        ):
            raise ValueError("limit must be a positive integer")

        object.__setattr__(self, "universe_ids", universe_ids)
        object.__setattr__(self, "maximum_age_days", maximum_age)
        object.__setattr__(self, "limit", int(self.limit))

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe_ids": list(self.universe_ids),
            "observed_from": self.observed_from.isoformat(),
            "observed_until": self.observed_until.isoformat(),
            "maximum_age_days": self.maximum_age_days,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class MaintainedAssetUniverseSourceItem:
    """Normalized provider output before deterministic quality assessment."""

    universe: MaintainedAssetUniverse
    provenance: MarketMetadataProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.universe, MaintainedAssetUniverse):
            raise TypeError("universe must be a MaintainedAssetUniverse")
        if not isinstance(self.provenance, MarketMetadataProvenance):
            raise TypeError(
                "provenance must be a MarketMetadataProvenance"
            )
        if self.provenance.observed_at != self.universe.as_of:
            raise ValueError(
                "provenance.observed_at must equal universe.as_of"
            )


class MaintainedAssetUniverseProvider(Protocol):
    """Contract implemented by maintained-universe provider adapters."""

    def fetch(
        self,
        query: MaintainedAssetUniverseQuery,
    ) -> tuple[MaintainedAssetUniverseSourceItem, ...]:
        """Return normalized source items for one bounded query."""
        ...


@dataclass(frozen=True, slots=True)
class MaintainedAssetUniverseIngestionResult:
    """Deterministic evidence returned by one provider ingestion call."""

    query: MaintainedAssetUniverseQuery
    checked_at: datetime
    evidence: tuple[MaintainedAssetUniverseEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.query, MaintainedAssetUniverseQuery):
            raise TypeError(
                "query must be a MaintainedAssetUniverseQuery"
            )
        validate_aware_datetime(self.checked_at, field_name="checked_at")
        _validate_tuple_members(
            self.evidence,
            field_name="evidence",
            expected_type=MaintainedAssetUniverseEvidence,
        )
        if any(
            item.quality.checked_at != self.checked_at
            for item in self.evidence
        ):
            raise ValueError(
                "evidence quality timestamps must match checked_at"
            )

    @property
    def status_counts(self) -> dict[str, int]:
        counts = Counter(item.quality.status for item in self.evidence)
        return {
            status: counts[status]
            for status in ("READY", "PARTIAL", "STALE")
        }

    @property
    def all_ready(self) -> bool:
        return bool(self.evidence) and all(
            item.quality.is_ready for item in self.evidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "checked_at": self.checked_at.isoformat(),
            "evidence_count": len(self.evidence),
            "status_counts": self.status_counts,
            "all_ready": self.all_ready,
            "evidence": [item.to_dict() for item in self.evidence],
        }


class MaintainedAssetUniverseIngestionService:
    """Acquire normalized universes and enforce the requested scope."""

    def __init__(
        self,
        provider: MaintainedAssetUniverseProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if provider is None or not callable(getattr(provider, "fetch", None)):
            raise TypeError("provider must implement fetch(query)")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._provider = provider
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def ingest(
        self,
        query: MaintainedAssetUniverseQuery,
    ) -> MaintainedAssetUniverseIngestionResult:
        if not isinstance(query, MaintainedAssetUniverseQuery):
            raise TypeError(
                "query must be a MaintainedAssetUniverseQuery"
            )
        checked_at = self._clock()
        validate_aware_datetime(checked_at, field_name="clock result")

        source_items = self._provider.fetch(query)
        _validate_tuple_members(
            source_items,
            field_name="provider result",
            expected_type=MaintainedAssetUniverseSourceItem,
        )
        if len(source_items) > query.limit:
            raise ValueError("provider result exceeds query limit")

        seen_universe_keys: set[str] = set()
        seen_source_ids: set[tuple[str, str | None]] = set()
        evidence: list[MaintainedAssetUniverseEvidence] = []

        for item in source_items:
            self._validate_scope(item, query, checked_at=checked_at)
            universe_key = item.universe.universe_key
            source_id = (
                item.provenance.source,
                item.provenance.source_record_id,
            )
            if universe_key in seen_universe_keys:
                raise ValueError(
                    "provider result contains duplicate universe identity"
                )
            if source_id in seen_source_ids:
                raise ValueError(
                    "provider result contains duplicate source identity"
                )
            seen_universe_keys.add(universe_key)
            seen_source_ids.add(source_id)

            quality = MarketMetadataQualityService.assess(
                item.provenance,
                checked_at=checked_at,
                maximum_age_days=query.maximum_age_days,
            )
            evidence.append(MaintainedAssetUniverseEvidence(
                universe=item.universe,
                provenance=item.provenance,
                quality=quality,
            ))

        evidence.sort(key=lambda item: (
            item.universe.as_of,
            item.universe.universe_id,
            item.universe.version,
            item.provenance.source,
            item.provenance.source_record_id or "",
        ))
        return MaintainedAssetUniverseIngestionResult(
            query=query,
            checked_at=checked_at,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _validate_scope(
        item: MaintainedAssetUniverseSourceItem,
        query: MaintainedAssetUniverseQuery,
        *,
        checked_at: datetime,
    ) -> None:
        if item.universe.universe_id not in query.universe_ids:
            raise ValueError("provider returned universe_id outside query")
        if not (
            query.observed_from
            <= item.provenance.observed_at
            < query.observed_until
        ):
            raise ValueError(
                "provider returned observation outside query window"
            )
        if item.provenance.observed_at > checked_at:
            raise ValueError("provider returned future observation")


def _validate_tuple_members(
    value: object,
    *,
    field_name: str,
    expected_type: type,
) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if any(not isinstance(item, expected_type) for item in value):
        raise TypeError(
            f"{field_name} must contain only {expected_type.__name__} objects"
        )
