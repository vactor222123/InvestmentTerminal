"""Provenance-aware read-only enrichment of reconstructed positions."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityAssessment,
    MarketMetadataQualityService,
)
from investment_terminal.portfolio.position_reconstruction import (
    PositionReconstruction,
    ReconstructedPosition,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class InstrumentMetadataEvidence:
    """Explicit venue metadata and its source lineage for one instrument."""

    instrument_key: str
    exchange_ticker: str
    exchange_code: str | None
    provenance: MarketMetadataProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_key", normalize_required_text(
            self.instrument_key, field_name="instrument_key", uppercase=True
        ))
        object.__setattr__(self, "exchange_ticker", normalize_required_text(
            self.exchange_ticker, field_name="exchange_ticker", uppercase=True
        ))
        object.__setattr__(self, "exchange_code", normalize_optional_text(
            self.exchange_code, field_name="exchange_code", uppercase=True
        ))
        if any(character.isspace() for character in self.exchange_ticker):
            raise ValueError("exchange_ticker must not contain whitespace")
        if self.exchange_code is not None and any(
            character.isspace() for character in self.exchange_code
        ):
            raise ValueError("exchange_code must not contain whitespace")
        if not isinstance(self.provenance, MarketMetadataProvenance):
            raise TypeError("provenance must be MarketMetadataProvenance")

    def to_dict(self) -> dict[str, Any]:
        provenance = self.provenance.to_dict()
        provenance.pop("is_fully_traceable")
        return {
            "instrument_key": self.instrument_key,
            "exchange_ticker": self.exchange_ticker,
            "exchange_code": self.exchange_code,
            "provenance": provenance,
        }


@dataclass(frozen=True, slots=True)
class InstrumentMetadataDocument:
    """Deterministically ordered schema-version-1 metadata evidence."""

    instruments: tuple[InstrumentMetadataEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.instruments, tuple):
            raise TypeError("instruments must be a tuple")
        if any(not isinstance(item, InstrumentMetadataEvidence) for item in self.instruments):
            raise TypeError("instruments must contain InstrumentMetadataEvidence")
        keys = tuple(item.instrument_key for item in self.instruments)
        if keys != tuple(sorted(keys)):
            raise ValueError("instruments must be ordered by instrument_key")
        if len(keys) != len(set(keys)):
            raise ValueError("instruments must contain unique instrument keys")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "instruments": [item.to_dict() for item in self.instruments],
        }


class InstrumentMetadataJsonLoader:
    """Load strict private instrument metadata without external lookup."""

    @classmethod
    def load(cls, path: str | Path) -> InstrumentMetadataDocument:
        resolved = path if isinstance(path, Path) else Path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Instrument metadata file does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError("Instrument metadata path must point to a file")
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Instrument metadata file contains invalid JSON") from exc
        if not isinstance(payload, dict):
            raise TypeError("Instrument metadata JSON root must be an object")
        cls._require_fields(payload, required={"schema_version", "instruments"},
                            allowed={"schema_version", "instruments"}, context="root")
        if payload["schema_version"] != 1:
            raise ValueError("Unsupported instrument metadata schema_version")
        if not isinstance(payload["instruments"], list):
            raise TypeError("instruments must be a JSON array")
        items = tuple(cls._item(value, index) for index, value in enumerate(
            payload["instruments"], start=1
        ))
        return InstrumentMetadataDocument(tuple(sorted(items, key=lambda item: item.instrument_key)))

    @classmethod
    def _item(cls, value: Any, number: int) -> InstrumentMetadataEvidence:
        if not isinstance(value, dict):
            raise TypeError(f"Instrument metadata item {number} must be an object")
        cls._require_fields(
            value,
            required={"instrument_key", "exchange_ticker", "provenance"},
            allowed={"instrument_key", "exchange_ticker", "exchange_code", "provenance"},
            context=f"item {number}",
        )
        provenance = value["provenance"]
        if not isinstance(provenance, dict):
            raise TypeError(f"Instrument metadata item {number} provenance must be an object")
        cls._require_fields(
            provenance,
            required={"source", "observed_at", "fetched_at"},
            allowed={"source", "source_record_id", "observed_at", "fetched_at", "checksum_sha256"},
            context=f"item {number} provenance",
        )
        try:
            source = MarketMetadataProvenance(
                source=provenance["source"],
                source_record_id=provenance.get("source_record_id"),
                observed_at=cls._datetime(provenance["observed_at"]),
                fetched_at=cls._datetime(provenance["fetched_at"]),
                checksum_sha256=provenance.get("checksum_sha256"),
            )
            return InstrumentMetadataEvidence(
                instrument_key=value["instrument_key"],
                exchange_ticker=value["exchange_ticker"],
                exchange_code=value.get("exchange_code"),
                provenance=source,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid instrument metadata item {number}: {exc}") from exc

    @staticmethod
    def _datetime(value: Any) -> datetime:
        if not isinstance(value, str):
            raise TypeError("metadata timestamps must be strings")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _require_fields(payload: dict[str, Any], *, required: set[str],
                        allowed: set[str], context: str) -> None:
        missing = sorted(required - payload.keys())
        extra = sorted(payload.keys() - allowed)
        if missing:
            raise ValueError(f"Instrument metadata {context} is missing fields: {', '.join(missing)}")
        if extra:
            raise ValueError(f"Instrument metadata {context} has unknown fields: {', '.join(extra)}")


@dataclass(frozen=True, slots=True)
class InstrumentMetadataEnrichmentResult:
    reconstruction: PositionReconstruction
    evidence: tuple[InstrumentMetadataEvidence, ...]
    quality: tuple[MarketMetadataQualityAssessment, ...]


class InstrumentMetadataEnrichmentService:
    """Create a detached enriched projection without changing ledger evidence."""

    @classmethod
    def enrich(cls, reconstruction: PositionReconstruction,
               document: InstrumentMetadataDocument, *, checked_at: datetime,
               maximum_age_days: float) -> InstrumentMetadataEnrichmentResult:
        if not isinstance(reconstruction, PositionReconstruction):
            raise TypeError("reconstruction must be a PositionReconstruction")
        if not isinstance(document, InstrumentMetadataDocument):
            raise TypeError("document must be an InstrumentMetadataDocument")
        cutoff = validate_aware_datetime(checked_at, field_name="checked_at")
        required = {position.instrument_key for position in reconstruction.positions}
        available = {item.instrument_key for item in document.instruments}
        if available != required:
            raise ValueError("instrument metadata coverage must exactly match open positions")

        by_key = {item.instrument_key: item for item in document.instruments}
        positions: list[ReconstructedPosition] = []
        assessments: list[MarketMetadataQualityAssessment] = []
        for position in reconstruction.positions:
            item = by_key[position.instrument_key]
            if item.provenance.fetched_at > cutoff:
                raise ValueError("instrument metadata was fetched later than checked_at")
            quality = MarketMetadataQualityService.assess(
                item.provenance, checked_at=cutoff, maximum_age_days=maximum_age_days
            )
            if not quality.is_ready:
                raise ValueError("instrument metadata quality must be READY")
            enriched_identity = cls._identity(position.instrument, item)
            if enriched_identity.instrument_key != position.instrument_key:
                raise ValueError("instrument metadata must not change instrument_key")
            positions.append(ReconstructedPosition(
                instrument=enriched_identity,
                quantity=position.quantity,
                cost_basis=position.cost_basis,
                average_cost=position.average_cost,
                cost_currency=position.cost_currency,
            ))
            assessments.append(quality)
        enriched = PositionReconstruction(
            ledger_id=reconstruction.ledger_id,
            portfolio_name=reconstruction.portfolio_name,
            processed_trade_count=reconstruction.processed_trade_count,
            positions=tuple(positions),
        )
        return InstrumentMetadataEnrichmentResult(
            reconstruction=enriched,
            evidence=document.instruments,
            quality=tuple(assessments),
        )

    @staticmethod
    def _identity(original: InstrumentIdentity,
                  evidence: InstrumentMetadataEvidence) -> InstrumentIdentity:
        if original.exchange_ticker not in (None, evidence.exchange_ticker):
            raise ValueError("instrument metadata conflicts with exchange_ticker")
        if original.exchange_code not in (None, evidence.exchange_code):
            raise ValueError("instrument metadata conflicts with exchange_code")
        return InstrumentIdentity(
            symbol=original.symbol,
            name=original.name,
            instrument_type=original.instrument_type,
            currency=original.currency,
            isin=original.isin,
            exchange_ticker=evidence.exchange_ticker,
            exchange_code=evidence.exchange_code,
        )
