"""
Canonical population-frame contract for historical outcome research.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any, ClassVar

from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchPopulationFrame:
    """
    Explicit denominator before and after research selection.

    The frame records how many methodology-aware archived observations were
    available to the selection boundary and how many remained after selection.
    It does not claim that the source observations represent a broader market.
    """

    frame_basis: str
    source_observation_count: int
    selected_candidate_count: int
    excluded_by_selection_count: int
    selection_fraction: float

    ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS: ClassVar[str] = (
        "ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS"
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "frame_basis",
            normalize_required_text(
                self.frame_basis,
                field_name="frame_basis",
                uppercase=True,
            ),
        )
        if (
            self.frame_basis
            != self.ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS
        ):
            raise ValueError(
                f"unsupported frame_basis: {self.frame_basis}"
            )

        for field_name in (
            "source_observation_count",
            "selected_candidate_count",
            "excluded_by_selection_count",
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

        if self.selected_candidate_count > self.source_observation_count:
            raise ValueError(
                "selected_candidate_count must not exceed "
                "source_observation_count"
            )

        expected_excluded = (
            self.source_observation_count
            - self.selected_candidate_count
        )
        if self.excluded_by_selection_count != expected_excluded:
            raise ValueError(
                "excluded_by_selection_count must equal "
                "source_observation_count - selected_candidate_count"
            )

        if (
            isinstance(self.selection_fraction, bool)
            or not isinstance(
                self.selection_fraction,
                (int, float),
            )
            or not isfinite(
                float(
                    self.selection_fraction
                )
            )
            or not 0.0
            <= float(
                self.selection_fraction
            )
            <= 1.0
        ):
            raise ValueError(
                "selection_fraction must be a finite number from 0 to 1"
            )

        expected_fraction = (
            0.0
            if self.source_observation_count == 0
            else (
                self.selected_candidate_count
                / self.source_observation_count
            )
        )
        if abs(
            float(
                self.selection_fraction
            )
            - expected_fraction
        ) > 1e-12:
            raise ValueError(
                "selection_fraction must equal "
                "selected_candidate_count / source_observation_count"
            )

        object.__setattr__(
            self,
            "selection_fraction",
            float(
                self.selection_fraction
            ),
        )

    @property
    def selection_applied(self) -> bool:
        return (
            self.selected_candidate_count
            != self.source_observation_count
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_basis": self.frame_basis,
            "source_observation_count": self.source_observation_count,
            "selected_candidate_count": self.selected_candidate_count,
            "excluded_by_selection_count": (
                self.excluded_by_selection_count
            ),
            "selection_fraction": self.selection_fraction,
            "selection_applied": self.selection_applied,
        }


class HistoricalOutcomeResearchPopulationFrameService:
    """Build one deterministic research population frame."""

    def build(
        self,
        *,
        source_observation_count: int,
        selected_candidate_count: int,
    ) -> HistoricalOutcomeResearchPopulationFrame:
        for field_name, value in (
            (
                "source_observation_count",
                source_observation_count,
            ),
            (
                "selected_candidate_count",
                selected_candidate_count,
            ),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if selected_candidate_count > source_observation_count:
            raise ValueError(
                "selected_candidate_count must not exceed "
                "source_observation_count"
            )

        excluded = (
            source_observation_count
            - selected_candidate_count
        )

        return HistoricalOutcomeResearchPopulationFrame(
            frame_basis=(
                HistoricalOutcomeResearchPopulationFrame
                .ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS
            ),
            source_observation_count=source_observation_count,
            selected_candidate_count=selected_candidate_count,
            excluded_by_selection_count=excluded,
            selection_fraction=(
                0.0
                if source_observation_count == 0
                else (
                    selected_candidate_count
                    / source_observation_count
                )
            ),
        )
