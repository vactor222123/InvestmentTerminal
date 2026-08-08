"""
Canonical read model for snapshot comparison prerequisites.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalComparisonFacts:
    """
    Immutable normalized facts used to decide snapshot comparability.

    These values describe the structured History projection only. They do not
    determine compatibility and they do not replace the immutable archive.
    """

    snapshot_id: str
    portfolio_summary_present: bool
    portfolio_name: str | None
    base_currency: str | None
    source_status: str | None
    holdings_count: int
    recommendations_count: int
    deployment_count: int
    timeline_event_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )

        if not isinstance(
            self.portfolio_summary_present,
            bool,
        ):
            raise TypeError(
                "portfolio_summary_present must be a boolean"
            )

        for field_name in (
            "portfolio_name",
            "base_currency",
            "source_status",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name=field_name,
                ),
            )

        if not self.portfolio_summary_present:
            for field_name in (
                "portfolio_name",
                "base_currency",
                "source_status",
            ):
                if getattr(
                    self,
                    field_name,
                ) is not None:
                    raise ValueError(
                        f"{field_name} must be None when "
                        "portfolio_summary_present is False"
                    )

        for field_name in (
            "holdings_count",
            "recommendations_count",
            "deployment_count",
            "timeline_event_count",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(
                    value,
                    int,
                )
                or isinstance(
                    value,
                    bool,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

    @property
    def has_any_detail_rows(
        self,
    ) -> bool:
        return (
            self.portfolio_summary_present
            or self.holdings_count > 0
            or self.recommendations_count > 0
            or self.deployment_count > 0
            or self.timeline_event_count > 0
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "portfolio_summary_present": (
                self.portfolio_summary_present
            ),
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "source_status": self.source_status,
            "holdings_count": self.holdings_count,
            "recommendations_count": (
                self.recommendations_count
            ),
            "deployment_count": self.deployment_count,
            "timeline_event_count": (
                self.timeline_event_count
            ),
            "has_any_detail_rows": (
                self.has_any_detail_rows
            ),
        }
