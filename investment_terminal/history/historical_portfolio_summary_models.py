"""
Canonical read model for one normalized historical portfolio summary.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalPortfolioSummary:
    """Immutable normalized portfolio-summary projection for one snapshot."""

    snapshot_id: str
    portfolio_name: str
    base_currency: str
    total_value: float
    invested_value: float
    cash_value: float
    monthly_contribution: float
    source_status: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "portfolio_name",
            normalize_required_text(
                self.portfolio_name,
                field_name="portfolio_name",
            ),
        )
        object.__setattr__(
            self,
            "base_currency",
            normalize_required_text(
                self.base_currency,
                field_name="base_currency",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "source_status",
            normalize_required_text(
                self.source_status,
                field_name="source_status",
                uppercase=True,
            ),
        )

        for field_name in (
            "total_value",
            "invested_value",
            "cash_value",
            "monthly_contribution",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    (
                        int,
                        float,
                    ),
                )
                or not isfinite(
                    float(
                        value
                    )
                )
                or float(
                    value
                ) < 0.0
            ):
                raise ValueError(
                    f"{field_name} must be a finite non-negative number"
                )

            object.__setattr__(
                self,
                field_name,
                float(
                    value
                ),
            )

        if abs(
            self.invested_value
            + self.cash_value
            - self.total_value
        ) > 0.01:
            raise ValueError(
                "invested_value and cash_value must equal total_value"
            )

    @property
    def cash_weight(
        self,
    ) -> float | None:
        if self.total_value == 0.0:
            return None

        return (
            self.cash_value
            / self.total_value
        )

    @property
    def invested_weight(
        self,
    ) -> float | None:
        if self.total_value == 0.0:
            return None

        return (
            self.invested_value
            / self.total_value
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "total_value": self.total_value,
            "invested_value": self.invested_value,
            "cash_value": self.cash_value,
            "monthly_contribution": self.monthly_contribution,
            "source_status": self.source_status,
            "cash_weight": self.cash_weight,
            "invested_weight": self.invested_weight,
        }
