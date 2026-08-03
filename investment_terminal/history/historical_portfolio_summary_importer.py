"""
Import portfolio summary data from a verified Review Package into SQLite.
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


class HistoricalPortfolioSummaryImporter:
    """
    Normalize one Review Package portfolio section into portfolio_summary.

    Market values are preferred when the portfolio section reports
    MARKET_VALUE_CONNECTED. Otherwise the cost-basis snapshot is stored.
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

    def import_summary(
        self,
        *,
        snapshot: HistoricalSnapshot,
        payload: dict[str, Any],
    ) -> None:
        """Insert one immutable portfolio summary for a snapshot."""
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

        summary = self._extract_summary(
            payload
        )

        self.store.initialize()

        try:
            with self.store.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO portfolio_summary (
                        snapshot_id,
                        portfolio_name,
                        base_currency,
                        total_value,
                        invested_value,
                        cash_value,
                        monthly_contribution,
                        source_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.snapshot_id,
                        summary["portfolio_name"],
                        summary["base_currency"],
                        summary["total_value"],
                        summary["invested_value"],
                        summary["cash_value"],
                        summary["monthly_contribution"],
                        summary["source_status"],
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Portfolio summary could not be imported. "
                "The snapshot may be missing or already imported."
            ) from exc

    @classmethod
    def _extract_summary(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
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

        portfolio_name = cls._required_text(
            cost_basis.get(
                "portfolio_name"
            ),
            field_name="portfolio_name",
        )
        base_currency = cls._required_text(
            cost_basis.get(
                "base_currency"
            ),
            field_name="base_currency",
        ).upper()
        monthly_contribution = cls._non_negative_number(
            cost_basis.get(
                "monthly_contribution"
            ),
            field_name="monthly_contribution",
        )

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

            market_portfolio_name = cls._required_text(
                market_value.get(
                    "portfolio_name"
                ),
                field_name="market_value.portfolio_name",
            )
            market_currency = cls._required_text(
                market_value.get(
                    "base_currency"
                ),
                field_name="market_value.base_currency",
            ).upper()

            if market_portfolio_name != portfolio_name:
                raise ValueError(
                    "Market-value portfolio name must match "
                    "cost-basis portfolio name"
                )

            if market_currency != base_currency:
                raise ValueError(
                    "Market-value currency must match "
                    "cost-basis currency"
                )

            invested_value = cls._non_negative_number(
                market_value.get(
                    "invested_market_value"
                ),
                field_name="invested_market_value",
            )
            cash_value = cls._non_negative_number(
                market_value.get(
                    "cash_value"
                ),
                field_name="cash_value",
            )
            total_value = cls._non_negative_number(
                market_value.get(
                    "total_market_value"
                ),
                field_name="total_market_value",
            )
        elif status == "COST_BASIS_ONLY":
            invested_value = cls._non_negative_number(
                cost_basis.get(
                    "invested_value"
                ),
                field_name="invested_value",
            )
            cash_value = cls._non_negative_number(
                cost_basis.get(
                    "cash_value"
                ),
                field_name="cash_value",
            )
            total_value = cls._non_negative_number(
                cost_basis.get(
                    "total_value"
                ),
                field_name="total_value",
            )
        else:
            raise ValueError(
                "portfolio.status must be COST_BASIS_ONLY "
                "or MARKET_VALUE_CONNECTED"
            )

        if abs(
            invested_value
            + cash_value
            - total_value
        ) > 0.01:
            raise ValueError(
                "invested_value and cash_value must equal total_value"
            )

        return {
            "portfolio_name": portfolio_name,
            "base_currency": base_currency,
            "total_value": total_value,
            "invested_value": invested_value,
            "cash_value": cash_value,
            "monthly_contribution": monthly_contribution,
            "source_status": status,
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

        return float(value)
