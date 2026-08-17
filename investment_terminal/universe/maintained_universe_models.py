"""Provider-independent maintained asset-universe contracts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityAssessment,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class AssetUniverseMember:
    """One instrument included in a maintained universe snapshot."""

    instrument: InstrumentIdentity
    included_at: datetime
    inclusion_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        validate_aware_datetime(self.included_at, field_name="included_at")
        object.__setattr__(
            self,
            "inclusion_reason",
            normalize_optional_text(
                self.inclusion_reason, field_name="inclusion_reason"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "included_at": self.included_at.isoformat(),
            "inclusion_reason": self.inclusion_reason,
        }


@dataclass(frozen=True, slots=True)
class MaintainedAssetUniverse:
    """Immutable versioned snapshot of an investable asset universe."""

    universe_id: str
    version: int
    name: str
    as_of: datetime
    members: tuple[AssetUniverseMember, ...]
    description: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be at least 1")
        validate_aware_datetime(self.as_of, field_name="as_of")
        if not isinstance(self.members, tuple):
            raise TypeError("members must be a tuple")
        if not self.members:
            raise ValueError("members must not be empty")
        if any(not isinstance(item, AssetUniverseMember) for item in self.members):
            raise TypeError("members must contain AssetUniverseMember values")
        if any(item.included_at > self.as_of for item in self.members):
            raise ValueError("members cannot be included after as_of")

        ordered_members = tuple(
            sorted(self.members, key=lambda item: item.instrument.instrument_key)
        )
        keys = tuple(item.instrument.instrument_key for item in ordered_members)
        if len(keys) != len(set(keys)):
            raise ValueError("members must have unique instrument identities")

        object.__setattr__(
            self,
            "universe_id",
            normalize_required_text(
                self.universe_id, field_name="universe_id", uppercase=True
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text(self.name, field_name="name"),
        )
        object.__setattr__(
            self,
            "description",
            normalize_optional_text(self.description, field_name="description"),
        )
        object.__setattr__(self, "members", ordered_members)

    @property
    def universe_key(self) -> str:
        return f"{self.universe_id}@{self.version}"

    @property
    def size(self) -> int:
        return len(self.members)

    def contains(self, instrument_key: str) -> bool:
        normalized_key = normalize_required_text(
            instrument_key, field_name="instrument_key", uppercase=True
        )
        return any(
            item.instrument.instrument_key == normalized_key
            for item in self.members
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe_id": self.universe_id,
            "version": self.version,
            "universe_key": self.universe_key,
            "name": self.name,
            "description": self.description,
            "as_of": self.as_of.isoformat(),
            "size": self.size,
            "members": [item.to_dict() for item in self.members],
        }


@dataclass(frozen=True, slots=True)
class MaintainedAssetUniverseEvidence:
    """Maintained universe snapshot with lineage and quality evidence."""

    universe: MaintainedAssetUniverse
    provenance: MarketMetadataProvenance
    quality: MarketMetadataQualityAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.universe, MaintainedAssetUniverse):
            raise TypeError("universe must be a MaintainedAssetUniverse")
        if not isinstance(self.provenance, MarketMetadataProvenance):
            raise TypeError("provenance must be a MarketMetadataProvenance")
        if not isinstance(self.quality, MarketMetadataQualityAssessment):
            raise TypeError(
                "quality must be a MarketMetadataQualityAssessment"
            )
        if self.provenance.observed_at != self.universe.as_of:
            raise ValueError("provenance.observed_at must equal universe.as_of")
        if self.quality.checked_at < self.universe.as_of:
            raise ValueError(
                "quality.checked_at must not be earlier than universe.as_of"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe": self.universe.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
        }
