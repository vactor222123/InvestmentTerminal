"""
Adapt a portfolio-ranking export into review-package sections.
"""

from copy import deepcopy
from typing import Any


class PortfolioAnalysisReviewAdapter:
    """
    Convert the existing stock-analysis export into unified sections.

    The adapter accepts the current compact exporter and remains tolerant
    of older field names. Original source data is preserved so that no
    analytical detail is silently discarded.
    """

    FRESHNESS_KEYS = (
        "market_data",
        "market_data_freshness",
        "freshness",
    )
    UNIVERSE_KEYS = (
        "universe",
        "universe_summary",
    )
    RANKING_KEYS = (
        "ranking",
        "portfolio_ranking",
    )
    RECOMMENDATION_KEYS = (
        "recommendations",
        "portfolio_recommendations",
    )
    THESIS_KEYS = (
        "theses",
        "investment_theses",
    )
    ALLOCATION_KEYS = (
        "allocation",
        "portfolio_allocation",
    )

    def adapt(
        self,
        payload: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "payload must be a dictionary"
            )

        freshness = self._first_value(
            payload,
            self.FRESHNESS_KEYS,
            default={},
        )
        universe = self._first_value(
            payload,
            self.UNIVERSE_KEYS,
            default={},
        )
        ranking = self._first_value(
            payload,
            self.RANKING_KEYS,
            default={},
        )
        recommendations = self._first_value(
            payload,
            self.RECOMMENDATION_KEYS,
            default={},
        )
        theses = self._first_value(
            payload,
            self.THESIS_KEYS,
            default={},
        )
        allocation = self._first_value(
            payload,
            self.ALLOCATION_KEYS,
            default={},
        )

        recommendation_items = self._items(
            recommendations
        )
        opportunity_items = tuple(
            item
            for item in recommendation_items
            if self._recommendation_label(
                item
            )
            in {
                "BUY",
                "ACCUMULATE",
            }
        )

        return {
            "data_freshness": {
                "status": (
                    "CONNECTED"
                    if freshness
                    else "MISSING_IN_SOURCE"
                ),
                "source": deepcopy(
                    freshness
                ),
            },
            "market_analysis": {
                "status": "CONNECTED",
                "universe": deepcopy(
                    universe
                ),
                "ranking": deepcopy(
                    ranking
                ),
                "source_schema_version": payload.get(
                    "schema_version"
                ),
                "source_generated_at": payload.get(
                    "generated_at"
                ),
            },
            "stock_analysis": {
                "status": "CONNECTED",
                "ranking": deepcopy(
                    ranking
                ),
                "recommendations": deepcopy(
                    recommendations
                ),
                "investment_theses": deepcopy(
                    theses
                ),
            },
            "opportunities": {
                "status": "CONNECTED",
                "selection_rule": (
                    "Recommendations labelled BUY or ACCUMULATE."
                ),
                "items": [
                    deepcopy(item)
                    for item in opportunity_items
                ],
            },
            "machine_recommendations": {
                "status": "CONNECTED",
                "recommendations": deepcopy(
                    recommendations
                ),
                "allocation": deepcopy(
                    allocation
                ),
            },
            "source_package": deepcopy(
                payload
            ),
        }

    @staticmethod
    def _first_value(
        payload: dict[str, Any],
        keys: tuple[str, ...],
        *,
        default: Any,
    ) -> Any:
        for key in keys:
            if key in payload:
                return payload[key]

        sections = payload.get(
            "sections"
        )

        if isinstance(
            sections,
            dict,
        ):
            for key in keys:
                if key in sections:
                    return sections[key]

        return default

    @staticmethod
    def _items(
        value: Any,
    ) -> tuple[dict[str, Any], ...]:
        if isinstance(
            value,
            list,
        ):
            return tuple(
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            )

        if isinstance(
            value,
            dict,
        ):
            for key in (
                "items",
                "recommendations",
                "candidates",
            ):
                items = value.get(
                    key
                )

                if isinstance(
                    items,
                    list,
                ):
                    return tuple(
                        item
                        for item in items
                        if isinstance(
                            item,
                            dict,
                        )
                    )

        return ()

    @staticmethod
    def _recommendation_label(
        item: dict[str, Any],
    ) -> str:
        for key in (
            "recommendation",
            "label",
            "action",
        ):
            value = item.get(
                key
            )

            if isinstance(
                value,
                str,
            ):
                return value.strip().upper()

        return ""