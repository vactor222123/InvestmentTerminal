"""Provider-independent ETF characteristics evidence contracts."""

from dataclasses import dataclass
from numbers import Integral
from typing import Any

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityAssessment,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class ETFCharacteristics:
    """Normalized ETF facts; unavailable source values remain ``None``."""

    identity: InstrumentIdentity
    asset_class: str | None = None
    benchmark_name: str | None = None
    replication_method: str | None = None
    distribution_policy: str | None = None
    total_expense_ratio: float | None = None
    assets_under_management: float | None = None
    assets_under_management_currency: str | None = None
    holdings_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, InstrumentIdentity):
            raise TypeError("identity must be an InstrumentIdentity")
        if self.identity.instrument_type != "ETF":
            raise ValueError("identity must describe an ETF")

        for field_name in (
            "asset_class", "benchmark_name", "replication_method",
            "distribution_policy",
        ):
            object.__setattr__(self, field_name, normalize_optional_text(
                getattr(self, field_name), field_name=field_name,
            ))

        currency = normalize_optional_text(
            self.assets_under_management_currency,
            field_name="assets_under_management_currency",
            uppercase=True,
        )
        object.__setattr__(self, "assets_under_management_currency", currency)

        if self.total_expense_ratio is not None:
            ratio = _non_negative(
                self.total_expense_ratio, field_name="total_expense_ratio"
            )
            if ratio > 1.0:
                raise ValueError("total_expense_ratio must be between 0 and 1")
            object.__setattr__(self, "total_expense_ratio", ratio)

        if self.assets_under_management is not None:
            object.__setattr__(self, "assets_under_management", _non_negative(
                self.assets_under_management,
                field_name="assets_under_management",
            ))
        if (self.assets_under_management is None) != (currency is None):
            raise ValueError(
                "assets_under_management and its currency must be provided together"
            )

        if self.holdings_count is not None:
            if (isinstance(self.holdings_count, bool)
                    or not isinstance(self.holdings_count, Integral)
                    or self.holdings_count < 0):
                raise ValueError(
                    "holdings_count must be a non-negative integer or None"
                )
            object.__setattr__(self, "holdings_count", int(self.holdings_count))

    @classmethod
    def characteristic_field_names(cls) -> tuple[str, ...]:
        return (
            "asset_class", "benchmark_name", "replication_method",
            "distribution_policy", "total_expense_ratio",
            "assets_under_management", "holdings_count",
        )

    @property
    def missing_characteristics(self) -> tuple[str, ...]:
        return tuple(name for name in self.characteristic_field_names()
                     if getattr(self, name) is None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "asset_class": self.asset_class,
            "benchmark_name": self.benchmark_name,
            "replication_method": self.replication_method,
            "distribution_policy": self.distribution_policy,
            "total_expense_ratio": self.total_expense_ratio,
            "assets_under_management": self.assets_under_management,
            "assets_under_management_currency": self.assets_under_management_currency,
            "holdings_count": self.holdings_count,
            "missing_characteristics": list(self.missing_characteristics),
        }


@dataclass(frozen=True, slots=True)
class ETFCharacteristicsEvidence:
    """ETF facts together with their source lineage and quality state."""

    characteristics: ETFCharacteristics
    provenance: MarketMetadataProvenance
    quality: MarketMetadataQualityAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.characteristics, ETFCharacteristics):
            raise TypeError("characteristics must be ETFCharacteristics")
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
            "characteristics": self.characteristics.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
        }


def _non_negative(value: object, *, field_name: str) -> float:
    normalized = validate_finite_number(value, field_name=field_name)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized
