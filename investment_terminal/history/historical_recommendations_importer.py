"""
Import machine recommendations from a verified Review Package into SQLite.
"""

import json
import sqlite3
from contextlib import nullcontext
from math import isfinite
from numbers import Real
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalRecommendationsImporter:
    """
    Normalize machine recommendations into structured historical records.

    The importer accepts the recommendation shapes already supported by the
    Review Package adapter:

    - a direct list;
    - a dictionary containing items;
    - a dictionary containing recommendations;
    - a dictionary containing candidates.

    The complete original recommendation is preserved in payload_json.
    """

    ITEM_KEYS = (
        "items",
        "recommendations",
        "candidates",
    )
    ACTION_KEYS = (
        "recommendation",
        "label",
        "action",
    )
    SYMBOL_KEYS = (
        "symbol",
        "ticker",
        "instrument",
    )
    SCORE_KEYS = (
        "score",
        "ranking_score",
        "total_score",
    )
    CONFIDENCE_KEYS = (
        "confidence",
        "confidence_score",
    )
    RATIONALE_KEYS = (
        "rationale",
        "reason",
        "summary",
        "thesis",
    )

    def __init__(
        self,
        store: HistoricalSQLiteStore,
    ) -> None:
        if not isinstance(
            store,
            HistoricalSQLiteStore,
        ):
            raise TypeError(
                "store must be a HistoricalSQLiteStore"
            )

        self.store = store

    def import_recommendations(
        self,
        *,
        snapshot: HistoricalSnapshot,
        payload: dict[str, Any],
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """Insert all available machine recommendations for one snapshot."""
        if not isinstance(
            snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )

        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "payload must be a dictionary"
            )

        rows = self._extract_rows(
            payload
        )

        if connection is None:
            self.store.initialize()

        try:
            with (nullcontext(connection) if connection is not None else self.store.connect()) as connection:
                connection.executemany(
                    """
                    INSERT INTO recommendations (
                        snapshot_id,
                        recommendation_key,
                        symbol,
                        action,
                        score,
                        confidence,
                        rationale,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            snapshot.snapshot_id,
                            row["recommendation_key"],
                            row["symbol"],
                            row["action"],
                            row["score"],
                            row["confidence"],
                            row["rationale"],
                            row["payload_json"],
                        )
                        for row in rows
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical recommendations could not be imported. "
                "The snapshot may be missing or recommendations "
                "may already exist."
            ) from exc

        return len(
            rows
        )

    @classmethod
    def _extract_rows(
        cls,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], ...]:
        sections = payload.get(
            "sections"
        )

        if not isinstance(
            sections,
            dict,
        ):
            raise ValueError(
                "Review Package sections must be a dictionary"
            )

        machine_section = sections.get(
            "machine_recommendations"
        )

        if not isinstance(
            machine_section,
            dict,
        ):
            raise ValueError(
                "machine_recommendations section must be a dictionary"
            )

        status = machine_section.get(
            "status"
        )

        if (
            isinstance(status, str)
            and status.strip().upper()
            in {
                "NOT_CONNECTED",
                "MISSING_IN_SOURCE",
            }
        ):
            return ()

        raw_recommendations = machine_section.get(
            "recommendations",
            [],
        )
        items = cls._items(
            raw_recommendations
        )

        rows: list[
            dict[str, Any]
        ] = []
        seen_keys: set[str] = set()

        for index, item in enumerate(
            items
        ):
            row = cls._normalize_item(
                item=item,
                index=index,
            )

            if row["recommendation_key"] in seen_keys:
                raise ValueError(
                    "recommendations must contain unique keys"
                )

            seen_keys.add(
                row["recommendation_key"]
            )
            rows.append(
                row
            )

        return tuple(
            rows
        )

    @classmethod
    def _normalize_item(
        cls,
        *,
        item: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        symbol = cls._first_text(
            item,
            cls.SYMBOL_KEYS,
        )
        action = cls._first_text(
            item,
            cls.ACTION_KEYS,
        )

        normalized_symbol = (
            symbol.upper()
            if symbol is not None
            else None
        )
        normalized_action = (
            action.upper()
            if action is not None
            else None
        )

        explicit_key = cls._optional_text(
            item.get(
                "recommendation_id"
            )
        )

        if explicit_key is None:
            explicit_key = cls._optional_text(
                item.get(
                    "id"
                )
            )

        recommendation_key = (
            explicit_key
            or cls._derived_key(
                symbol=normalized_symbol,
                action=normalized_action,
                index=index,
            )
        )

        return {
            "recommendation_key": recommendation_key,
            "symbol": normalized_symbol,
            "action": normalized_action,
            "score": cls._first_optional_number(
                item,
                cls.SCORE_KEYS,
                field_name=(
                    f"recommendations[{index}].score"
                ),
            ),
            "confidence": cls._first_optional_number(
                item,
                cls.CONFIDENCE_KEYS,
                field_name=(
                    f"recommendations[{index}].confidence"
                ),
            ),
            "rationale": cls._first_text(
                item,
                cls.RATIONALE_KEYS,
            ),
            "payload_json": json.dumps(
                item,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                allow_nan=False,
            ),
        }

    @classmethod
    def _items(
        cls,
        value: object,
    ) -> tuple[dict[str, Any], ...]:
        if isinstance(
            value,
            list,
        ):
            if any(
                not isinstance(
                    item,
                    dict,
                )
                for item in value
            ):
                raise ValueError(
                    "recommendation items must be dictionaries"
                )

            return tuple(
                value
            )

        if isinstance(
            value,
            dict,
        ):
            for key in cls.ITEM_KEYS:
                nested = value.get(
                    key
                )

                if nested is not None:
                    return cls._items(
                        nested
                    )

            if not value:
                return ()

        raise ValueError(
            "recommendations must be a list or a supported dictionary"
        )

    @staticmethod
    def _derived_key(
        *,
        symbol: str | None,
        action: str | None,
        index: int,
    ) -> str:
        parts = tuple(
            part
            for part in (
                symbol,
                action,
            )
            if part is not None
        )

        prefix = (
            ":".join(
                parts
            )
            if parts
            else "RECOMMENDATION"
        )

        return (
            f"{prefix}:{index:04d}"
        )

    @staticmethod
    def _first_text(
        payload: dict[str, Any],
        keys: tuple[str, ...],
    ) -> str | None:
        for key in keys:
            value = payload.get(
                key
            )

            if value is not None:
                return HistoricalRecommendationsImporter._optional_text(
                    value
                )

        return None

    @staticmethod
    def _optional_text(
        value: object,
    ) -> str | None:
        if value is None:
            return None

        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "optional text values must be non-empty strings"
            )

        return value.strip()

    @staticmethod
    def _first_optional_number(
        payload: dict[str, Any],
        keys: tuple[str, ...],
        *,
        field_name: str,
    ) -> float | None:
        for key in keys:
            value = payload.get(
                key
            )

            if value is not None:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, Real)
                    or not isfinite(float(value))
                ):
                    raise ValueError(
                        f"{field_name} must be a finite number"
                    )

                return float(
                    value
                )

        return None
