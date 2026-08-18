"""Deterministic ETF discovery evidence assembly."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.market.etf_composition_models import (
    ETFCompositionEvidence,
)
from investment_terminal.market.etf_evidence_models import (
    ETFCharacteristicsEvidence,
)
from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.universe.maintained_universe_models import (
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.utils.validation import validate_aware_datetime


ETF_DISCOVERY_QUALITY_STATUSES = ("READY", "PARTIAL", "STALE")


@dataclass(frozen=True, slots=True)
class ETFDiscoveryCandidate:
    """One universe ETF with explicitly available discovery evidence."""

    instrument: InstrumentIdentity
    universe_quality_status: str
    characteristics: ETFCharacteristicsEvidence | None = None
    composition: ETFCompositionEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        if self.instrument.instrument_type != "ETF":
            raise ValueError("instrument must describe an ETF")
        if self.universe_quality_status not in ETF_DISCOVERY_QUALITY_STATUSES:
            raise ValueError(
                "universe_quality_status must be READY, PARTIAL, or STALE"
            )
        if self.characteristics is not None:
            if not isinstance(
                self.characteristics,
                ETFCharacteristicsEvidence,
            ):
                raise TypeError(
                    "characteristics must be ETFCharacteristicsEvidence or None"
                )
            if self.characteristics.characteristics.identity != self.instrument:
                raise ValueError(
                    "characteristics identity must match instrument"
                )
        if self.composition is not None:
            if not isinstance(self.composition, ETFCompositionEvidence):
                raise TypeError(
                    "composition must be ETFCompositionEvidence or None"
                )
            if self.composition.composition.identity != self.instrument:
                raise ValueError("composition identity must match instrument")

    @property
    def missing_evidence(self) -> tuple[str, ...]:
        result: list[str] = []
        if self.characteristics is None:
            result.append("CHARACTERISTICS")
        if self.composition is None:
            result.append("COMPOSITION")
        return tuple(result)

    @property
    def quality_status(self) -> str:
        statuses = [self.universe_quality_status]
        if self.characteristics is not None:
            statuses.append(self.characteristics.quality.status)
        if self.composition is not None:
            statuses.append(self.composition.quality.status)
        if "STALE" in statuses:
            return "STALE"
        if self.missing_evidence or "PARTIAL" in statuses:
            return "PARTIAL"
        return "READY"

    @property
    def is_ready(self) -> bool:
        return self.quality_status == "READY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "quality_status": self.quality_status,
            "is_ready": self.is_ready,
            "missing_evidence": list(self.missing_evidence),
            "characteristics": (
                self.characteristics.to_dict()
                if self.characteristics is not None
                else None
            ),
            "composition": (
                self.composition.to_dict()
                if self.composition is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ETFDiscoveryEvidence:
    """Deterministic ETF candidates projected from one universe snapshot."""

    universe: MaintainedAssetUniverseEvidence
    assessed_at: datetime
    candidates: tuple[ETFDiscoveryCandidate, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.universe, MaintainedAssetUniverseEvidence):
            raise TypeError(
                "universe must be MaintainedAssetUniverseEvidence"
            )
        validate_aware_datetime(self.assessed_at, field_name="assessed_at")
        if self.assessed_at < self.universe.universe.as_of:
            raise ValueError(
                "assessed_at must not be earlier than universe as_of"
            )
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a tuple")
        if any(
            not isinstance(item, ETFDiscoveryCandidate)
            for item in self.candidates
        ):
            raise TypeError(
                "candidates must contain ETFDiscoveryCandidate values"
            )
        ordered = tuple(
            sorted(
                self.candidates,
                key=lambda item: item.instrument.instrument_key,
            )
        )
        keys = tuple(item.instrument.instrument_key for item in ordered)
        if len(keys) != len(set(keys)):
            raise ValueError(
                "candidates must have unique instrument identities"
            )
        object.__setattr__(self, "candidates", ordered)

    @property
    def status_counts(self) -> dict[str, int]:
        counts = Counter(item.quality_status for item in self.candidates)
        return {
            status: counts[status]
            for status in ETF_DISCOVERY_QUALITY_STATUSES
        }

    @property
    def all_ready(self) -> bool:
        return bool(self.candidates) and all(
            item.is_ready for item in self.candidates
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe": self.universe.to_dict(),
            "assessed_at": self.assessed_at.isoformat(),
            "candidate_count": len(self.candidates),
            "status_counts": self.status_counts,
            "all_ready": self.all_ready,
            "candidates": [item.to_dict() for item in self.candidates],
        }


class ETFDiscoveryEvidenceBuilder:
    """Join existing ETF facts to ETF members without scoring them."""

    @classmethod
    def build(
        cls,
        universe: MaintainedAssetUniverseEvidence,
        *,
        assessed_at: datetime,
        characteristics: tuple[ETFCharacteristicsEvidence, ...] = (),
        compositions: tuple[ETFCompositionEvidence, ...] = (),
    ) -> ETFDiscoveryEvidence:
        if not isinstance(universe, MaintainedAssetUniverseEvidence):
            raise TypeError(
                "universe must be MaintainedAssetUniverseEvidence"
            )
        validate_aware_datetime(assessed_at, field_name="assessed_at")
        cls._validate_evidence_time(universe, assessed_at)
        characteristics_by_key = cls._index_characteristics(
            characteristics,
            assessed_at=assessed_at,
        )
        compositions_by_key = cls._index_compositions(
            compositions,
            assessed_at=assessed_at,
        )
        etf_members = tuple(
            member.instrument
            for member in universe.universe.members
            if member.instrument.instrument_type == "ETF"
        )
        member_keys = {
            instrument.instrument_key for instrument in etf_members
        }
        supplied_keys = set(characteristics_by_key) | set(compositions_by_key)
        if not supplied_keys.issubset(member_keys):
            raise ValueError(
                "ETF evidence contains an instrument outside the universe"
            )

        candidates = tuple(
            ETFDiscoveryCandidate(
                instrument=instrument,
                universe_quality_status=universe.quality.status,
                characteristics=characteristics_by_key.get(
                    instrument.instrument_key
                ),
                composition=compositions_by_key.get(
                    instrument.instrument_key
                ),
            )
            for instrument in etf_members
        )
        return ETFDiscoveryEvidence(
            universe=universe,
            assessed_at=assessed_at,
            candidates=candidates,
        )

    @staticmethod
    def _validate_evidence_time(
        universe: MaintainedAssetUniverseEvidence,
        assessed_at: datetime,
    ) -> None:
        if universe.quality.checked_at > assessed_at:
            raise ValueError(
                "universe quality cannot be checked after assessed_at"
            )

    @classmethod
    def _index_characteristics(
        cls,
        values: tuple[ETFCharacteristicsEvidence, ...],
        *,
        assessed_at: datetime,
    ) -> dict[str, ETFCharacteristicsEvidence]:
        cls._validate_tuple(
            values,
            field_name="characteristics",
            expected_type=ETFCharacteristicsEvidence,
        )
        result: dict[str, ETFCharacteristicsEvidence] = {}
        for item in values:
            cls._validate_item_time(item, assessed_at=assessed_at)
            key = item.characteristics.identity.instrument_key
            if key in result:
                raise ValueError(
                    "characteristics contains duplicate instrument identity"
                )
            result[key] = item
        return result

    @classmethod
    def _index_compositions(
        cls,
        values: tuple[ETFCompositionEvidence, ...],
        *,
        assessed_at: datetime,
    ) -> dict[str, ETFCompositionEvidence]:
        cls._validate_tuple(
            values,
            field_name="compositions",
            expected_type=ETFCompositionEvidence,
        )
        result: dict[str, ETFCompositionEvidence] = {}
        for item in values:
            cls._validate_item_time(item, assessed_at=assessed_at)
            key = item.composition.identity.instrument_key
            if key in result:
                raise ValueError(
                    "compositions contains duplicate instrument identity"
                )
            result[key] = item
        return result

    @staticmethod
    def _validate_item_time(
        item: ETFCharacteristicsEvidence | ETFCompositionEvidence,
        *,
        assessed_at: datetime,
    ) -> None:
        if (
            item.provenance.observed_at > assessed_at
            or item.quality.checked_at > assessed_at
        ):
            raise ValueError("ETF evidence cannot be later than assessed_at")

    @staticmethod
    def _validate_tuple(
        value: object,
        *,
        field_name: str,
        expected_type: type,
    ) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f"{field_name} must be a tuple")
        if any(not isinstance(item, expected_type) for item in value):
            raise TypeError(
                f"{field_name} must contain only "
                f"{expected_type.__name__} values"
            )
