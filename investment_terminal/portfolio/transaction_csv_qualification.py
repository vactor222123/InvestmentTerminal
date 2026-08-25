"""Bounded, parse-only qualification of a private transaction CSV."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import Any

from investment_terminal.portfolio.transaction_csv_parser import (
    PortfolioTransactionCsvParser,
)
from investment_terminal.utils.validation import validate_aware_datetime


class TransactionCsvQualificationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TransactionCsvQualificationResult:
    qualified_at: datetime
    status: TransactionCsvQualificationStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    transaction_count: int | None
    transaction_type_counts: tuple[tuple[str, int], ...] = ()
    earliest_occurred_at: datetime | None = None
    latest_occurred_at: datetime | None = None
    failure_type: str | None = None
    failure_reason: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_aware_datetime(self.qualified_at, field_name="qualified_at")
        validate_aware_datetime(self.started_at, field_name="started_at")
        validate_aware_datetime(self.completed_at, field_name="completed_at")
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.status, TransactionCsvQualificationStatus):
            raise TypeError("status must be TransactionCsvQualificationStatus")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")
        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
            or not isfinite(float(self.duration_seconds))
            or self.duration_seconds < 0
        ):
            raise ValueError("duration_seconds must be finite and non-negative")
        if float(self.duration_seconds) != (
            self.completed_at - self.started_at
        ).total_seconds():
            raise ValueError("duration_seconds must match run timestamps")
        if tuple(sorted(self.transaction_type_counts)) != self.transaction_type_counts:
            raise ValueError("transaction_type_counts must be ordered")

        if self.status is TransactionCsvQualificationStatus.SUCCESS:
            if self.transaction_count is None or self.transaction_count < 1:
                raise ValueError("SUCCESS requires a positive transaction_count")
            if self.earliest_occurred_at is None or self.latest_occurred_at is None:
                raise ValueError("SUCCESS requires occurrence coverage")
            if sum(count for _, count in self.transaction_type_counts) != self.transaction_count:
                raise ValueError("type counts must match transaction_count")
            if self.failure_type is not None or self.failure_reason is not None:
                raise ValueError("SUCCESS cannot carry failure details")
        elif self.status is TransactionCsvQualificationStatus.EMPTY:
            if self.transaction_count != 0:
                raise ValueError("EMPTY requires transaction_count zero")
            if self.transaction_type_counts:
                raise ValueError("EMPTY cannot carry type counts")
            if self.earliest_occurred_at is not None or self.latest_occurred_at is not None:
                raise ValueError("EMPTY cannot carry occurrence coverage")
            if self.failure_type is not None or self.failure_reason is not None:
                raise ValueError("EMPTY cannot carry failure details")
        else:
            if self.transaction_count is not None or self.transaction_type_counts:
                raise ValueError("FAILED requires unknown coverage")
            if self.earliest_occurred_at is not None or self.latest_occurred_at is not None:
                raise ValueError("FAILED cannot carry occurrence coverage")
            if not self.failure_type or not self.failure_reason:
                raise ValueError("FAILED requires failure details")

        for value, name in (
            (self.earliest_occurred_at, "earliest_occurred_at"),
            (self.latest_occurred_at, "latest_occurred_at"),
        ):
            if value is not None:
                validate_aware_datetime(value, field_name=name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "request": {"qualified_at": self.qualified_at.isoformat()},
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "coverage": {
                "transaction_count": self.transaction_count,
                "transaction_type_counts": dict(self.transaction_type_counts),
                "earliest_occurred_at": (
                    self.earliest_occurred_at.isoformat()
                    if self.earliest_occurred_at is not None else None
                ),
                "latest_occurred_at": (
                    self.latest_occurred_at.isoformat()
                    if self.latest_occurred_at is not None else None
                ),
            },
            "failure": (
                None if self.failure_type is None else {
                    "type": self.failure_type,
                    "reason": self.failure_reason,
                }
            ),
            "limitations": [
                "report excludes transaction identities and monetary values",
                "qualification does not persist transactions",
                "qualification does not establish atomic batch import readiness",
                "qualification does not authorize analysis or trading",
            ],
        }


class TransactionCsvQualificationService:
    def __init__(self, *, clock) -> None:
        self._clock = clock

    def qualify(
        self, path: str | Path, *, qualified_at: datetime
    ) -> TransactionCsvQualificationResult:
        validate_aware_datetime(qualified_at, field_name="qualified_at")
        started_at = self._clock()
        validate_aware_datetime(started_at, field_name="started_at")
        try:
            batch = PortfolioTransactionCsvParser.load(
                path, imported_at=qualified_at
            )
        except Exception as exc:
            completed_at = self._completed_at(started_at)
            return TransactionCsvQualificationResult(
                qualified_at=qualified_at,
                status=TransactionCsvQualificationStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                transaction_count=None,
                failure_type=type(exc).__name__,
                failure_reason=str(exc).strip() or "transaction CSV qualification failed",
            )

        completed_at = self._completed_at(started_at)
        if not batch.transactions:
            return TransactionCsvQualificationResult(
                qualified_at=qualified_at,
                status=TransactionCsvQualificationStatus.EMPTY,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                transaction_count=0,
            )
        occurred = tuple(item.occurred_at for item in batch.transactions)
        counts = Counter(item.transaction_type for item in batch.transactions)
        return TransactionCsvQualificationResult(
            qualified_at=qualified_at,
            status=TransactionCsvQualificationStatus.SUCCESS,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            transaction_count=len(batch.transactions),
            transaction_type_counts=tuple(sorted(counts.items())),
            earliest_occurred_at=min(occurred),
            latest_occurred_at=max(occurred),
        )

    def _completed_at(self, started_at: datetime) -> datetime:
        completed_at = self._clock()
        validate_aware_datetime(completed_at, field_name="completed_at")
        if completed_at < started_at:
            raise ValueError("qualification clock moved backwards")
        return completed_at
