"""Bounded operational qualification for Yahoo historical candles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Any, Protocol

from investment_terminal.models.candle import Candle
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class YahooHistoricalCandleClient(Protocol):
    """Narrow existing-client seam used by operational qualification."""

    def get_candles(
        self,
        symbol: str,
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
    ) -> list[Candle]: ...


class YahooCandleQualificationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class YahooCandleQualificationRequest:
    symbol: str
    resolution: str
    currency: str
    requested_start: datetime
    requested_end: datetime

    def __post_init__(self) -> None:
        symbol = normalize_required_text(
            self.symbol,
            field_name="symbol",
            uppercase=True,
        )
        if any(character.isspace() for character in symbol):
            raise ValueError("symbol must not contain whitespace")
        object.__setattr__(self, "symbol", symbol)
        resolution = normalize_required_text(
            self.resolution,
            field_name="resolution",
            uppercase=True,
        )
        if resolution not in {"D", "W", "M"}:
            raise ValueError("resolution must be one of: D, W, M")
        object.__setattr__(self, "resolution", resolution)
        currency = normalize_required_text(
            self.currency,
            field_name="currency",
            uppercase=True,
        )
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code")
        object.__setattr__(self, "currency", currency)
        validate_aware_datetime(
            self.requested_start,
            field_name="requested_start",
        )
        validate_aware_datetime(
            self.requested_end,
            field_name="requested_end",
        )
        if self.requested_start >= self.requested_end:
            raise ValueError("requested_start must be earlier than requested_end")


@dataclass(frozen=True, slots=True)
class YahooCandleQualificationResult:
    request: YahooCandleQualificationRequest
    status: YahooCandleQualificationStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    candle_count: int | None
    earliest_candle_at: datetime | None = None
    latest_candle_at: datetime | None = None
    failure_type: str | None = None
    failure_reason: str | None = None
    schema_version: int = 1
    provider_identity: str = "YAHOO_FINANCE"

    def __post_init__(self) -> None:
        if not isinstance(self.request, YahooCandleQualificationRequest):
            raise TypeError("request must be YahooCandleQualificationRequest")
        if not isinstance(self.status, YahooCandleQualificationStatus):
            raise TypeError("status must be YahooCandleQualificationStatus")
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if self.provider_identity != "YAHOO_FINANCE":
            raise ValueError("provider_identity must be YAHOO_FINANCE")
        validate_aware_datetime(self.started_at, field_name="started_at")
        validate_aware_datetime(self.completed_at, field_name="completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")
        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
            or not isfinite(float(self.duration_seconds))
            or self.duration_seconds < 0
        ):
            raise ValueError("duration_seconds must be finite and non-negative")
        expected_duration = (
            self.completed_at - self.started_at
        ).total_seconds()
        if float(self.duration_seconds) != expected_duration:
            raise ValueError("duration_seconds must match run timestamps")

        if self.status is YahooCandleQualificationStatus.SUCCESS:
            if self.candle_count is None or self.candle_count < 1:
                raise ValueError("SUCCESS requires a positive candle_count")
            if self.earliest_candle_at is None or self.latest_candle_at is None:
                raise ValueError("SUCCESS requires candle coverage timestamps")
            if self.failure_type is not None or self.failure_reason is not None:
                raise ValueError("SUCCESS cannot carry failure details")
        elif self.status is YahooCandleQualificationStatus.EMPTY:
            if self.candle_count != 0:
                raise ValueError("EMPTY requires candle_count zero")
            if self.earliest_candle_at is not None or self.latest_candle_at is not None:
                raise ValueError("EMPTY cannot carry candle coverage timestamps")
            if self.failure_type is not None or self.failure_reason is not None:
                raise ValueError("EMPTY cannot carry failure details")
        else:
            if self.candle_count is not None:
                raise ValueError("FAILED requires unknown candle_count")
            if self.earliest_candle_at is not None or self.latest_candle_at is not None:
                raise ValueError("FAILED cannot carry candle coverage timestamps")
            if not self.failure_type or not self.failure_reason:
                raise ValueError("FAILED requires failure details")

        for value, field_name in (
            (self.earliest_candle_at, "earliest_candle_at"),
            (self.latest_candle_at, "latest_candle_at"),
        ):
            if value is not None:
                validate_aware_datetime(value, field_name=field_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_identity": self.provider_identity,
            "status": self.status.value,
            "request": {
                "symbol": self.request.symbol,
                "resolution": self.request.resolution,
                "currency": self.request.currency,
                "requested_start": self.request.requested_start.isoformat(),
                "requested_end": self.request.requested_end.isoformat(),
            },
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "coverage": {
                "candle_count": self.candle_count,
                "earliest_candle_at": (
                    None
                    if self.earliest_candle_at is None
                    else self.earliest_candle_at.isoformat()
                ),
                "latest_candle_at": (
                    None
                    if self.latest_candle_at is None
                    else self.latest_candle_at.isoformat()
                ),
            },
            "failure": (
                None
                if self.failure_type is None
                else {
                    "type": self.failure_type,
                    "reason": self.failure_reason,
                }
            ),
            "limitations": [
                "one request does not establish general provider reliability",
                "result does not establish licensing suitability",
                "result does not establish approximately 20-year coverage",
                "result does not authorize analysis or trading",
            ],
        }


class YahooCandleQualificationService:
    """Execute one bounded provider request and preserve operational facts."""

    def __init__(self, *, client: YahooHistoricalCandleClient, clock) -> None:
        self._client = client
        self._clock = clock

    def qualify(
        self,
        request: YahooCandleQualificationRequest,
    ) -> YahooCandleQualificationResult:
        if not isinstance(request, YahooCandleQualificationRequest):
            raise TypeError("request must be YahooCandleQualificationRequest")
        started_at = self._clock()
        validate_aware_datetime(started_at, field_name="started_at")
        try:
            candles = self._client.get_candles(
                symbol=request.symbol,
                resolution=request.resolution,
                start=request.requested_start,
                end=request.requested_end,
                currency=request.currency,
            )
            self._validate_candles(request, candles)
        except Exception as exc:
            completed_at = self._completed_at(started_at)
            reason = str(exc).strip() or "provider qualification failed"
            return YahooCandleQualificationResult(
                request=request,
                status=YahooCandleQualificationStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                candle_count=None,
                failure_type=type(exc).__name__,
                failure_reason=reason,
            )

        completed_at = self._completed_at(started_at)
        if not candles:
            return YahooCandleQualificationResult(
                request=request,
                status=YahooCandleQualificationStatus.EMPTY,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                candle_count=0,
            )
        return YahooCandleQualificationResult(
            request=request,
            status=YahooCandleQualificationStatus.SUCCESS,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            candle_count=len(candles),
            earliest_candle_at=candles[0].timestamp,
            latest_candle_at=candles[-1].timestamp,
        )

    def _completed_at(self, started_at: datetime) -> datetime:
        completed_at = self._clock()
        validate_aware_datetime(completed_at, field_name="completed_at")
        if completed_at < started_at:
            raise ValueError("qualification clock moved backwards")
        return completed_at

    @staticmethod
    def _validate_candles(
        request: YahooCandleQualificationRequest,
        candles: object,
    ) -> None:
        if not isinstance(candles, list):
            raise TypeError("Yahoo client result must be a list")
        previous: datetime | None = None
        for candle in candles:
            if not isinstance(candle, Candle):
                raise TypeError("Yahoo client result must contain Candle values")
            if (
                candle.symbol != request.symbol
                or candle.resolution != request.resolution
                or candle.currency != request.currency
            ):
                raise ValueError("Yahoo candle is outside the requested identity")
            if not (
                request.requested_start
                <= candle.timestamp
                < request.requested_end
            ):
                raise ValueError("Yahoo candle is outside the requested window")
            if previous is not None and candle.timestamp <= previous:
                raise ValueError("Yahoo candles must be unique and ordered")
            previous = candle.timestamp
