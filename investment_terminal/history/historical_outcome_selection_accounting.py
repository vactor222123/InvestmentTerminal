"""
Selection-reason accounting for historical outcome research queries.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Iterable

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
    HistoricalOutcomeQueryService,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeSelectionReasonCount:
    """Count of source observations that fail one active query predicate."""

    reason: str
    count: int

    RECOMMENDATION_KEY: ClassVar[str] = "RECOMMENDATION_KEY"
    SYMBOL: ClassVar[str] = "SYMBOL"
    ACTION: ClassVar[str] = "ACTION"
    STATUS: ClassVar[str] = "STATUS"
    WINDOW_KIND: ClassVar[str] = "WINDOW_KIND"
    WINDOW_VALUE: ClassVar[str] = "WINDOW_VALUE"
    METHODOLOGY_ID: ClassVar[str] = "METHODOLOGY_ID"
    METHODOLOGY_VERSION: ClassVar[str] = "METHODOLOGY_VERSION"
    ORIGIN_FROM: ClassVar[str] = "ORIGIN_FROM"
    ORIGIN_TO: ClassVar[str] = "ORIGIN_TO"

    KNOWN_REASONS: ClassVar[tuple[str, ...]] = (
        RECOMMENDATION_KEY,
        SYMBOL,
        ACTION,
        STATUS,
        WINDOW_KIND,
        WINDOW_VALUE,
        METHODOLOGY_ID,
        METHODOLOGY_VERSION,
        ORIGIN_FROM,
        ORIGIN_TO,
    )

    def __post_init__(self) -> None:
        if self.reason not in self.KNOWN_REASONS:
            raise ValueError(
                f"unsupported selection reason: {self.reason}"
            )
        if (
            isinstance(self.count, bool)
            or not isinstance(self.count, int)
            or self.count < 0
        ):
            raise ValueError(
                "count must be a non-negative integer"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "count": self.count,
        }


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeSelectionAccounting:
    """
    Explain source-to-selected reduction without pretending reasons are exclusive.

    One excluded observation can fail multiple active predicates. Therefore
    reason counts are diagnostic marginals and are not required to sum to the
    excluded observation count.
    """

    source_observation_count: int
    selected_candidate_count: int
    excluded_observation_count: int
    reason_counts: tuple[HistoricalOutcomeSelectionReasonCount, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "source_observation_count",
            "selected_candidate_count",
            "excluded_observation_count",
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

        if self.selected_candidate_count > self.source_observation_count:
            raise ValueError(
                "selected_candidate_count must not exceed "
                "source_observation_count"
            )
        if self.excluded_observation_count != (
            self.source_observation_count
            - self.selected_candidate_count
        ):
            raise ValueError(
                "excluded_observation_count must equal "
                "source_observation_count - selected_candidate_count"
            )

        if not isinstance(self.reason_counts, tuple):
            raise TypeError(
                "reason_counts must be a tuple"
            )
        seen: set[str] = set()
        for item in self.reason_counts:
            if not isinstance(
                item,
                HistoricalOutcomeSelectionReasonCount,
            ):
                raise TypeError(
                    "reason_counts must contain only "
                    "HistoricalOutcomeSelectionReasonCount values"
                )
            if item.reason in seen:
                raise ValueError(
                    f"duplicate selection reason: {item.reason}"
                )
            seen.add(item.reason)

    @property
    def total_reason_failures(self) -> int:
        return sum(
            item.count
            for item in self.reason_counts
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_observation_count": self.source_observation_count,
            "selected_candidate_count": self.selected_candidate_count,
            "excluded_observation_count": self.excluded_observation_count,
            "reason_counts": [
                item.to_dict()
                for item in self.reason_counts
            ],
            "total_reason_failures": self.total_reason_failures,
            "reason_counts_are_exclusive": False,
        }


class HistoricalOutcomeSelectionAccountingService:
    """Apply existing query semantics and explain rejected source observations."""

    _REASON_ORDER = HistoricalOutcomeSelectionReasonCount.KNOWN_REASONS

    def __init__(
        self,
        *,
        query_service: HistoricalOutcomeQueryService | None = None,
    ) -> None:
        self._query_service = (
            query_service
            if query_service is not None
            else HistoricalOutcomeQueryService()
        )

    def assess(
        self,
        results: Iterable[HistoricalMethodologyAwareObservationResult],
        *,
        query: HistoricalOutcomeQuery,
    ) -> HistoricalOutcomeSelectionAccounting:
        if not isinstance(
            query,
            HistoricalOutcomeQuery,
        ):
            raise TypeError(
                "query must be a HistoricalOutcomeQuery"
            )

        materialized = tuple(
            results
        )
        for result in materialized:
            if not isinstance(
                result,
                HistoricalMethodologyAwareObservationResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "HistoricalMethodologyAwareObservationResult"
                )

        selected = self._query_service.filter(
            materialized,
            query=query,
        )

        counts = {
            reason: 0
            for reason in self._REASON_ORDER
        }
        for result in materialized:
            for reason in self._failed_reasons(
                result,
                query,
            ):
                counts[
                    reason
                ] += 1

        return HistoricalOutcomeSelectionAccounting(
            source_observation_count=len(
                materialized
            ),
            selected_candidate_count=len(
                selected
            ),
            excluded_observation_count=(
                len(
                    materialized
                )
                - len(
                    selected
                )
            ),
            reason_counts=tuple(
                HistoricalOutcomeSelectionReasonCount(
                    reason=reason,
                    count=counts[
                        reason
                    ],
                )
                for reason in self._REASON_ORDER
                if counts[
                    reason
                ] > 0
            ),
        )

    @staticmethod
    def _failed_reasons(
        result: HistoricalMethodologyAwareObservationResult,
        query: HistoricalOutcomeQuery,
    ) -> tuple[str, ...]:
        observation = result.observation
        methodology = result.methodology
        window = observation.window
        reasons: list[str] = []

        checks = (
            (
                HistoricalOutcomeSelectionReasonCount.RECOMMENDATION_KEY,
                query.recommendation_key is not None
                and observation.recommendation_key
                != query.recommendation_key,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.SYMBOL,
                query.symbol is not None
                and observation.symbol
                != query.symbol,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.ACTION,
                query.action is not None
                and observation.action
                != query.action,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.STATUS,
                query.status is not None
                and observation.status
                != query.status,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.WINDOW_KIND,
                query.window_kind is not None
                and window.kind
                != query.window_kind,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.WINDOW_VALUE,
                query.window_value is not None
                and window.value
                != query.window_value,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.METHODOLOGY_ID,
                query.methodology_id is not None
                and methodology.methodology_id
                != query.methodology_id,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.METHODOLOGY_VERSION,
                query.methodology_version is not None
                and methodology.version
                != query.methodology_version,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.ORIGIN_FROM,
                query.origin_from is not None
                and observation.origin_at
                < query.origin_from,
            ),
            (
                HistoricalOutcomeSelectionReasonCount.ORIGIN_TO,
                query.origin_to is not None
                and observation.origin_at
                > query.origin_to,
            ),
        )

        for reason, failed in checks:
            if failed:
                reasons.append(
                    reason
                )

        return tuple(
            reasons
        )
