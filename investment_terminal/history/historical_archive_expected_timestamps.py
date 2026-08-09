"""
Deterministic expected timestamp generation for historical archive cadence.
"""

from datetime import datetime, timedelta

from investment_terminal.history.historical_archive_cadence import (
    HistoricalArchiveCadencePolicy,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


class HistoricalArchiveExpectedTimestampService:
    """
    Generate cadence-aligned GENERATED_AT points inside an inclusive interval.

    No tolerance, nearest-point substitution, calendar semantics, or gap
    classification is applied here.
    """

    def generate(
        self,
        *,
        policy: HistoricalArchiveCadencePolicy,
        start_at: datetime,
        end_at: datetime,
    ) -> tuple[datetime, ...]:
        if not isinstance(
            policy,
            HistoricalArchiveCadencePolicy,
        ):
            raise TypeError(
                "policy must be a HistoricalArchiveCadencePolicy"
            )

        validate_aware_datetime(
            start_at,
            field_name="start_at",
        )
        validate_aware_datetime(
            end_at,
            field_name="end_at",
        )
        if start_at > end_at:
            raise ValueError(
                "start_at must not be later than end_at"
            )

        interval = timedelta(
            seconds=policy.interval_seconds
        )
        anchor = policy.anchor_at

        if start_at <= anchor:
            first = anchor
        else:
            elapsed = start_at - anchor
            whole_steps = (
                elapsed // interval
            )
            first = (
                anchor
                + whole_steps * interval
            )
            if first < start_at:
                first += interval

        if first > end_at:
            return ()

        points: list[datetime] = []
        current = first
        while current <= end_at:
            points.append(
                current
            )
            current += interval

        return tuple(
            points
        )
