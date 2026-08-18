"""Deterministic sector analysis evidence for maintained universes."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)
from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.universe.maintained_universe_models import (
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class SectorInstrumentEvidence:
    instrument: InstrumentIdentity
    classification: CompanyClassification

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        if self.instrument.instrument_type != "STOCK":
            raise ValueError("instrument must describe a STOCK")
        if not isinstance(self.classification, CompanyClassification):
            raise TypeError(
                "classification must be a CompanyClassification"
            )
        if self.instrument.symbol != self.classification.symbol:
            raise ValueError("classification symbol must match instrument")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "classification": self.classification.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SectorGroupEvidence:
    sector: str
    instruments: tuple[SectorInstrumentEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sector",
            normalize_required_text(self.sector, field_name="sector"),
        )
        if not isinstance(self.instruments, tuple) or not self.instruments:
            raise ValueError("instruments must be a non-empty tuple")
        if any(
            not isinstance(item, SectorInstrumentEvidence)
            for item in self.instruments
        ):
            raise TypeError(
                "instruments must contain SectorInstrumentEvidence values"
            )
        if any(
            item.classification.sector != self.sector
            for item in self.instruments
        ):
            raise ValueError("all instruments must match sector")
        ordered = tuple(sorted(
            self.instruments,
            key=lambda item: item.instrument.instrument_key,
        ))
        object.__setattr__(self, "instruments", ordered)

    @property
    def industry_counts(self) -> dict[str, int]:
        counts = Counter(
            item.classification.industry for item in self.instruments
        )
        return {key: counts[key] for key in sorted(counts)}

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "instrument_count": len(self.instruments),
            "industry_counts": self.industry_counts,
            "instruments": [item.to_dict() for item in self.instruments],
        }


@dataclass(frozen=True, slots=True)
class SectorAnalysisEvidence:
    universe: MaintainedAssetUniverseEvidence
    assessed_at: datetime
    eligible_instrument_count: int
    sectors: tuple[SectorGroupEvidence, ...]
    unclassified_instrument_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.universe, MaintainedAssetUniverseEvidence):
            raise TypeError(
                "universe must be MaintainedAssetUniverseEvidence"
            )
        validate_aware_datetime(self.assessed_at, field_name="assessed_at")
        if self.assessed_at < self.universe.universe.as_of:
            raise ValueError("assessed_at must not be earlier than universe")
        if (
            isinstance(self.eligible_instrument_count, bool)
            or not isinstance(self.eligible_instrument_count, int)
            or self.eligible_instrument_count < 0
        ):
            raise ValueError(
                "eligible_instrument_count must be non-negative"
            )
        if not isinstance(self.sectors, tuple):
            raise TypeError("sectors must be a tuple")
        if any(not isinstance(item, SectorGroupEvidence) for item in self.sectors):
            raise TypeError("sectors must contain SectorGroupEvidence values")
        if not isinstance(self.unclassified_instrument_keys, tuple):
            raise TypeError("unclassified_instrument_keys must be a tuple")

    @property
    def classified_instrument_count(self) -> int:
        return sum(len(item.instruments) for item in self.sectors)

    @property
    def coverage(self) -> float:
        if self.eligible_instrument_count == 0:
            return 0.0
        return round(
            self.classified_instrument_count
            / self.eligible_instrument_count,
            8,
        )

    @property
    def quality_status(self) -> str:
        if self.universe.quality.status == "STALE":
            return "STALE"
        if (
            self.universe.quality.status == "PARTIAL"
            or self.unclassified_instrument_keys
            or self.eligible_instrument_count == 0
        ):
            return "PARTIAL"
        return "READY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe": self.universe.to_dict(),
            "assessed_at": self.assessed_at.isoformat(),
            "eligible_instrument_count": self.eligible_instrument_count,
            "classified_instrument_count": self.classified_instrument_count,
            "coverage": self.coverage,
            "quality_status": self.quality_status,
            "unclassified_instrument_keys": list(
                self.unclassified_instrument_keys
            ),
            "sectors": [item.to_dict() for item in self.sectors],
        }


class SectorAnalysisEvidenceBuilder:
    """Aggregate existing company classifications without scoring sectors."""

    @classmethod
    def build(
        cls,
        universe: MaintainedAssetUniverseEvidence,
        classifications: tuple[CompanyClassification, ...],
        *,
        assessed_at: datetime,
    ) -> SectorAnalysisEvidence:
        if not isinstance(universe, MaintainedAssetUniverseEvidence):
            raise TypeError(
                "universe must be MaintainedAssetUniverseEvidence"
            )
        validate_aware_datetime(assessed_at, field_name="assessed_at")
        if universe.quality.checked_at > assessed_at:
            raise ValueError("universe quality cannot be after assessed_at")
        if not isinstance(classifications, tuple):
            raise TypeError("classifications must be a tuple")
        if any(
            not isinstance(item, CompanyClassification)
            for item in classifications
        ):
            raise TypeError(
                "classifications must contain CompanyClassification values"
            )
        stock_members = tuple(
            member.instrument
            for member in universe.universe.members
            if member.instrument.instrument_type == "STOCK"
        )
        symbols = tuple(item.symbol for item in stock_members)
        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "stock member symbols must be unique for classification"
            )
        by_symbol: dict[str, CompanyClassification] = {}
        for item in classifications:
            if item.symbol in by_symbol:
                raise ValueError(
                    "classifications contains duplicate symbol"
                )
            if item.symbol not in symbols:
                raise ValueError(
                    "classification contains symbol outside universe"
                )
            by_symbol[item.symbol] = item

        grouped: dict[str, list[SectorInstrumentEvidence]] = {}
        missing: list[str] = []
        for instrument in stock_members:
            classification = by_symbol.get(instrument.symbol)
            if classification is None:
                missing.append(instrument.instrument_key)
                continue
            item = SectorInstrumentEvidence(instrument, classification)
            grouped.setdefault(classification.sector, []).append(item)
        sectors = tuple(
            SectorGroupEvidence(sector, tuple(grouped[sector]))
            for sector in sorted(grouped)
        )
        return SectorAnalysisEvidence(
            universe=universe,
            assessed_at=assessed_at,
            eligible_instrument_count=len(stock_members),
            sectors=sectors,
            unclassified_instrument_keys=tuple(sorted(missing)),
        )
