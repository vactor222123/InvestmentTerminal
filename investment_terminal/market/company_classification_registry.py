"""
CSV-backed company classification registry.
"""

import csv
from pathlib import Path

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)


class CompanyClassificationRegistry:
    """
    Load and query sector-aware company metadata.
    """

    DEFAULT_PATH = (
        Path("data")
        / "company_classifications.csv"
    )

    REQUIRED_COLUMNS = (
        "symbol",
        "sector",
        "industry",
        "business_model",
    )

    def __init__(
        self,
        classifications: tuple[
            CompanyClassification,
            ...
        ],
        *,
        source_path: Path | None = None,
    ) -> None:
        if not isinstance(
            classifications,
            tuple,
        ):
            raise TypeError(
                "classifications must be a tuple"
            )

        if any(
            not isinstance(
                item,
                CompanyClassification,
            )
            for item in classifications
        ):
            raise TypeError(
                "classifications must contain only "
                "CompanyClassification objects"
            )

        symbols = tuple(
            item.symbol
            for item in classifications
        )

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "classifications must contain unique symbols"
            )

        if (
            source_path is not None
            and not isinstance(
                source_path,
                Path,
            )
        ):
            raise TypeError(
                "source_path must be a Path or None"
            )

        self._classifications = classifications
        self._by_symbol = {
            item.symbol: item
            for item in classifications
        }
        self.source_path = source_path

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_PATH,
    ) -> "CompanyClassificationRegistry":
        resolved_path = (
            path
            if isinstance(path, Path)
            else Path(path)
        )

        if not resolved_path.exists():
            raise FileNotFoundError(
                "Company classification file does not exist: "
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise ValueError(
                "Company classification path must point to a file"
            )

        with resolved_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(
                    "Company classification CSV has no header"
                )

            missing_columns = tuple(
                column
                for column in cls.REQUIRED_COLUMNS
                if column not in reader.fieldnames
            )

            if missing_columns:
                raise ValueError(
                    "Company classification CSV is missing columns: "
                    + ", ".join(missing_columns)
                )

            classifications = tuple(
                CompanyClassification(
                    symbol=row["symbol"],
                    sector=row["sector"],
                    industry=row["industry"],
                    business_model=row["business_model"],
                )
                for row in reader
                if any(
                    value and value.strip()
                    for value in row.values()
                )
            )

        if not classifications:
            raise ValueError(
                "Company classification CSV contains no records"
            )

        return cls(
            classifications,
            source_path=resolved_path,
        )

    @property
    def size(self) -> int:
        return len(self._classifications)

    @property
    def classifications(
        self,
    ) -> tuple[CompanyClassification, ...]:
        return self._classifications

    def get(
        self,
        symbol: str,
    ) -> CompanyClassification | None:
        normalized = (
            symbol.strip().upper()
            if isinstance(symbol, str)
            else ""
        )

        if not normalized:
            raise ValueError(
                "symbol must be a non-empty string"
            )

        return self._by_symbol.get(
            normalized
        )

    def require(
        self,
        symbol: str,
    ) -> CompanyClassification:
        classification = self.get(
            symbol
        )

        if classification is None:
            raise KeyError(
                f"No company classification found for {symbol}"
            )

        return classification

    def missing_symbols(
        self,
        symbols: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not isinstance(
            symbols,
            tuple,
        ):
            raise TypeError(
                "symbols must be a tuple"
            )

        return tuple(
            symbol.strip().upper()
            for symbol in symbols
            if (
                not isinstance(symbol, str)
                or not symbol.strip()
                or symbol.strip().upper()
                not in self._by_symbol
            )
        )