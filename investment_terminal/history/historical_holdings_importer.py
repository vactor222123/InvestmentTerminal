"""
Import historical portfolio holdings from a verified Review Package.
"""

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


class HistoricalHoldingsImporter:
    """
    Normalize portfolio positions into the SQLite holdings table.

    For MARKET_VALUE_CONNECTED packages, market-value positions are imported.
    For COST_BASIS_ONLY packages, the importer accepts the optional
    portfolio.cost_basis_holdings list. Current packages without that list
    produce zero holding rows rather than inventing unavailable detail.
    """

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

    def import_holdings(
        self,
        *,
        snapshot: HistoricalSnapshot,
        payload: dict[str, Any],
    ) -> int:
        """Insert all available holdings for one snapshot."""
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
                    INSERT INTO holdings (
                        snapshot_id,
                        holding_key,
                        symbol,
                        name,
                        asset_type,
                        sleeve,
                        strategy,
                        currency,
                        quantity,
                        unit_price,
                        market_value,
                        weight
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            snapshot.snapshot_id,
                            row["holding_key"],
                            row["symbol"],
                            row["name"],
                            row["asset_type"],
                            row["sleeve"],
                            row["strategy"],
                            row["currency"],
                            row["quantity"],
                            row["unit_price"],
                            row["market_value"],
                            row["weight"],
                        )
                        for row in rows
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Historical holdings could not be imported. "
                "The snapshot may be missing or holdings may already exist."
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

        portfolio = sections.get(
            "portfolio"
        )

        if not isinstance(
            portfolio,
            dict,
        ):
            raise ValueError(
                "Review Package portfolio section must be a dictionary"
            )

        status = cls._required_text(
            portfolio.get(
                "status"
            ),
            field_name="portfolio.status",
        ).upper()

        if status == "MARKET_VALUE_CONNECTED":
            market_value = portfolio.get(
                "market_value"
            )

            if not isinstance(
                market_value,
                dict,
            ):
                raise ValueError(
                    "portfolio.market_value must be a dictionary "
                    "when status is MARKET_VALUE_CONNECTED"
                )

            positions = market_value.get(
                "positions"
            )
            total_value = cls._non_negative_number(
                market_value.get(
                    "total_market_value"
                ),
                field_name="total_market_value",
            )
            source = "MARKET"
        elif status == "COST_BASIS_ONLY":
            positions = portfolio.get(
                "cost_basis_holdings",
                [],
            )
            cost_basis = portfolio.get(
                "cost_basis_snapshot"
            )

            if not isinstance(
                cost_basis,
                dict,
            ):
                raise ValueError(
                    "portfolio.cost_basis_snapshot must be a dictionary"
                )

            total_value = cls._non_negative_number(
                cost_basis.get(
                    "total_value"
                ),
                field_name="total_value",
            )
            source = "COST_BASIS"
        else:
            raise ValueError(
                "portfolio.status must be COST_BASIS_ONLY "
                "or MARKET_VALUE_CONNECTED"
            )

        if not isinstance(
            positions,
            list,
        ):
            raise ValueError(
                "portfolio positions must be a list"
            )

        rows: list[
            dict[str, Any]
        ] = []
        seen_keys: set[str] = set()

        for index, position in enumerate(
            positions
        ):
            if not isinstance(
                position,
                dict,
            ):
                raise ValueError(
                    f"portfolio position {index} must be a dictionary"
                )

            row = cls._normalize_position(
                position=position,
                source=source,
                total_value=total_value,
                index=index,
            )

            if row["holding_key"] in seen_keys:
                raise ValueError(
                    "portfolio positions must contain unique holding keys"
                )

            seen_keys.add(
                row["holding_key"]
            )
            rows.append(
                row
            )

        return tuple(
            rows
        )

    @classmethod
    def _normalize_position(
        cls,
        *,
        position: dict[str, Any],
        source: str,
        total_value: float,
        index: int,
    ) -> dict[str, Any]:
        symbol = cls._required_text(
            position.get(
                "symbol"
            ),
            field_name=f"positions[{index}].symbol",
        ).upper()
        name = cls._required_text(
            position.get(
                "name"
            ),
            field_name=f"positions[{index}].name",
        )
        asset_type = cls._required_text(
            position.get(
                "asset_type"
            ),
            field_name=f"positions[{index}].asset_type",
        ).upper()
        sleeve = cls._required_text(
            position.get(
                "sleeve"
            ),
            field_name=f"positions[{index}].sleeve",
        ).upper()
        strategy = cls._optional_text(
            position.get(
                "strategy"
            )
        )
        currency = cls._required_text(
            position.get(
                "currency"
            ),
            field_name=f"positions[{index}].currency",
        ).upper()
        quantity = cls._non_negative_number(
            position.get(
                "quantity"
            ),
            field_name=f"positions[{index}].quantity",
        )

        if source == "MARKET":
            unit_price = cls._non_negative_number(
                position.get(
                    "market_price"
                ),
                field_name=f"positions[{index}].market_price",
            )
            value = cls._non_negative_number(
                position.get(
                    "market_value"
                ),
                field_name=f"positions[{index}].market_value",
            )
        else:
            unit_price = cls._non_negative_number(
                position.get(
                    "average_cost"
                ),
                field_name=f"positions[{index}].average_cost",
            )
            raw_value = position.get(
                "cost_basis"
            )
            value = (
                cls._non_negative_number(
                    raw_value,
                    field_name=f"positions[{index}].cost_basis",
                )
                if raw_value is not None
                else round(
                    quantity
                    * unit_price,
                    2,
                )
            )

        holding_key = cls._optional_text(
            position.get(
                "instrument_key"
            )
        )

        if holding_key is None:
            holding_key = cls._optional_text(
                position.get(
                    "isin"
                )
            )

        if holding_key is None:
            holding_key = cls._optional_text(
                position.get(
                    "exchange_ticker"
                )
            )

        if holding_key is None:
            holding_key = symbol

        normalized_key = holding_key.upper()
        weight = (
            round(
                value / total_value,
                8,
            )
            if total_value > 0
            else 0.0
        )

        if weight > 1.0 + 0.0001:
            raise ValueError(
                f"positions[{index}] value exceeds portfolio total value"
            )

        return {
            "holding_key": normalized_key,
            "symbol": symbol,
            "name": name,
            "asset_type": asset_type,
            "sleeve": sleeve,
            "strategy": (
                strategy.upper()
                if strategy is not None
                else None
            ),
            "currency": currency,
            "quantity": quantity,
            "unit_price": unit_price,
            "market_value": value,
            "weight": weight,
        }

    @staticmethod
    def _required_text(
        value: object,
        *,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip()

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
    def _non_negative_number(
        value: object,
        *,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
            or float(value) < 0
        ):
            raise ValueError(
                f"{field_name} must be a finite non-negative number"
            )

        return float(
            value
        )
