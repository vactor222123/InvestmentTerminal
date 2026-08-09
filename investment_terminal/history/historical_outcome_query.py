"""
Read-only in-memory filtering for methodology-aware historical outcomes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeQuery:
    """Optional filters over produced methodology-aware observations."""

    recommendation_key: str | None = None
    symbol: str | None = None
    action: str | None = None
    status: str | None = None
    window_kind: str | None = None
    window_value: int | None = None
    methodology_id: str | None = None
    methodology_version: int | None = None
    origin_from: datetime | None = None
    origin_to: datetime | None = None

    def __post_init__(self) -> None:
        text_fields = (
            "recommendation_key",
            "symbol",
            "action",
            "status",
            "window_kind",
            "methodology_id",
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

        if self.window_value is not None:
            if isinstance(self.window_value, bool) or not isinstance(
                self.window_value,
                int,
            ):
                raise TypeError("window_value must be an integer or None")
            if self.window_value <= 0:
                raise ValueError("window_value must be greater than zero")

        if self.methodology_version is not None:
            if isinstance(self.methodology_version, bool) or not isinstance(
                self.methodology_version,
                int,
            ):
                raise TypeError(
                    "methodology_version must be an integer or None"
                )
            if self.methodology_version <= 0:
                raise ValueError(
                    "methodology_version must be greater than zero"
                )

        if self.origin_from is not None:
            validate_aware_datetime(
                self.origin_from,
                field_name="origin_from",
            )
        if self.origin_to is not None:
            validate_aware_datetime(
                self.origin_to,
                field_name="origin_to",
            )
        if (
            self.origin_from is not None
            and self.origin_to is not None
            and self.origin_from > self.origin_to
        ):
            raise ValueError(
                "origin_from must not be later than origin_to"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_key": self.recommendation_key,
            "symbol": self.symbol,
            "action": self.action,
            "status": self.status,
            "window_kind": self.window_kind,
            "window_value": self.window_value,
            "methodology_id": self.methodology_id,
            "methodology_version": self.methodology_version,
            "origin_from": (
                None if self.origin_from is None else self.origin_from.isoformat()
            ),
            "origin_to": (
                None if self.origin_to is None else self.origin_to.isoformat()
            ),
        }


class HistoricalOutcomeQueryService:
    """Deterministically filter already-produced observations in memory."""

    def filter(
        self,
        results: Iterable[HistoricalMethodologyAwareObservationResult],
        *,
        query: HistoricalOutcomeQuery,
    ) -> tuple[HistoricalMethodologyAwareObservationResult, ...]:
        if not isinstance(query, HistoricalOutcomeQuery):
            raise TypeError("query must be a HistoricalOutcomeQuery")

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

        return tuple(
            result
            for result in materialized
            if self._matches(result, query)
        )

    @staticmethod
    def _matches(
        result: HistoricalMethodologyAwareObservationResult,
        query: HistoricalOutcomeQuery,
    ) -> bool:
        observation = result.observation
        methodology = result.methodology
        window = observation.window

        if (
            query.recommendation_key is not None
            and observation.recommendation_key != query.recommendation_key
        ):
            return False
        if query.symbol is not None and observation.symbol != query.symbol:
            return False
        if query.action is not None and observation.action != query.action:
            return False
        if query.status is not None and observation.status != query.status:
            return False
        if query.window_kind is not None and window.kind != query.window_kind:
            return False
        if query.window_value is not None and window.value != query.window_value:
            return False
        if (
            query.methodology_id is not None
            and methodology.methodology_id != query.methodology_id
        ):
            return False
        if (
            query.methodology_version is not None
            and methodology.version != query.methodology_version
        ):
            return False
        if (
            query.origin_from is not None
            and observation.origin_at < query.origin_from
        ):
            return False
        if (
            query.origin_to is not None
            and observation.origin_at > query.origin_to
        ):
            return False

        return True
