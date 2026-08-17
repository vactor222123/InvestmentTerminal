"""Provider-neutral CSV parsing boundary for portfolio transactions."""

import csv
from datetime import datetime
from pathlib import Path

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.transaction_import import (
    TransactionImportBatch,
)
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
)


class PortfolioTransactionCsvParser:
    """Parse canonical UTF-8 transaction CSV files without deduplication."""

    COLUMNS = (
        "transaction_id",
        "transaction_type",
        "occurred_at",
        "settlement_currency",
        "symbol",
        "name",
        "instrument_type",
        "instrument_currency",
        "isin",
        "exchange_ticker",
        "exchange_code",
        "quantity",
        "unit_price",
        "cash_amount",
        "source_reference",
    )
    INSTRUMENT_COLUMNS = (
        "symbol",
        "name",
        "instrument_type",
        "instrument_currency",
        "isin",
        "exchange_ticker",
        "exchange_code",
    )
    REQUIRED_INSTRUMENT_COLUMNS = (
        "symbol",
        "name",
        "instrument_type",
        "instrument_currency",
    )

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        imported_at: datetime,
    ) -> TransactionImportBatch:
        resolved_path = path if isinstance(path, Path) else Path(path)
        if not resolved_path.exists():
            raise FileNotFoundError(
                f"Portfolio transaction CSV does not exist: {resolved_path}"
            )
        if not resolved_path.is_file():
            raise ValueError("Portfolio transaction CSV path must point to a file")

        with resolved_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            cls._validate_header(reader.fieldnames)
            transactions = tuple(
                cls._build_transaction(row, line_number=line_number)
                for line_number, row in enumerate(reader, start=2)
                if any(value and value.strip() for value in row.values())
            )

        return TransactionImportBatch(
            source_name=resolved_path.name,
            imported_at=imported_at,
            transactions=transactions,
        )

    @classmethod
    def _validate_header(cls, fieldnames: list[str] | None) -> None:
        if fieldnames is None:
            raise ValueError("Portfolio transaction CSV has no header")
        duplicates = tuple(
            name for name in dict.fromkeys(fieldnames) if fieldnames.count(name) > 1
        )
        if duplicates:
            raise ValueError(
                "Portfolio transaction CSV has duplicate columns: "
                + ", ".join(duplicates)
            )
        missing = tuple(column for column in cls.COLUMNS if column not in fieldnames)
        if missing:
            raise ValueError(
                "Portfolio transaction CSV is missing columns: " + ", ".join(missing)
            )

    @classmethod
    def _build_transaction(
        cls,
        row: dict[str | None, str | list[str] | None],
        *,
        line_number: int,
    ) -> PortfolioTransaction:
        try:
            if None in row:
                raise ValueError("row contains more values than the header")
            return PortfolioTransaction(
                transaction_id=cls._required_text(
                    row.get("transaction_id"), "transaction_id"
                ),
                transaction_type=cls._required_text(
                    row.get("transaction_type"), "transaction_type"
                ),
                occurred_at=cls._parse_datetime(row.get("occurred_at")),
                settlement_currency=cls._required_text(
                    row.get("settlement_currency"), "settlement_currency"
                ),
                instrument=cls._build_instrument(row),
                quantity=cls._optional_float(row.get("quantity"), "quantity"),
                unit_price=cls._optional_float(row.get("unit_price"), "unit_price"),
                cash_amount=cls._optional_float(row.get("cash_amount"), "cash_amount"),
                source_reference=cls._optional_text(row.get("source_reference")),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid portfolio transaction on CSV line {line_number}: {exc}"
            ) from exc

    @classmethod
    def _build_instrument(
        cls,
        row: dict[str | None, str | list[str] | None],
    ) -> InstrumentIdentity | None:
        values = {
            name: cls._optional_text(row.get(name)) for name in cls.INSTRUMENT_COLUMNS
        }
        if not any(values.values()):
            return None
        missing = tuple(
            name for name in cls.REQUIRED_INSTRUMENT_COLUMNS if values[name] is None
        )
        if missing:
            raise ValueError(
                "partial instrument is missing fields: " + ", ".join(missing)
            )
        return InstrumentIdentity(
            symbol=values["symbol"],
            name=values["name"],
            instrument_type=values["instrument_type"],
            currency=values["instrument_currency"],
            isin=values["isin"],
            exchange_ticker=values["exchange_ticker"],
            exchange_code=values["exchange_code"],
        )

    @staticmethod
    def _required_text(value: object, field_name: str) -> str:
        normalized = PortfolioTransactionCsvParser._optional_text(value)
        if normalized is None:
            raise ValueError(f"{field_name} must not be empty")
        return normalized

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("CSV field value must be text")
        normalized = value.strip()
        return normalized or None

    @classmethod
    def _parse_datetime(cls, value: object) -> datetime:
        normalized = cls._required_text(value, "occurred_at")
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("occurred_at must be an ISO 8601 datetime") from exc

    @classmethod
    def _optional_float(cls, value: object, field_name: str) -> float | None:
        normalized = cls._optional_text(value)
        if normalized is None:
            return None
        try:
            return float(normalized.replace(" ", "").replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be numeric") from exc
