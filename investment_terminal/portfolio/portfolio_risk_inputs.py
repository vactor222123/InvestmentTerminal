"""Provider-neutral immutable inputs for portfolio risk analysis."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)

RETURN_SERIES_SUBJECT_TYPES = ("PORTFOLIO", "INSTRUMENT")
RETURN_PERIODS = ("DAILY", "WEEKLY", "MONTHLY")


@dataclass(frozen=True, slots=True)
class RiskDataProvenance:
    """Trace one risk input series to its provider-neutral source record."""

    source: str
    source_record_id: str
    fetched_at: datetime

    def __post_init__(self) -> None:
        for field_name in ("source", "source_record_id"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        validate_aware_datetime(self.fetched_at, field_name="fetched_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_record_id": self.source_record_id,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ReturnObservation:
    """One explicit total return over a closed-open observation period."""

    period_started_at: datetime
    period_ended_at: datetime
    return_fraction: float

    def __post_init__(self) -> None:
        start = validate_aware_datetime(
            self.period_started_at, field_name="period_started_at"
        )
        end = validate_aware_datetime(
            self.period_ended_at, field_name="period_ended_at"
        )
        if end <= start:
            raise ValueError("period_ended_at must be later than period_started_at")
        value = validate_finite_number(
            self.return_fraction, field_name="return_fraction"
        )
        if value < -1:
            raise ValueError("return_fraction must not be less than -1")
        object.__setattr__(self, "return_fraction", value)

    @property
    def period_key(self) -> tuple[datetime, datetime]:
        return (self.period_started_at, self.period_ended_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_started_at": self.period_started_at.isoformat(),
            "period_ended_at": self.period_ended_at.isoformat(),
            "return_fraction": self.return_fraction,
        }


@dataclass(frozen=True, slots=True)
class ReturnSeries:
    """One deterministic currency-explicit return series."""

    subject_type: str
    subject_key: str
    currency: str
    period: str
    observations: tuple[ReturnObservation, ...]
    provenance: RiskDataProvenance

    def __post_init__(self) -> None:
        subject_type = normalize_required_text(
            self.subject_type, field_name="subject_type", uppercase=True
        )
        if subject_type not in RETURN_SERIES_SUBJECT_TYPES:
            raise ValueError(
                "subject_type must be one of: " + ", ".join(RETURN_SERIES_SUBJECT_TYPES)
            )
        period = normalize_required_text(
            self.period, field_name="period", uppercase=True
        )
        if period not in RETURN_PERIODS:
            raise ValueError("period must be one of: " + ", ".join(RETURN_PERIODS))
        if not isinstance(self.observations, tuple):
            raise TypeError("observations must be a tuple")
        if len(self.observations) < 2:
            raise ValueError("observations must contain at least two periods")
        if any(not isinstance(item, ReturnObservation) for item in self.observations):
            raise TypeError("observations must contain only ReturnObservation objects")
        keys = tuple(item.period_key for item in self.observations)
        if keys != tuple(sorted(keys)):
            raise ValueError("observations must be ordered by period")
        if len(keys) != len(set(keys)):
            raise ValueError("observations must contain unique periods")
        if any(
            current.period_started_at < previous.period_ended_at
            for previous, current in zip(self.observations, self.observations[1:])
        ):
            raise ValueError("observation periods must not overlap")
        if not isinstance(self.provenance, RiskDataProvenance):
            raise TypeError("provenance must be a RiskDataProvenance")
        object.__setattr__(self, "subject_type", subject_type)
        object.__setattr__(
            self,
            "subject_key",
            normalize_required_text(
                self.subject_key, field_name="subject_key", uppercase=True
            ),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency, field_name="currency", uppercase=True
            ),
        )
        object.__setattr__(self, "period", period)

    @property
    def started_at(self) -> datetime:
        return self.observations[0].period_started_at

    @property
    def ended_at(self) -> datetime:
        return self.observations[-1].period_ended_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "subject_key": self.subject_key,
            "currency": self.currency,
            "period": self.period,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "observation_count": len(self.observations),
            "observations": [item.to_dict() for item in self.observations],
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PortfolioRiskInput:
    """Validated portfolio and instrument return evidence at one cutoff."""

    ledger_id: str
    portfolio_name: str
    as_of: datetime
    portfolio_returns: ReturnSeries
    instrument_returns: tuple[ReturnSeries, ...]

    def __post_init__(self) -> None:
        ledger_id = normalize_required_text(self.ledger_id, field_name="ledger_id")
        object.__setattr__(self, "ledger_id", ledger_id)
        object.__setattr__(
            self,
            "portfolio_name",
            normalize_required_text(self.portfolio_name, field_name="portfolio_name"),
        )
        cutoff = validate_aware_datetime(self.as_of, field_name="as_of")
        if not isinstance(self.portfolio_returns, ReturnSeries):
            raise TypeError("portfolio_returns must be a ReturnSeries")
        if self.portfolio_returns.subject_type != "PORTFOLIO":
            raise ValueError("portfolio_returns must use PORTFOLIO subject_type")
        if self.portfolio_returns.subject_key != ledger_id.upper():
            raise ValueError("portfolio_returns must use the input ledger_id")
        if not isinstance(self.instrument_returns, tuple):
            raise TypeError("instrument_returns must be a tuple")
        if any(not isinstance(item, ReturnSeries) for item in self.instrument_returns):
            raise TypeError("instrument_returns must contain only ReturnSeries objects")
        if any(item.subject_type != "INSTRUMENT" for item in self.instrument_returns):
            raise ValueError("instrument_returns must use INSTRUMENT subject_type")
        keys = tuple(item.subject_key for item in self.instrument_returns)
        if keys != tuple(sorted(keys)):
            raise ValueError("instrument_returns must be ordered by subject_key")
        if len(keys) != len(set(keys)):
            raise ValueError("instrument_returns must contain unique subject keys")
        series = (self.portfolio_returns, *self.instrument_returns)
        if any(item.ended_at > cutoff for item in series):
            raise ValueError("return observations must not be later than as_of")
        if any(item.provenance.fetched_at > cutoff for item in series):
            raise ValueError("risk provenance must not be later than as_of")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "as_of": self.as_of.isoformat(),
            "portfolio_returns": self.portfolio_returns.to_dict(),
            "instrument_series_count": len(self.instrument_returns),
            "instrument_returns": [item.to_dict() for item in self.instrument_returns],
        }
