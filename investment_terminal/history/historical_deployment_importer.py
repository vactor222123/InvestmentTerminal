"""
Import historical deployment and allocation decisions into SQLite.
"""

import json
import sqlite3
from math import isfinite
from numbers import Real
from typing import Any

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


class HistoricalDeploymentImporter:
    """
    Normalize machine allocation or deployment plans into structured history.

    The importer reads sections.machine_recommendations.allocation and accepts:

    - a direct list;
    - a dictionary containing items;
    - a dictionary containing allocations;
    - a dictionary containing deployment;
    - a dictionary containing plan.

    Every source item is preserved exactly in payload_json.
    """

    ITEM_KEYS = (
        "items",
        "allocations",
        "deployment",
        "plan",
    )
    KEY_FIELDS = (
        "deployment_id",
        "allocation_id",
        "id",
    )
    AMOUNT_FIELDS = (
        "amount",
        "allocation_amount",
        "capital",
        "value",
    )
    SHARE_FIELDS = (
        "share",
        "weight",
        "allocation_share",
    )
    REASON_FIELDS = (
        "reason",
        "rationale",
        "summary",
        "explanation",
    )
    SUBJECT_FIELDS = (
        "symbol",
        "ticker",
        "instrument",
        "asset",
        "bucket",
        "sleeve",
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

    def import_deployment(
        self,
        *,
        snapshot: HistoricalSnapshot,
        payload: dict[str, Any],
    ) -> int:
        """Insert all available deployment records for one snapshot."""
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

        self.store.initialize()

        try:
            with self.store.connect() as connection:
                connection.executemany(
                    """
                    INSERT INTO deployment (
                        snapshot_id,
                        deployment_key,
                        amount,
                        share,
                        reason,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            snapshot.snapshot_id,
                            row["deployment_key"],
                            row["amount"],
                            row["share"],
                            row["reason"],
                            row["payload_json"],
                        )
                        for row in rows
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical deployment could not be imported. "
                "The snapshot may be missing or deployment records "
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

        allocation = machine_section.get(
            "allocation",
            [],
        )
        items = cls._items(
            allocation
        )

        rows: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for index, item in enumerate(
            items
        ):
            row = cls._normalize_item(
                item=item,
                index=index,
            )

            if row["deployment_key"] in seen_keys:
                raise ValueError(
                    "deployment records must contain unique keys"
                )

            seen_keys.add(
                row["deployment_key"]
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
        explicit_key = cls._first_text(
            item,
            cls.KEY_FIELDS,
        )
        subject = cls._first_text(
            item,
            cls.SUBJECT_FIELDS,
        )

        deployment_key = (
            explicit_key
            or cls._derived_key(
                subject=subject,
                index=index,
            )
        )

        amount = cls._first_optional_number(
            item,
            cls.AMOUNT_FIELDS,
            field_name=(
                f"deployment[{index}].amount"
            ),
        )
        share = cls._first_optional_number(
            item,
            cls.SHARE_FIELDS,
            field_name=(
                f"deployment[{index}].share"
            ),
        )

        if (
            share is not None
            and not 0.0 <= share <= 1.0
        ):
            raise ValueError(
                f"deployment[{index}].share must be between 0 and 1"
            )

        if (
            amount is not None
            and amount < 0
        ):
            raise ValueError(
                f"deployment[{index}].amount must be non-negative"
            )

        return {
            "deployment_key": deployment_key,
            "amount": amount,
            "share": share,
            "reason": cls._first_text(
                item,
                cls.REASON_FIELDS,
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
                    "deployment items must be dictionaries"
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

            # A single deployment dictionary is also accepted.
            return (
                value,
            )

        raise ValueError(
            "allocation must be a list or a supported dictionary"
        )

    @staticmethod
    def _derived_key(
        *,
        subject: str | None,
        index: int,
    ) -> str:
        prefix = (
            subject.strip().upper()
            if subject is not None
            else "DEPLOYMENT"
        )

        return f"{prefix}:{index:04d}"

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
                if (
                    not isinstance(value, str)
                    or not value.strip()
                ):
                    raise ValueError(
                        f"{key} must be a non-empty string"
                    )

                return value.strip()

        return None

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
