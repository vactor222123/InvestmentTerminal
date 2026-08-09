"""
Import-lifecycle quality assessment for historical research source observations.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Iterable

from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeSourceImportQualityAssessment:
    """Summarize import lifecycle quality for unique source snapshots."""

    status: str
    source_observation_count: int
    unique_snapshot_count: int
    imported_snapshot_count: int
    non_imported_snapshot_count: int
    missing_state_snapshot_count: int
    status_counts: tuple[tuple[str, int], ...]
    warning: str | None = None

    COMPLETE: ClassVar[str] = "COMPLETE"
    PARTIAL: ClassVar[str] = "PARTIAL"
    UNKNOWN: ClassVar[str] = "UNKNOWN"

    def __post_init__(self) -> None:
        if self.status not in {
            self.COMPLETE,
            self.PARTIAL,
            self.UNKNOWN,
        }:
            raise ValueError(
                f"unsupported source import quality status: {self.status}"
            )

        for field_name in (
            "source_observation_count",
            "unique_snapshot_count",
            "imported_snapshot_count",
            "non_imported_snapshot_count",
            "missing_state_snapshot_count",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            self.imported_snapshot_count
            + self.non_imported_snapshot_count
            + self.missing_state_snapshot_count
            != self.unique_snapshot_count
        ):
            raise ValueError(
                "snapshot quality counts must sum to unique_snapshot_count"
            )

        if not isinstance(self.status_counts, tuple):
            raise TypeError(
                "status_counts must be a tuple"
            )

        seen: set[str] = set()
        counted = 0
        for item in self.status_counts:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "status_counts must contain (status, count) tuples"
                )
            state_status, count = item
            if state_status not in HistoricalImportState.SUPPORTED_STATUSES:
                raise ValueError(
                    f"unsupported import state status: {state_status}"
                )
            if state_status in seen:
                raise ValueError(
                    f"duplicate import state status: {state_status}"
                )
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
            ):
                raise ValueError(
                    "status count must be a positive integer"
                )
            seen.add(state_status)
            counted += count

        if counted + self.missing_state_snapshot_count != self.unique_snapshot_count:
            raise ValueError(
                "status_counts plus missing states must cover unique snapshots"
            )

        expected = self._expected_status()
        if self.status != expected:
            raise ValueError(
                "status does not match source import lifecycle quality"
            )

        if self.warning is not None and (
            not isinstance(self.warning, str)
            or not self.warning.strip()
        ):
            raise ValueError(
                "warning must be a non-empty string or None"
            )

    def _expected_status(self) -> str:
        if self.unique_snapshot_count == 0:
            return self.UNKNOWN
        if (
            self.imported_snapshot_count == self.unique_snapshot_count
            and self.non_imported_snapshot_count == 0
            and self.missing_state_snapshot_count == 0
        ):
            return self.COMPLETE
        return self.PARTIAL

    @property
    def imported_fraction(self) -> float | None:
        if self.unique_snapshot_count == 0:
            return None
        return (
            self.imported_snapshot_count
            / self.unique_snapshot_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_observation_count": self.source_observation_count,
            "unique_snapshot_count": self.unique_snapshot_count,
            "imported_snapshot_count": self.imported_snapshot_count,
            "non_imported_snapshot_count": self.non_imported_snapshot_count,
            "missing_state_snapshot_count": self.missing_state_snapshot_count,
            "imported_fraction": self.imported_fraction,
            "status_counts": {
                status: count
                for status, count in self.status_counts
            },
            "warning": self.warning,
        }


class HistoricalOutcomeSourceImportQualityService:
    """
    Assess whether source observations originate from fully imported snapshots.

    Assessment is snapshot-based rather than observation-based so multiple
    observations from one snapshot do not inflate lifecycle quality counts.
    """

    _STATUS_ORDER = HistoricalImportState.SUPPORTED_STATUSES

    def __init__(
        self,
        repository: HistoricalImportStateRepository,
    ) -> None:
        if not isinstance(
            repository,
            HistoricalImportStateRepository,
        ):
            raise TypeError(
                "repository must be a HistoricalImportStateRepository"
            )
        self.repository = repository

    def assess(
        self,
        results: Iterable[HistoricalMethodologyAwareObservationResult],
    ) -> HistoricalOutcomeSourceImportQualityAssessment:
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

        snapshot_ids = tuple(
            dict.fromkeys(
                result.observation.origin_snapshot_id
                for result in materialized
            )
        )

        counts = {
            status: 0
            for status in self._STATUS_ORDER
        }
        missing = 0

        for snapshot_id in snapshot_ids:
            state = self.repository.get(
                snapshot_id
            )
            if state is None:
                missing += 1
                continue
            counts[state.status] += 1

        imported = counts["IMPORTED"]
        non_imported = (
            len(snapshot_ids)
            - imported
            - missing
        )

        if not snapshot_ids:
            status = HistoricalOutcomeSourceImportQualityAssessment.UNKNOWN
            warning = (
                "Source import quality is unknown because the research source "
                "contains no snapshots"
            )
        elif imported == len(snapshot_ids):
            status = HistoricalOutcomeSourceImportQualityAssessment.COMPLETE
            warning = None
        else:
            status = HistoricalOutcomeSourceImportQualityAssessment.PARTIAL
            warning = (
                "Research source includes snapshots without canonical IMPORTED "
                "lifecycle state"
            )

        return HistoricalOutcomeSourceImportQualityAssessment(
            status=status,
            source_observation_count=len(materialized),
            unique_snapshot_count=len(snapshot_ids),
            imported_snapshot_count=imported,
            non_imported_snapshot_count=non_imported,
            missing_state_snapshot_count=missing,
            status_counts=tuple(
                (
                    state_status,
                    counts[state_status],
                )
                for state_status in self._STATUS_ORDER
                if counts[state_status] > 0
            ),
            warning=warning,
        )
