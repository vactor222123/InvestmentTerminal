from datetime import datetime, timezone
from decimal import Decimal

import pytest

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    GroundedProviderUsageCostLedgerRepository,
    InMemoryGroundedProviderUsageCostLedgerRepository,
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


def populated():
    repo = InMemoryGroundedProviderUsageCostLedgerRepository()
    for item in (
        record("request-b", minute=2),
        record("request-z", minute=0),
        record("request-a", minute=2),
        record("request-m", minute=1),
    ):
        repo.add(item)
    return repo


def test_recent_is_bounded_and_newest_first() -> None:
    repo = populated()

    assert [
        item.request_id
        for item in repo.list_recent(3)
    ] == [
        "request-b",
        "request-a",
        "request-m",
    ]


@pytest.mark.parametrize("limit", [0, -1, True])
def test_recent_rejects_invalid_limit(limit) -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        populated().list_recent(limit)


def test_between_uses_half_open_window() -> None:
    repo = populated()

    assert [
        item.request_id
        for item in repo.list_between(
            at(1),
            at(2),
        )
    ] == [
        "request-m",
    ]


def test_between_orders_ties_by_request_id() -> None:
    repo = populated()

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


def test_between_requires_aware_boundaries() -> None:
    repo = populated()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        repo.list_between(
            datetime(2026, 8, 15, 12, 0),
            at(3),
        )


def test_between_requires_positive_window() -> None:
    repo = populated()

    with pytest.raises(
        ValueError,
        match="later than",
    ):
        repo.list_between(
            at(2),
            at(2),
        )


def test_repository_contract_exposes_bounded_queries() -> None:
    repo = populated()

    assert isinstance(
        repo,
        GroundedProviderUsageCostLedgerRepository,
    )
    assert repo.list_recent(1)
    assert repo.list_between(at(0), at(3))
