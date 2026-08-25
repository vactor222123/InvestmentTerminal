"""Bounded durable import and redacted reporting for transaction CSV files."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import Any

from investment_terminal.portfolio.transaction_csv_parser import (
    PortfolioTransactionCsvParser,
)
from investment_terminal.portfolio.transaction_import import TransactionImportService
from investment_terminal.portfolio.transaction_ledger_repository import (
    PortfolioTransactionRepository,
)
from investment_terminal.utils.validation import validate_aware_datetime


class TransactionCsvImportStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TransactionCsvImportResult:
    imported_at: datetime
    status: TransactionCsvImportStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    submitted_count: int | None
    imported_count: int | None
    duplicate_count: int | None
    stored_total: int | None
    earliest_occurred_at: datetime | None = None
    latest_occurred_at: datetime | None = None
    failure_type: str | None = None
    failure_reason: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        for value, name in (
            (self.imported_at, "imported_at"),
            (self.started_at, "started_at"),
            (self.completed_at, "completed_at"),
        ):
            validate_aware_datetime(value, field_name=name)
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.status, TransactionCsvImportStatus):
            raise TypeError("status must be TransactionCsvImportStatus")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")
        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
            or not isfinite(float(self.duration_seconds))
            or self.duration_seconds < 0
        ):
            raise ValueError("duration_seconds must be finite and non-negative")
        if self.duration_seconds != (
            self.completed_at - self.started_at
        ).total_seconds():
            raise ValueError("duration_seconds must match run timestamps")

        counts = (
            self.submitted_count,
            self.imported_count,
            self.duplicate_count,
            self.stored_total,
        )
        if self.status is TransactionCsvImportStatus.SUCCESS:
            if any(value is None or value < 0 for value in counts):
                raise ValueError("SUCCESS requires non-negative aggregate counts")
            if self.submitted_count != self.imported_count + self.duplicate_count:
                raise ValueError("submitted count must equal imported plus duplicate")
            if self.failure_type is not None or self.failure_reason is not None:
                raise ValueError("SUCCESS cannot carry failure details")
        elif self.status is TransactionCsvImportStatus.EMPTY:
            if counts != (0, 0, 0, None):
                raise ValueError("EMPTY requires zero submitted counts")
            if self.failure_type is not None or self.failure_reason is not None:
                raise ValueError("EMPTY cannot carry failure details")
        else:
            if any(value is not None for value in counts):
                raise ValueError("FAILED requires unknown aggregate counts")
            if not self.failure_type or not self.failure_reason:
                raise ValueError("FAILED requires failure details")

        for value, name in (
            (self.earliest_occurred_at, "earliest_occurred_at"),
            (self.latest_occurred_at, "latest_occurred_at"),
        ):
            if value is not None:
                validate_aware_datetime(value, field_name=name)
        if self.status is not TransactionCsvImportStatus.SUCCESS and (
            self.earliest_occurred_at is not None
            or self.latest_occurred_at is not None
        ):
            raise ValueError("only SUCCESS may carry stored occurrence coverage")
        if (self.earliest_occurred_at is None) != (
            self.latest_occurred_at is None
        ):
            raise ValueError("stored occurrence coverage must be complete")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "request": {"imported_at": self.imported_at.isoformat()},
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "coverage": {
                "submitted_count": self.submitted_count,
                "imported_count": self.imported_count,
                "duplicate_count": self.duplicate_count,
                "stored_total": self.stored_total,
                "earliest_occurred_at": self._iso(self.earliest_occurred_at),
                "latest_occurred_at": self._iso(self.latest_occurred_at),
            },
            "failure": (
                None
                if self.failure_type is None
                else {"type": self.failure_type, "reason": self.failure_reason}
            ),
            "limitations": [
                "report excludes transaction identities and monetary values",
                "report excludes source, database, ledger, and portfolio identities",
                "result does not generate valuations or execute a workflow",
                "result does not authorize analysis or trading",
            ],
        }

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None


class TransactionCsvImportService:
    def __init__(self, repository: PortfolioTransactionRepository, *, clock) -> None:
        if not isinstance(repository, PortfolioTransactionRepository):
            raise TypeError("repository must be a PortfolioTransactionRepository")
        self._repository = repository
        self._clock = clock

    def import_csv(
        self, path: str | Path, *, imported_at: datetime
    ) -> TransactionCsvImportResult:
        validate_aware_datetime(imported_at, field_name="imported_at")
        started_at = self._clock()
        validate_aware_datetime(started_at, field_name="started_at")
        try:
            batch = PortfolioTransactionCsvParser.load(path, imported_at=imported_at)
            if not batch.transactions:
                return self._result(
                    imported_at=imported_at,
                    status=TransactionCsvImportStatus.EMPTY,
                    started_at=started_at,
                    submitted_count=0,
                    imported_count=0,
                    duplicate_count=0,
                    stored_total=None,
                )
            imported = TransactionImportService(self._repository).import_batch(batch)
            stored = self._repository.list_all()
            occurred = tuple(item.occurred_at for item in stored)
            return self._result(
                imported_at=imported_at,
                status=TransactionCsvImportStatus.SUCCESS,
                started_at=started_at,
                submitted_count=imported.submitted_count,
                imported_count=imported.imported_count,
                duplicate_count=imported.duplicate_count,
                stored_total=len(stored),
                earliest_occurred_at=min(occurred) if occurred else None,
                latest_occurred_at=max(occurred) if occurred else None,
            )
        except Exception as exc:
            return self._result(
                imported_at=imported_at,
                status=TransactionCsvImportStatus.FAILED,
                started_at=started_at,
                submitted_count=None,
                imported_count=None,
                duplicate_count=None,
                stored_total=None,
                failure_type=type(exc).__name__,
                failure_reason=_privacy_safe_failure_reason(exc),
            )

    def _result(self, *, started_at: datetime, **values) -> TransactionCsvImportResult:
        completed_at = self._clock()
        validate_aware_datetime(completed_at, field_name="completed_at")
        if completed_at < started_at:
            raise ValueError("import clock moved backwards")
        return TransactionCsvImportResult(
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            **values,
        )


def _privacy_safe_failure_reason(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "transaction CSV is unavailable"
    if isinstance(exc, PermissionError):
        return "transaction import input or storage is not accessible"
    if isinstance(exc, UnicodeError):
        return "transaction CSV is not valid UTF-8"
    if isinstance(exc, ValueError):
        return "transaction CSV or database metadata validation failed"
    if (
        isinstance(exc, RuntimeError)
        and str(exc) == "transaction database metadata does not match store configuration"
    ):
        return "transaction CSV or database metadata validation failed"
    return "transaction database operation failed"
