"""Select and compare the previous compatible imported Review snapshot."""

from dataclasses import dataclass
from typing import Any

from investment_terminal.history.historical_comparison_models import (
    SnapshotComparison,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_snapshot_comparison_service import (
    HistoricalSnapshotComparisonService,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class IntegratedReviewComparisonResult:
    """Explicit comparison, first-run, or unavailable stage outcome."""

    current_snapshot_id: str
    status: str
    previous_snapshot_id: str | None = None
    comparison: SnapshotComparison | None = None
    reason: str | None = None

    SUPPORTED_STATUSES = (
        "COMPLETED",
        "FIRST_RUN",
        "UNAVAILABLE",
    )

    def __post_init__(self) -> None:
        current = HistoricalSnapshot._normalize_uuid(
            self.current_snapshot_id,
            field_name="current_snapshot_id",
        )
        object.__setattr__(
            self,
            "current_snapshot_id",
            current,
        )

        status = normalize_required_text(
            self.status,
            field_name="status",
            uppercase=True,
        )
        if status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(
                    self.SUPPORTED_STATUSES
                )
            )
        object.__setattr__(
            self,
            "status",
            status,
        )

        previous = (
            None
            if self.previous_snapshot_id is None
            else HistoricalSnapshot._normalize_uuid(
                self.previous_snapshot_id,
                field_name="previous_snapshot_id",
            )
        )
        object.__setattr__(
            self,
            "previous_snapshot_id",
            previous,
        )
        if previous == current:
            raise ValueError(
                "previous_snapshot_id must differ from current_snapshot_id"
            )

        if (
            self.comparison is not None
            and not isinstance(
                self.comparison,
                SnapshotComparison,
            )
        ):
            raise TypeError(
                "comparison must be a SnapshotComparison or None"
            )

        reason = normalize_optional_text(
            self.reason,
            field_name="reason",
        )
        object.__setattr__(
            self,
            "reason",
            reason,
        )

        if status == "COMPLETED":
            if previous is None or self.comparison is None:
                raise ValueError(
                    "COMPLETED requires previous_snapshot_id and comparison"
                )
            if reason is not None:
                raise ValueError(
                    "COMPLETED must not contain reason"
                )
            if (
                self.comparison.earlier_snapshot_id != previous
                or self.comparison.later_snapshot_id != current
                or self.comparison.compatibility_status == "INCOMPATIBLE"
            ):
                raise ValueError(
                    "comparison must describe a compatible previous/current pair"
                )
        else:
            if previous is not None or self.comparison is not None:
                raise ValueError(
                    f"{status} must not contain comparison artifacts"
                )
            if reason is None:
                raise ValueError(
                    f"{status} requires reason"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_snapshot_id": self.current_snapshot_id,
            "previous_snapshot_id": self.previous_snapshot_id,
            "status": self.status,
            "reason": self.reason,
            "comparison": (
                None
                if self.comparison is None
                else self.comparison.to_dict()
            ),
        }


class IntegratedReviewComparisonService:
    """Deterministically select the nearest comparable imported snapshot."""

    def __init__(
        self,
        *,
        snapshot_repository: HistoricalSnapshotRepository,
        import_state_repository: HistoricalImportStateRepository,
        comparison_service: HistoricalSnapshotComparisonService,
    ) -> None:
        dependencies = (
            (
                "snapshot_repository",
                snapshot_repository,
                HistoricalSnapshotRepository,
            ),
            (
                "import_state_repository",
                import_state_repository,
                HistoricalImportStateRepository,
            ),
            (
                "comparison_service",
                comparison_service,
                HistoricalSnapshotComparisonService,
            ),
        )
        for field_name, value, expected_type in dependencies:
            if not isinstance(
                value,
                expected_type,
            ):
                raise TypeError(
                    f"{field_name} must be a {expected_type.__name__}"
                )

        self.snapshot_repository = snapshot_repository
        self.import_state_repository = import_state_repository
        self.comparison_service = comparison_service

    def compare_previous(
        self,
        current_snapshot_id: str,
    ) -> IntegratedReviewComparisonResult:
        current = self.snapshot_repository.require(
            current_snapshot_id
        )
        current_state = self.import_state_repository.get(
            current.snapshot_id
        )
        if current_state is None or current_state.status != "IMPORTED":
            return IntegratedReviewComparisonResult(
                current_snapshot_id=current.snapshot_id,
                status="UNAVAILABLE",
                reason="Current snapshot does not have IMPORTED state",
            )

        snapshots = self.snapshot_repository.list_all()
        current_index = snapshots.index(
            current
        )
        earlier = snapshots[
            :current_index
        ]
        if not earlier:
            return IntegratedReviewComparisonResult(
                current_snapshot_id=current.snapshot_id,
                status="FIRST_RUN",
                reason="No earlier historical snapshot exists",
            )

        for candidate in reversed(
            earlier
        ):
            state = self.import_state_repository.get(
                candidate.snapshot_id
            )
            if state is None or state.status != "IMPORTED":
                continue

            comparison = self.comparison_service.compare(
                earlier_snapshot_id=candidate.snapshot_id,
                later_snapshot_id=current.snapshot_id,
            )
            if comparison.compatibility_status == "INCOMPATIBLE":
                continue

            return IntegratedReviewComparisonResult(
                current_snapshot_id=current.snapshot_id,
                previous_snapshot_id=candidate.snapshot_id,
                status="COMPLETED",
                comparison=comparison,
            )

        return IntegratedReviewComparisonResult(
            current_snapshot_id=current.snapshot_id,
            status="UNAVAILABLE",
            reason=(
                "No earlier compatible snapshot with IMPORTED state exists"
            ),
        )
