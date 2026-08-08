"""
Read-only local candle adapter for historical outcome price evidence.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalPricePoint:
    """One exact historical close-price observation with provenance."""

    instrument_key: str
    observed_at: datetime
    price: float
    currency: str
    resolution: str
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instrument_key",
            normalize_required_text(
                self.instrument_key,
                field_name="instrument_key",
                uppercase=True,
            ),
        )
        validate_aware_datetime(
            self.observed_at,
            field_name="observed_at",
        )

        if (
            isinstance(self.price, bool)
            or not isinstance(
                self.price,
                (int, float),
            )
            or float(self.price) <= 0.0
        ):
            raise ValueError(
                "price must be a positive number"
            )
        object.__setattr__(
            self,
            "price",
            float(self.price),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency,
                field_name="currency",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "resolution",
            normalize_required_text(
                self.resolution,
                field_name="resolution",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "source",
            normalize_required_text(
                self.source,
                field_name="source",
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "observed_at": self.observed_at.isoformat(),
            "price": self.price,
            "currency": self.currency,
            "resolution": self.resolution,
            "source": self.source,
        }


class HistoricalOutcomePriceEvidenceProvider:
    """
    Read exact historical close-price evidence from local persisted candles.

    No network calls, current-price fallback, nearest-date substitution, or
    implicit timezone conversion of naive stored timestamps are allowed.
    """

    SOURCE = "LOCAL_CANDLE_REPOSITORY_CLOSE"

    def __init__(
        self,
        repository: CandleRepository,
    ) -> None:
        if not isinstance(
            repository,
            CandleRepository,
        ):
            raise TypeError(
                "repository must be a CandleRepository"
            )

        self.repository = repository

    def get_exact(
        self,
        *,
        instrument_key: str,
        resolution: str,
        observed_at: datetime,
    ) -> HistoricalPricePoint | None:
        """Return exact close-price evidence or None when unavailable."""
        normalized_instrument = normalize_required_text(
            instrument_key,
            field_name="instrument_key",
            uppercase=True,
        )
        normalized_resolution = normalize_required_text(
            resolution,
            field_name="resolution",
            uppercase=True,
        )
        validate_aware_datetime(
            observed_at,
            field_name="observed_at",
        )

        target_utc = observed_at.astimezone(
            timezone.utc
        )

        candidates = self.repository.get_range(
            normalized_instrument,
            normalized_resolution,
        )

        exact = []
        for candle in candidates:
            if candle.timestamp is None:
                continue

            try:
                candle_utc = validate_aware_datetime(
                    candle.timestamp,
                    field_name="candle timestamp",
                ).astimezone(
                    timezone.utc
                )
            except ValueError as exc:
                raise ValueError(
                    "stored candle timestamp must be timezone-aware "
                    "for historical outcome evidence"
                ) from exc

            if candle_utc == target_utc:
                exact.append(
                    candle
                )

        if not exact:
            return None

        if len(exact) != 1:
            raise RuntimeError(
                "multiple exact historical candles found for "
                f"{normalized_instrument} {normalized_resolution} "
                f"at {target_utc.isoformat()}"
            )

        candle = exact[0]

        return HistoricalPricePoint(
            instrument_key=normalized_instrument,
            observed_at=target_utc,
            price=candle.close_price,
            currency=candle.currency,
            resolution=normalized_resolution,
            source=self.SOURCE,
        )
