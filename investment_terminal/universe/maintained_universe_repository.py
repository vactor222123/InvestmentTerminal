"""Append-only repository boundary for maintained universe evidence."""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.universe.maintained_universe_models import (
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class MaintainedAssetUniverseRepository(ABC):
    """Persistence-agnostic append-only maintained-universe repository."""

    @abstractmethod
    def add(
        self,
        evidence: MaintainedAssetUniverseEvidence,
    ) -> MaintainedAssetUniverseEvidence:
        """Append evidence or reject its immutable identities."""

    @abstractmethod
    def get(
        self,
        universe_key: str,
    ) -> MaintainedAssetUniverseEvidence | None:
        """Return evidence by versioned canonical universe identity."""

    def require(
        self,
        universe_key: str,
    ) -> MaintainedAssetUniverseEvidence:
        evidence = self.get(universe_key)
        if evidence is None:
            raise KeyError(
                f"No maintained asset universe found for {universe_key}"
            )
        return evidence

    @abstractmethod
    def list_all(self) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        """Return all snapshots in deterministic chronological order."""

    @abstractmethod
    def list_between(
        self,
        observed_from: datetime,
        observed_until: datetime,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        """Return snapshots in the half-open observation interval."""

    @abstractmethod
    def list_for_universe(
        self,
        universe_id: str,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        """Return the version history for one canonical universe."""

    @abstractmethod
    def list_for_instrument(
        self,
        instrument_key: str,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        """Return snapshots containing one canonical instrument identity."""

    @abstractmethod
    def latest(
        self,
        universe_id: str,
    ) -> MaintainedAssetUniverseEvidence | None:
        """Return the latest snapshot for one universe, or None."""


class InMemoryMaintainedAssetUniverseRepository(
    MaintainedAssetUniverseRepository
):
    """Reference implementation of immutable universe append semantics."""

    def __init__(self) -> None:
        self._evidence: dict[str, MaintainedAssetUniverseEvidence] = {}
        self._source_identities: set[tuple[str, str | None]] = set()

    def add(
        self,
        evidence: MaintainedAssetUniverseEvidence,
    ) -> MaintainedAssetUniverseEvidence:
        if not isinstance(evidence, MaintainedAssetUniverseEvidence):
            raise TypeError(
                "evidence must be MaintainedAssetUniverseEvidence"
            )
        universe_key = evidence.universe.universe_key
        source_identity = (
            evidence.provenance.source,
            evidence.provenance.source_record_id,
        )
        if universe_key in self._evidence:
            raise ValueError(
                "Maintained asset universe identity already exists"
            )
        if source_identity in self._source_identities:
            raise ValueError(
                "Maintained asset universe source identity already exists"
            )
        self._evidence[universe_key] = evidence
        self._source_identities.add(source_identity)
        return evidence

    def get(
        self,
        universe_key: str,
    ) -> MaintainedAssetUniverseEvidence | None:
        normalized = normalize_required_text(
            universe_key,
            field_name="universe_key",
            uppercase=True,
        )
        return self._evidence.get(normalized)

    def list_all(self) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        return tuple(sorted(self._evidence.values(), key=_ordering_key))

    def list_between(
        self,
        observed_from: datetime,
        observed_until: datetime,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        start = validate_aware_datetime(
            observed_from,
            field_name="observed_from",
        )
        end = validate_aware_datetime(
            observed_until,
            field_name="observed_until",
        )
        if end <= start:
            raise ValueError(
                "observed_until must be later than observed_from"
            )
        return tuple(
            item
            for item in self.list_all()
            if start <= item.universe.as_of < end
        )

    def list_for_universe(
        self,
        universe_id: str,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        normalized = normalize_required_text(
            universe_id,
            field_name="universe_id",
            uppercase=True,
        )
        return tuple(
            item
            for item in self.list_all()
            if item.universe.universe_id == normalized
        )

    def list_for_instrument(
        self,
        instrument_key: str,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        normalized = normalize_required_text(
            instrument_key,
            field_name="instrument_key",
            uppercase=True,
        )
        return tuple(
            item
            for item in self.list_all()
            if item.universe.contains(normalized)
        )

    def latest(
        self,
        universe_id: str,
    ) -> MaintainedAssetUniverseEvidence | None:
        history = self.list_for_universe(universe_id)
        return history[-1] if history else None


def _ordering_key(
    evidence: MaintainedAssetUniverseEvidence,
) -> tuple[object, ...]:
    return (
        evidence.universe.as_of,
        evidence.universe.universe_id,
        evidence.universe.version,
        evidence.provenance.source,
        evidence.provenance.source_record_id or "",
    )
