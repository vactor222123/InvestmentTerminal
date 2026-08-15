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


def record(
    request_id: str,
    *,
    minute: int = 0,
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
        recorded_at=datetime(
            2026,
            8,
            15,
            12,
            minute,
            tzinfo=timezone.utc,
        ),
    )


def repository() -> InMemoryGroundedProviderUsageCostLedgerRepository:
    result = InMemoryGroundedProviderUsageCostLedgerRepository()
    assert isinstance(
        result,
        GroundedProviderUsageCostLedgerRepository,
    )
    return result


def test_add_and_get_exact_request_identity() -> None:
    repo = repository()
    expected = record("request-001")

    assert repo.add(expected) is expected
    assert repo.get("request-001") is expected


def test_get_returns_none_when_request_is_absent() -> None:
    repo = repository()

    assert repo.get("missing") is None


def test_require_returns_existing_record() -> None:
    repo = repository()
    expected = record("request-001")
    repo.add(expected)

    assert repo.require("request-001") is expected


def test_require_rejects_missing_record() -> None:
    repo = repository()

    with pytest.raises(
        KeyError,
        match="No provider usage/cost ledger record",
    ):
        repo.require("missing")


def test_add_rejects_duplicate_request_identity() -> None:
    repo = repository()
    repo.add(record("request-001"))

    with pytest.raises(
        ValueError,
        match="request identity already exists",
    ):
        repo.add(
            record(
                "request-001",
                minute=1,
            )
        )


def test_add_rejects_wrong_record_type() -> None:
    repo = repository()

    with pytest.raises(
        TypeError,
        match="GroundedProviderUsageCostLedgerRecord",
    ):
        repo.add(object())  # type: ignore[arg-type]


def test_list_all_is_deterministic() -> None:
    repo = repository()

    second_same_time = record(
        "request-b",
        minute=1,
    )
    first_same_time = record(
        "request-a",
        minute=1,
    )
    earlier = record(
        "request-z",
        minute=0,
    )

    repo.add(second_same_time)
    repo.add(earlier)
    repo.add(first_same_time)

    assert repo.list_all() == (
        earlier,
        first_same_time,
        second_same_time,
    )


def test_get_normalizes_request_identity() -> None:
    repo = repository()
    expected = record("request-001")
    repo.add(expected)

    assert repo.get("  request-001  ") is expected


def test_get_rejects_empty_request_identity() -> None:
    repo = repository()

    with pytest.raises(
        ValueError,
        match="request_id",
    ):
        repo.get("   ")
