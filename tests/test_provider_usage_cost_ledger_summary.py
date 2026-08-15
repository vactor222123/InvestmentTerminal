from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    InMemoryGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import (
    SQLiteGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


def record(
    request_id: str,
    *,
    currency: str = "EUR",
    input_tokens: int = 100,
    output_tokens: int = 40,
    input_cost: str = "0.001000",
    output_cost: str = "0.002000",
):
    return GroundedProviderUsageCostLedgerRecord(
        request_id=request_id,
        provider_identity="OPENAI",
        model_identity="gpt-test",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        currency=currency,
        input_cost=Decimal(input_cost),
        output_cost=Decimal(output_cost),
        total_cost=Decimal(input_cost) + Decimal(output_cost),
        recorded_at=datetime(
            2026, 8, 15, 12, 0, tzinfo=timezone.utc
        ),
    )


def assert_summary(summary) -> None:
    assert summary.to_dict() == {
        "request_count": 2,
        "currency": "EUR",
        "input_tokens": 300,
        "output_tokens": 100,
        "total_tokens": 400,
        "input_cost": "0.003000",
        "output_cost": "0.005000",
        "total_cost": "0.008000",
    }


def populate(repo) -> None:
    repo.add(record("a"))
    repo.add(record(
        "b",
        input_tokens=200,
        output_tokens=60,
        input_cost="0.002000",
        output_cost="0.003000",
    ))


def test_in_memory_summary_exact() -> None:
    repo = InMemoryGroundedProviderUsageCostLedgerRepository()
    populate(repo)
    assert_summary(repo.summarize())


def test_sqlite_summary_exact(
    tmp_path: Path,
) -> None:
    repo = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            tmp_path / "provider_usage.db"
        )
    )
    populate(repo)
    assert_summary(repo.summarize())


def test_empty_summary_is_zeroed(
    tmp_path: Path,
) -> None:
    repo = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            tmp_path / "provider_usage.db"
        )
    )
    assert repo.summarize().to_dict() == {
        "request_count": 0,
        "currency": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "input_cost": "0",
        "output_cost": "0",
        "total_cost": "0",
    }


@pytest.mark.parametrize("sqlite", [False, True])
def test_summary_rejects_mixed_currency(
    tmp_path: Path,
    sqlite: bool,
) -> None:
    if sqlite:
        repo = SQLiteGroundedProviderUsageCostLedgerRepository(
            GroundedProviderUsageCostLedgerSQLiteStore(
                tmp_path / "provider_usage.db"
            )
        )
    else:
        repo = InMemoryGroundedProviderUsageCostLedgerRepository()

    repo.add(record("eur", currency="EUR"))
    repo.add(record("usd", currency="USD"))

    with pytest.raises(
        RuntimeError,
        match="one currency",
    ):
        repo.summarize()
