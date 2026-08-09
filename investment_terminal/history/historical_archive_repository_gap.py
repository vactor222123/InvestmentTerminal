"""
Repository-backed composition for historical archive continuity assessment.
"""

from datetime import datetime

from investment_terminal.history.historical_archive_cadence import (
    HistoricalArchiveCadencePolicy,
)
from investment_terminal.history.historical_archive_expected_timestamps import (
    HistoricalArchiveExpectedTimestampService,
)
from investment_terminal.history.historical_archive_gap_assessment import (
    HistoricalArchiveGapAssessment,
    HistoricalArchiveGapAssessmentService,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


class HistoricalArchiveRepositoryGapService:
    """
    Compose repository observations with cadence generation and gap assessment.

    This service owns no cadence math and no gap-classification logic.
    """

    def __init__(
        self,
        *,
        snapshot_repository: HistoricalSnapshotRepository,
        expected_timestamp_service: (
            HistoricalArchiveExpectedTimestampService | None
        ) = None,
        gap_assessment_service: (
            HistoricalArchiveGapAssessmentService | None
        ) = None,
    ) -> None:
        if not isinstance(
            snapshot_repository,
            HistoricalSnapshotRepository,
        ):
            raise TypeError(
                "snapshot_repository must be a HistoricalSnapshotRepository"
            )

        self._snapshot_repository = snapshot_repository
        self._expected_timestamp_service = (
            expected_timestamp_service
            if expected_timestamp_service is not None
            else HistoricalArchiveExpectedTimestampService()
        )
        self._gap_assessment_service = (
            gap_assessment_service
            if gap_assessment_service is not None
            else HistoricalArchiveGapAssessmentService()
        )

    def assess(
        self,
        *,
        policy: HistoricalArchiveCadencePolicy,
        start_at: datetime,
        end_at: datetime,
    ) -> HistoricalArchiveGapAssessment:
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

        expected = self._expected_timestamp_service.generate(
            policy=policy,
            start_at=start_at,
            end_at=end_at,
        )

        snapshots = self._snapshot_repository.find_generated_between(
            start=start_at,
            end=end_at,
        )
        observed = tuple(
            snapshot.generated_at
            for snapshot in snapshots
        )

        return self._gap_assessment_service.assess(
            expected_timestamps=expected,
            observed_timestamps=observed,
        )
