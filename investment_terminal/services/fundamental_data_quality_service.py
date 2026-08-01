"""
Fundamental data-quality calculations.
"""

from datetime import datetime, timezone

from investment_terminal.models.fundamental_snapshot import (
    FundamentalDataQuality,
    FundamentalSnapshot,
)


class FundamentalDataQualityService:
    """
    Calculate completeness metadata for fundamental data.
    """

    @staticmethod
    def evaluate(
        snapshot: FundamentalSnapshot,
        source: str,
        fetched_at: datetime | None = None,
    ) -> FundamentalDataQuality:
        """
        Evaluate which normalized metrics are available.
        """
        if not isinstance(snapshot, FundamentalSnapshot):
            raise TypeError(
                "snapshot must be a FundamentalSnapshot"
            )

        normalized_source = source.strip()

        if not normalized_source:
            raise ValueError(
                "source must be a non-empty string"
            )

        field_names = snapshot.metric_field_names()

        missing_fields = tuple(
            field_name
            for field_name in field_names
            if getattr(snapshot, field_name) is None
        )

        total_fields = len(field_names)
        available_fields = (
            total_fields - len(missing_fields)
        )

        completeness_percent = (
            available_fields / total_fields * 100.0
        )

        return FundamentalDataQuality(
            available_fields=available_fields,
            total_fields=total_fields,
            completeness_percent=round(
                completeness_percent,
                2,
            ),
            missing_fields=missing_fields,
            source=normalized_source,
            fetched_at=(
                fetched_at
                if fetched_at is not None
                else datetime.now(timezone.utc)
            ),
        )