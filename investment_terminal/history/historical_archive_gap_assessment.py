"""
Gap assessment for expected versus observed historical archive timestamps.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Iterable

from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalArchiveGapAssessment:
    """Immutable comparison of expected and observed GENERATED_AT timestamps."""

    status: str
    expected_count: int
    observed_expected_count: int
    missing_count: int
    unexpected_observed_count: int
    missing_timestamps: tuple[datetime, ...]
    unexpected_observed_timestamps: tuple[datetime, ...]

    COMPLETE: ClassVar[str] = "COMPLETE"
    GAPS: ClassVar[str] = "GAPS"
    NO_EXPECTATION: ClassVar[str] = "NO_EXPECTATION"

    def __post_init__(self) -> None:
        if self.status not in {
            self.COMPLETE,
            self.GAPS,
            self.NO_EXPECTATION,
        }:
            raise ValueError(
                f"unsupported archive gap status: {self.status}"
            )

        for field_name in (
            "expected_count",
            "observed_expected_count",
            "missing_count",
            "unexpected_observed_count",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.observed_expected_count + self.missing_count != self.expected_count:
            raise ValueError(
                "observed_expected_count + missing_count must equal expected_count"
            )
        if len(self.missing_timestamps) != self.missing_count:
            raise ValueError(
                "missing_timestamps length must equal missing_count"
            )
        if (
            len(self.unexpected_observed_timestamps)
            != self.unexpected_observed_count
        ):
            raise ValueError(
                "unexpected_observed_timestamps length must equal "
                "unexpected_observed_count"
            )

        for field_name in (
            "missing_timestamps",
            "unexpected_observed_timestamps",
        ):
            values = getattr(
                self,
                field_name,
            )
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )
            previous: datetime | None = None
            for value in values:
                validate_aware_datetime(
                    value,
                    field_name=field_name,
                )
                if previous is not None and value <= previous:
                    raise ValueError(
                        f"{field_name} must be strictly increasing"
                    )
                previous = value

        expected_status = self._expected_status()
        if self.status != expected_status:
            raise ValueError(
                "status does not match expected/missing counts"
            )

    def _expected_status(self) -> str:
        if self.expected_count == 0:
            return self.NO_EXPECTATION
        if self.missing_count == 0:
            return self.COMPLETE
        return self.GAPS

    @property
    def expected_coverage_fraction(self) -> float | None:
        if self.expected_count == 0:
            return None
        return (
            self.observed_expected_count
            / self.expected_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "expected_count": self.expected_count,
            "observed_expected_count": self.observed_expected_count,
            "missing_count": self.missing_count,
            "unexpected_observed_count": self.unexpected_observed_count,
            "expected_coverage_fraction": self.expected_coverage_fraction,
            "missing_timestamps": [
                value.isoformat()
                for value in self.missing_timestamps
            ],
            "unexpected_observed_timestamps": [
                value.isoformat()
                for value in self.unexpected_observed_timestamps
            ],
        }


class HistoricalArchiveGapAssessmentService:
    """Compare exact expected and observed GENERATED_AT timestamps."""

    def assess(
        self,
        *,
        expected_timestamps: Iterable[datetime],
        observed_timestamps: Iterable[datetime],
    ) -> HistoricalArchiveGapAssessment:
        expected = self._normalize(
            expected_timestamps,
            field_name="expected_timestamps",
        )
        observed = self._normalize(
            observed_timestamps,
            field_name="observed_timestamps",
        )

        expected_set = set(
            expected
        )
        observed_set = set(
            observed
        )

        missing = tuple(
            sorted(
                expected_set
                - observed_set
            )
        )
        observed_expected = (
            expected_set
            & observed_set
        )
        unexpected = tuple(
            sorted(
                observed_set
                - expected_set
            )
        )

        if not expected:
            status = HistoricalArchiveGapAssessment.NO_EXPECTATION
        elif missing:
            status = HistoricalArchiveGapAssessment.GAPS
        else:
            status = HistoricalArchiveGapAssessment.COMPLETE

        return HistoricalArchiveGapAssessment(
            status=status,
            expected_count=len(
                expected
            ),
            observed_expected_count=len(
                observed_expected
            ),
            missing_count=len(
                missing
            ),
            unexpected_observed_count=len(
                unexpected
            ),
            missing_timestamps=missing,
            unexpected_observed_timestamps=unexpected,
        )

    @staticmethod
    def _normalize(
        values: Iterable[datetime],
        *,
        field_name: str,
    ) -> tuple[datetime, ...]:
        materialized = tuple(
            values
        )

        normalized: list[datetime] = []
        seen: set[datetime] = set()

        for value in materialized:
            if not isinstance(
                value,
                datetime,
            ):
                raise TypeError(
                    f"{field_name} must contain only datetime values"
                )
            validate_aware_datetime(
                value,
                field_name=field_name,
            )
            if value in seen:
                continue
            seen.add(
                value
            )
            normalized.append(
                value
            )

        return tuple(
            sorted(
                normalized
            )
        )
