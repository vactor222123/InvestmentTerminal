"""
Population metadata and selection-bias guardrails for outcome research.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchPopulationMetadata:
    """
    Explicit description of the observed research population.

    This model describes how the available archived observations were selected.
    It does not claim that the sample is representative of a broader market
    population or free from survivorship/selection bias.
    """

    selection_basis: str
    candidate_count: int
    requested_recommendation_key: str | None
    requested_symbol: str | None
    requested_action: str | None
    requested_status: str | None
    requested_window_kind: str | None
    requested_window_value: int | None
    requested_methodology_id: str | None
    requested_methodology_version: int | None
    origin_start: datetime | None
    origin_end: datetime | None
    prefiltered: bool
    warnings: tuple[str, ...]

    ARCHIVED_OBSERVATIONS: ClassVar[str] = "ARCHIVED_OBSERVATIONS"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "selection_basis",
            normalize_required_text(
                self.selection_basis,
                field_name="selection_basis",
                uppercase=True,
            ),
        )
        if self.selection_basis != self.ARCHIVED_OBSERVATIONS:
            raise ValueError(
                f"unsupported selection_basis: {self.selection_basis}"
            )

        if (
            isinstance(self.candidate_count, bool)
            or not isinstance(self.candidate_count, int)
            or self.candidate_count < 0
        ):
            raise ValueError(
                "candidate_count must be a non-negative integer"
            )

        text_fields = (
            "requested_recommendation_key",
            "requested_symbol",
            "requested_action",
            "requested_status",
            "requested_window_kind",
            "requested_methodology_id",
        )
        for field_name in text_fields:
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    normalize_required_text(
                        value,
                        field_name=field_name,
                        uppercase=True,
                    ),
                )

        for field_name in (
            "requested_window_value",
            "requested_methodology_version",
        ):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(
                    f"{field_name} must be a positive integer or None"
                )

        if self.origin_start is not None:
            validate_aware_datetime(
                self.origin_start,
                field_name="origin_start",
            )
        if self.origin_end is not None:
            validate_aware_datetime(
                self.origin_end,
                field_name="origin_end",
            )
        if (
            self.origin_start is not None
            and self.origin_end is not None
            and self.origin_start > self.origin_end
        ):
            raise ValueError(
                "origin_start must not be later than origin_end"
            )

        if not isinstance(self.prefiltered, bool):
            raise TypeError(
                "prefiltered must be a bool"
            )
        if not isinstance(self.warnings, tuple):
            raise TypeError(
                "warnings must be a tuple"
            )
        normalized_warnings = tuple(
            normalize_required_text(
                warning,
                field_name="warnings",
            )
            for warning in self.warnings
        )
        if not normalized_warnings:
            raise ValueError(
                "warnings must not be empty"
            )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_basis": self.selection_basis,
            "candidate_count": self.candidate_count,
            "requested_recommendation_key": self.requested_recommendation_key,
            "requested_symbol": self.requested_symbol,
            "requested_action": self.requested_action,
            "requested_status": self.requested_status,
            "requested_window_kind": self.requested_window_kind,
            "requested_window_value": self.requested_window_value,
            "requested_methodology_id": self.requested_methodology_id,
            "requested_methodology_version": (
                self.requested_methodology_version
            ),
            "origin_start": (
                None
                if self.origin_start is None
                else self.origin_start.isoformat()
            ),
            "origin_end": (
                None
                if self.origin_end is None
                else self.origin_end.isoformat()
            ),
            "prefiltered": self.prefiltered,
            "warnings": list(self.warnings),
        }


class HistoricalOutcomeResearchPopulationMetadataService:
    """Build deterministic population metadata from the actual query boundary."""

    BASE_WARNING = (
        "Population consists of historical recommendations archived by this "
        "system; it is not automatically an unbiased or representative market "
        "population"
    )
    PREFILTER_WARNING = (
        "Population was prefiltered before research aggregation; reported "
        "statistics apply only to the requested subset"
    )

    def build(
        self,
        *,
        query: HistoricalOutcomeQuery,
        candidate_count: int,
    ) -> HistoricalOutcomeResearchPopulationMetadata:
        if not isinstance(
            query,
            HistoricalOutcomeQuery,
        ):
            raise TypeError(
                "query must be a HistoricalOutcomeQuery"
            )
        if (
            isinstance(candidate_count, bool)
            or not isinstance(candidate_count, int)
            or candidate_count < 0
        ):
            raise ValueError(
                "candidate_count must be a non-negative integer"
            )

        prefiltered = any(
            value is not None
            for value in (
                query.recommendation_key,
                query.symbol,
                query.action,
                query.status,
                query.window_kind,
                query.window_value,
                query.methodology_id,
                query.methodology_version,
                query.origin_from,
                query.origin_to,
            )
        )

        warnings = (
            (
                self.BASE_WARNING,
                self.PREFILTER_WARNING,
            )
            if prefiltered
            else (
                self.BASE_WARNING,
            )
        )

        return HistoricalOutcomeResearchPopulationMetadata(
            selection_basis=(
                HistoricalOutcomeResearchPopulationMetadata
                .ARCHIVED_OBSERVATIONS
            ),
            candidate_count=candidate_count,
            requested_recommendation_key=query.recommendation_key,
            requested_symbol=query.symbol,
            requested_action=query.action,
            requested_status=query.status,
            requested_window_kind=query.window_kind,
            requested_window_value=query.window_value,
            requested_methodology_id=query.methodology_id,
            requested_methodology_version=query.methodology_version,
            origin_start=query.origin_from,
            origin_end=query.origin_to,
            prefiltered=prefiltered,
            warnings=warnings,
        )
