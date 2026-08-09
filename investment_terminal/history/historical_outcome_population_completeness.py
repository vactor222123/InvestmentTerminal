"""
Temporal completeness assessment for historical research source populations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Iterable

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomePopulationCompletenessAssessment:
    """
    Describe whether observed source timestamps cover an explicit research range.

    This contract assesses only temporal boundary coverage. It does not infer
    that snapshots should exist at any cadence and therefore does not claim
    that the archive has no internal gaps.
    """

    status: str
    source_observation_count: int
    observed_origin_start: datetime | None
    observed_origin_end: datetime | None
    requested_origin_start: datetime | None
    requested_origin_end: datetime | None
    covers_requested_start: bool | None
    covers_requested_end: bool | None
    internal_continuity_status: str
    warning: str

    UNKNOWN: ClassVar[str] = "UNKNOWN"
    PARTIAL: ClassVar[str] = "PARTIAL"
    COVERED: ClassVar[str] = "COVERED"
    NOT_ASSESSED: ClassVar[str] = "NOT_ASSESSED"

    def __post_init__(self) -> None:
        if self.status not in {
            self.UNKNOWN,
            self.PARTIAL,
            self.COVERED,
        }:
            raise ValueError(
                f"unsupported completeness status: {self.status}"
            )
        if (
            isinstance(self.source_observation_count, bool)
            or not isinstance(self.source_observation_count, int)
            or self.source_observation_count < 0
        ):
            raise ValueError(
                "source_observation_count must be a non-negative integer"
            )

        for field_name in (
            "observed_origin_start",
            "observed_origin_end",
            "requested_origin_start",
            "requested_origin_end",
        ):
            value = getattr(self, field_name)
            if value is not None:
                validate_aware_datetime(
                    value,
                    field_name=field_name,
                )

        if (
            self.observed_origin_start is not None
            and self.observed_origin_end is not None
            and self.observed_origin_start > self.observed_origin_end
        ):
            raise ValueError(
                "observed_origin_start must not be later than observed_origin_end"
            )
        if (
            self.requested_origin_start is not None
            and self.requested_origin_end is not None
            and self.requested_origin_start > self.requested_origin_end
        ):
            raise ValueError(
                "requested_origin_start must not be later than requested_origin_end"
            )

        for field_name in (
            "covers_requested_start",
            "covers_requested_end",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be a bool or None"
                )

        if self.internal_continuity_status != self.NOT_ASSESSED:
            raise ValueError(
                "internal_continuity_status must be NOT_ASSESSED"
            )
        if not isinstance(self.warning, str) or not self.warning.strip():
            raise ValueError(
                "warning must be a non-empty string"
            )

        expected_status = self._expected_status()
        if self.status != expected_status:
            raise ValueError(
                "status does not match temporal boundary coverage"
            )

    def _expected_status(self) -> str:
        if (
            self.source_observation_count == 0
            or (
                self.requested_origin_start is None
                and self.requested_origin_end is None
            )
        ):
            return self.UNKNOWN

        checks = tuple(
            value
            for value in (
                self.covers_requested_start,
                self.covers_requested_end,
            )
            if value is not None
        )
        if checks and all(checks):
            return self.COVERED
        return self.PARTIAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_observation_count": self.source_observation_count,
            "observed_origin_start": (
                None
                if self.observed_origin_start is None
                else self.observed_origin_start.isoformat()
            ),
            "observed_origin_end": (
                None
                if self.observed_origin_end is None
                else self.observed_origin_end.isoformat()
            ),
            "requested_origin_start": (
                None
                if self.requested_origin_start is None
                else self.requested_origin_start.isoformat()
            ),
            "requested_origin_end": (
                None
                if self.requested_origin_end is None
                else self.requested_origin_end.isoformat()
            ),
            "covers_requested_start": self.covers_requested_start,
            "covers_requested_end": self.covers_requested_end,
            "internal_continuity_status": self.internal_continuity_status,
            "warning": self.warning,
        }


class HistoricalOutcomePopulationCompletenessService:
    """
    Assess only source temporal boundary coverage.

    Internal archive continuity is intentionally not inferred because the
    product has no canonical expected snapshot cadence.
    """

    WARNING = (
        "Temporal boundary coverage only; internal archive continuity is not "
        "assessed because no canonical expected snapshot cadence is defined"
    )

    def assess(
        self,
        results: Iterable[HistoricalMethodologyAwareObservationResult],
        *,
        requested_origin_start: datetime | None = None,
        requested_origin_end: datetime | None = None,
    ) -> HistoricalOutcomePopulationCompletenessAssessment:
        if requested_origin_start is not None:
            validate_aware_datetime(
                requested_origin_start,
                field_name="requested_origin_start",
            )
        if requested_origin_end is not None:
            validate_aware_datetime(
                requested_origin_end,
                field_name="requested_origin_end",
            )
        if (
            requested_origin_start is not None
            and requested_origin_end is not None
            and requested_origin_start > requested_origin_end
        ):
            raise ValueError(
                "requested_origin_start must not be later than requested_origin_end"
            )

        materialized = tuple(results)
        for result in materialized:
            if not isinstance(
                result,
                HistoricalMethodologyAwareObservationResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "HistoricalMethodologyAwareObservationResult"
                )

        origins = tuple(
            result.observation.origin_at
            for result in materialized
        )
        observed_start = min(origins) if origins else None
        observed_end = max(origins) if origins else None

        covers_start = (
            None
            if requested_origin_start is None
            else (
                observed_start is not None
                and observed_start <= requested_origin_start
            )
        )
        covers_end = (
            None
            if requested_origin_end is None
            else (
                observed_end is not None
                and observed_end >= requested_origin_end
            )
        )

        if (
            not materialized
            or (
                requested_origin_start is None
                and requested_origin_end is None
            )
        ):
            status = HistoricalOutcomePopulationCompletenessAssessment.UNKNOWN
        else:
            checks = tuple(
                value
                for value in (
                    covers_start,
                    covers_end,
                )
                if value is not None
            )
            status = (
                HistoricalOutcomePopulationCompletenessAssessment.COVERED
                if checks and all(checks)
                else HistoricalOutcomePopulationCompletenessAssessment.PARTIAL
            )

        return HistoricalOutcomePopulationCompletenessAssessment(
            status=status,
            source_observation_count=len(materialized),
            observed_origin_start=observed_start,
            observed_origin_end=observed_end,
            requested_origin_start=requested_origin_start,
            requested_origin_end=requested_origin_end,
            covers_requested_start=covers_start,
            covers_requested_end=covers_end,
            internal_continuity_status=(
                HistoricalOutcomePopulationCompletenessAssessment.NOT_ASSESSED
            ),
            warning=self.WARNING,
        )
