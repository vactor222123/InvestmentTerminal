from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import (
    SQLiteGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


def at(minute: int) -> datetime:
    return datetime(
        2026, 8, 15, 12, minute, tzinfo=timezone.utc
    )


def record(
    request_id: str,
    *,
    minute: int,
) -> GroundedProviderUsageCostLedgerRecord:
    return GroundedProviderUsageCostLedgerRecord(
        request_id=request_id,
        provider_identity="OPENAI",
        model_identity="gpt-test",
        input_tokens=100,
        output_tokens=40,
        total_tokens=140,
        currency="EUR",
        input_cost=Decimal("0.001000"),
        output_cost=Decimal("0.002000"),
        total_cost=Decimal("0.003000"),
        recorded_at=at(minute),
    )


def populated(
    database: Path,
) -> SQLiteGroundedProviderUsageCostLedgerRepository:
    repo = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    for item in (
        record("request-b", minute=2),
        record("request-z", minute=0),
        record("request-a", minute=2),
        record("request-m", minute=1),
    ):
        repo.add(item)
    return repo


def test_sqlite_recent_is_bounded_and_newest_first(
    tmp_path: Path,
) -> None:
    repo = populated(
        tmp_path / "provider_usage.db"
    )

    assert [
        item.request_id
        for item in repo.list_recent(3)
    ] == [
        "request-b",
        "request-a",
        "request-m",
    ]


def test_sqlite_between_uses_half_open_window(
    tmp_path: Path,
) -> None:
    repo = populated(
        tmp_path / "provider_usage.db"
    )

    assert [
        item.request_id
        for item in repo.list_between(
            at(1),
            at(2),
        )
    ] == [
        "request-m",
    ]


def test_sqlite_between_orders_ties_by_request_id(
    tmp_path: Path,
) -> None:
    repo = populated(
        tmp_path / "provider_usage.db"
    )

    assert [
        item.request_id
        for item in repo.list_between(
            at(2),
            at(3),
        )
    ] == [
        "request-a",
        "request-b",
    ]


@pytest.mark.parametrize("limit", [0, -1, True])
def test_sqlite_recent_rejects_invalid_limit(
    tmp_path: Path,
    limit,
) -> None:
    repo = populated(
        tmp_path / "provider_usage.db"
    )

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        repo.list_recent(limit)


def test_sqlite_between_requires_aware_boundaries(
    tmp_path: Path,
) -> None:
    repo = populated(
        tmp_path / "provider_usage.db"
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        repo.list_between(
            datetime(2026, 8, 15, 12, 0),
            at(3),
        )


def test_sqlite_bounded_queries_survive_repository_recreation(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage.db"
    populated(database)

    reopened = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )

    assert [
        item.request_id
        for item in reopened.list_recent(2)
    ] == [
        "request-b",
        "request-a",
    ]
    assert [
        item.request_id
        for item in reopened.list_between(
            at(0),
            at(2),
        )
    ] == [
        "request-z",
        "request-m",
    ]
