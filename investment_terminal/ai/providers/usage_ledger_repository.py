"""
Provider usage/cost ledger repository contract and in-memory reference adapter.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.utils.validation import normalize_required_text


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError(
            "limit must be a positive integer"
        )
    return limit


def _validate_aware_datetime(
    value: datetime,
    *,
    field_name: str,
) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )
    return value


class GroundedProviderUsageCostLedgerRepository(ABC):
    """Persistence-agnostic immutable usage/cost ledger contract."""

    @abstractmethod
    def add(
        self,
        record: GroundedProviderUsageCostLedgerRecord,
    ) -> GroundedProviderUsageCostLedgerRecord:
        """Persist one request identity or reject a duplicate."""

    @abstractmethod
    def get(
        self,
        request_id: str,
    ) -> GroundedProviderUsageCostLedgerRecord | None:
        """Return one exact request record, or None when absent."""

    def require(
        self,
        request_id: str,
    ) -> GroundedProviderUsageCostLedgerRecord:
        record = self.get(request_id)
        if record is None:
            raise KeyError(
                f"No provider usage/cost ledger record found for {request_id}"
            )
        return record

    @abstractmethod
    def list_all(
        self,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        """Return all records ordered by recorded_at then request_id."""

    @abstractmethod
    def list_recent(
        self,
        limit: int,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        """Return newest records ordered by recorded_at/request_id descending."""

    @abstractmethod
    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        """Return records in [started_at, ended_at), ordered ascending."""


class InMemoryGroundedProviderUsageCostLedgerRepository(
    GroundedProviderUsageCostLedgerRepository
):
    """Executable reference implementation of immutable ledger semantics."""

    def __init__(self) -> None:
        self._records: dict[
            str,
            GroundedProviderUsageCostLedgerRecord,
        ] = {}

    def add(
        self,
        record: GroundedProviderUsageCostLedgerRecord,
    ) -> GroundedProviderUsageCostLedgerRecord:
        if not isinstance(
            record,
            GroundedProviderUsageCostLedgerRecord,
        ):
            raise TypeError(
                "record must be a GroundedProviderUsageCostLedgerRecord"
            )

        if record.request_id in self._records:
            raise ValueError(
                "Provider usage/cost ledger request identity already exists"
            )

        self._records[record.request_id] = record
        return record

    def get(
        self,
        request_id: str,
    ) -> GroundedProviderUsageCostLedgerRecord | None:
        normalized_id = normalize_required_text(
            request_id,
            field_name="request_id",
        )
        return self._records.get(normalized_id)

    def list_all(
        self,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (
                    record.recorded_at,
                    record.request_id,
                ),
            )
        )

    def list_recent(
        self,
        limit: int,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        validated_limit = _validate_limit(limit)
        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (
                    record.recorded_at,
                    record.request_id,
                ),
                reverse=True,
            )[:validated_limit]
        )

    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[GroundedProviderUsageCostLedgerRecord, ...]:
        start = _validate_aware_datetime(
            started_at,
            field_name="started_at",
        )
        end = _validate_aware_datetime(
            ended_at,
            field_name="ended_at",
        )
        if end <= start:
            raise ValueError(
                "ended_at must be later than started_at"
            )

        return tuple(
            record
            for record in self.list_all()
            if start <= record.recorded_at < end
        )
