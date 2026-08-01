"""
CSV importer for portfolio holdings.
"""

import csv
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_models import (
    PortfolioHolding,
)
from investment_terminal.portfolio.portfolio_holding_import_models import (
    PortfolioHoldingImportResult,
)


class PortfolioHoldingCsvImporter:
    """Load exact portfolio holdings from a UTF-8 CSV file."""

    REQUIRED_COLUMNS = (
        "symbol",
        "name",
        "asset_type",
        "sleeve",
        "quantity",
        "average_cost",
        "currency",
        "isin",
        "exchange_ticker",
    )

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> PortfolioHoldingImportResult:
        resolved_path = (
            path
            if isinstance(path, Path)
            else Path(path)
        )

        if not resolved_path.exists():
            raise FileNotFoundError(
                "Portfolio holdings CSV does not exist: "
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise ValueError(
                "Portfolio holdings CSV path must point to a file"
            )

        with resolved_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(
                file
            )

            if reader.fieldnames is None:
                raise ValueError(
                    "Portfolio holdings CSV has no header"
                )

            missing_columns = tuple(
                column
                for column in cls.REQUIRED_COLUMNS
                if column not in reader.fieldnames
            )

            if missing_columns:
                raise ValueError(
                    "Portfolio holdings CSV is missing columns: "
                    + ", ".join(missing_columns)
                )

            holdings = tuple(
                cls._build_holding(
                    row,
                    line_number=index,
                )
                for index, row in enumerate(
                    reader,
                    start=2,
                )
                if any(
                    value and value.strip()
                    for value in row.values()
                )
            )

        if not holdings:
            raise ValueError(
                "Portfolio holdings CSV contains no holdings"
            )

        return PortfolioHoldingImportResult(
            holdings=holdings,
            source_name=resolved_path.name,
        )

    @classmethod
    def _build_holding(
        cls,
        row: dict[str, str | None],
        *,
        line_number: int,
    ) -> PortfolioHolding:
        try:
            quantity = cls._parse_float(
                row.get("quantity"),
                field_name="quantity",
            )
            average_cost = cls._parse_float(
                row.get("average_cost"),
                field_name="average_cost",
            )

            return PortfolioHolding(
                symbol=cls._required_text(
                    row.get("symbol"),
                    field_name="symbol",
                ),
                name=cls._required_text(
                    row.get("name"),
                    field_name="name",
                ),
                asset_type=cls._required_text(
                    row.get("asset_type"),
                    field_name="asset_type",
                ),
                sleeve=cls._required_text(
                    row.get("sleeve"),
                    field_name="sleeve",
                ),
                quantity=quantity,
                average_cost=average_cost,
                currency=cls._required_text(
                    row.get("currency"),
                    field_name="currency",
                ),
                isin=cls._optional_text(
                    row.get("isin")
                ),
                exchange_ticker=cls._optional_text(
                    row.get("exchange_ticker")
                ),
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"Invalid portfolio holding on CSV line "
                f"{line_number}: {exc}"
            ) from exc

    @staticmethod
    def _required_text(
        value: str | None,
        *,
        field_name: str,
    ) -> str:
        if value is None or not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return value.strip()

    @staticmethod
    def _optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None

    @staticmethod
    def _parse_float(
        value: str | None,
        *,
        field_name: str,
    ) -> float:
        if value is None or not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )

        normalized = (
            value.strip()
            .replace(" ", "")
            .replace(",", ".")
        )

        try:
            return float(
                normalized
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be numeric"
            ) from exc