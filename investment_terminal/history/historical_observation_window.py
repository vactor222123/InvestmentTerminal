"""
Deterministic observation-window policy for historical outcome analysis.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalObservationWindowResolution:
    """Resolved endpoint and maturity for one explicit observation window."""

    origin_at: datetime
    endpoint_at: datetime
    as_of: datetime
    is_mature: bool

    def __post_init__(self) -> None:
        validate_aware_datetime(
            self.origin_at,
            field_name="origin_at",
        )
        validate_aware_datetime(
            self.endpoint_at,
            field_name="endpoint_at",
        )
        validate_aware_datetime(
            self.as_of,
            field_name="as_of",
        )

        if self.endpoint_at < self.origin_at:
            raise ValueError(
                "endpoint_at must not be earlier than origin_at"
            )

        expected_maturity = (
            self.as_of >= self.endpoint_at
        )
        if self.is_mature is not expected_maturity:
            raise ValueError(
                "is_mature must match as_of relative to endpoint_at"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "origin_at": self.origin_at.isoformat(),
            "endpoint_at": self.endpoint_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "is_mature": self.is_mature,
        }


class HistoricalObservationWindowPolicy:
    """
    Resolve the first canonical Sprint 14 observation-window semantics.

    `ELAPSED_DAYS` means N absolute 24-hour periods measured from the origin.
    Calculation is normalized to UTC so DST or local wall-clock transitions do
    not change the elapsed duration.

    This policy intentionally does not implement trading-session semantics,
    market calendars, candle selection, or nearest-date substitution.
    """

    ELAPSED_DAYS: ClassVar[str] = "ELAPSED_DAYS"
    SUPPORTED_KINDS: ClassVar[tuple[str, ...]] = (
        ELAPSED_DAYS,
    )

    def resolve(
        self,
        *,
        origin_at: datetime,
        window: HistoricalObservationWindow,
        as_of: datetime,
    ) -> HistoricalObservationWindowResolution:
        """Resolve one endpoint and whether it has matured by `as_of`."""
        validate_aware_datetime(
            origin_at,
            field_name="origin_at",
        )
        validate_aware_datetime(
            as_of,
            field_name="as_of",
        )

        if not isinstance(
            window,
            HistoricalObservationWindow,
        ):
            raise TypeError(
                "window must be a HistoricalObservationWindow"
            )

        if window.kind not in self.SUPPORTED_KINDS:
            raise ValueError(
                "window kind is not supported by this policy: "
                f"{window.kind}"
            )

        origin_utc = origin_at.astimezone(
            timezone.utc
        )
        as_of_utc = as_of.astimezone(
            timezone.utc
        )
        endpoint_utc = origin_utc + timedelta(
            days=window.value
        )

        return HistoricalObservationWindowResolution(
            origin_at=origin_utc,
            endpoint_at=endpoint_utc,
            as_of=as_of_utc,
            is_mature=(
                as_of_utc
                >= endpoint_utc
            ),
        )
