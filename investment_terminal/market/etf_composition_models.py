"""Provider-independent ETF holdings and exposure composition contracts."""

from dataclasses import dataclass
from typing import Any

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityAssessment,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_finite_number,
)


WEIGHT_TOLERANCE = 0.0001


@dataclass(frozen=True, slots=True)
class ETFConstituentHolding:
    """One reported constituent and its decimal portfolio weight."""

    name: str
    weight: float
    identity: InstrumentIdentity | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            normalize_required_text(self.name, field_name="name"),
        )
        object.__setattr__(
            self,
            "weight",
            _validate_weight(self.weight, field_name="weight"),
        )
        if self.identity is not None and not isinstance(
            self.identity, InstrumentIdentity
        ):
            raise TypeError("identity must be an InstrumentIdentity or None")

    @property
    def holding_key(self) -> str:
        if self.identity is not None:
            return self.identity.instrument_key
        return self.name.upper()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weight": self.weight,
            "identity": (
                self.identity.to_dict() if self.identity is not None else None
            ),
            "holding_key": self.holding_key,
        }


@dataclass(frozen=True, slots=True)
class ETFExposure:
    """One reported category inside an exposure dimension."""

    dimension: str
    label: str
    weight: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dimension",
            normalize_required_text(
                self.dimension,
                field_name="dimension",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "label",
            normalize_required_text(self.label, field_name="label"),
        )
        object.__setattr__(
            self,
            "weight",
            _validate_weight(self.weight, field_name="weight"),
        )

    @property
    def exposure_key(self) -> str:
        return f"{self.dimension}:{self.label.upper()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "label": self.label,
            "weight": self.weight,
            "exposure_key": self.exposure_key,
        }


@dataclass(frozen=True, slots=True)
class ETFComposition:
    """Reported ETF constituents and categorical exposure breakdowns."""

    identity: InstrumentIdentity
    holdings: tuple[ETFConstituentHolding, ...]
    exposures: tuple[ETFExposure, ...]
    holdings_scope: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, InstrumentIdentity):
            raise TypeError("identity must be an InstrumentIdentity")
        if self.identity.instrument_type != "ETF":
            raise ValueError("identity must describe an ETF")

        _validate_tuple_members(
            self.holdings,
            field_name="holdings",
            expected_type=ETFConstituentHolding,
        )
        _validate_tuple_members(
            self.exposures,
            field_name="exposures",
            expected_type=ETFExposure,
        )
        object.__setattr__(
            self,
            "holdings_scope",
            normalize_optional_text(
                self.holdings_scope,
                field_name="holdings_scope",
            ),
        )

        holding_keys = tuple(item.holding_key for item in self.holdings)
        if len(holding_keys) != len(set(holding_keys)):
            raise ValueError("holdings must contain unique holding keys")

        exposure_keys = tuple(item.exposure_key for item in self.exposures)
        if len(exposure_keys) != len(set(exposure_keys)):
            raise ValueError("exposures must contain unique dimension/label pairs")

        _validate_weight_total(
            sum(item.weight for item in self.holdings),
            field_name="holdings",
        )
        for dimension in self.exposure_dimensions:
            _validate_weight_total(
                sum(
                    item.weight
                    for item in self.exposures
                    if item.dimension == dimension
                ),
                field_name=f"{dimension} exposures",
            )

    @property
    def holdings_coverage(self) -> float:
        return round(sum(item.weight for item in self.holdings), 8)

    @property
    def exposure_dimensions(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.dimension for item in self.exposures))

    @property
    def exposure_coverage(self) -> dict[str, float]:
        return {
            dimension: round(
                sum(
                    item.weight
                    for item in self.exposures
                    if item.dimension == dimension
                ),
                8,
            )
            for dimension in self.exposure_dimensions
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "holdings_scope": self.holdings_scope,
            "holdings": [item.to_dict() for item in self.holdings],
            "holdings_coverage": self.holdings_coverage,
            "exposures": [item.to_dict() for item in self.exposures],
            "exposure_coverage": self.exposure_coverage,
        }


@dataclass(frozen=True, slots=True)
class ETFCompositionEvidence:
    """ETF composition with source lineage and quality state."""

    composition: ETFComposition
    provenance: MarketMetadataProvenance
    quality: MarketMetadataQualityAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.composition, ETFComposition):
            raise TypeError("composition must be ETFComposition")
        if not isinstance(self.provenance, MarketMetadataProvenance):
            raise TypeError("provenance must be MarketMetadataProvenance")
        if not isinstance(self.quality, MarketMetadataQualityAssessment):
            raise TypeError("quality must be MarketMetadataQualityAssessment")
        if self.quality.checked_at < self.provenance.observed_at:
            raise ValueError(
                "quality.checked_at must not be earlier than provenance.observed_at"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "composition": self.composition.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
        }


def _validate_weight(value: object, *, field_name: str) -> float:
    normalized = validate_finite_number(value, field_name=field_name)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return normalized


def _validate_weight_total(value: float, *, field_name: str) -> None:
    if value > 1.0 + WEIGHT_TOLERANCE:
        raise ValueError(f"{field_name} weights must not exceed 1.0")


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
