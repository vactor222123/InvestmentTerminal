from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import (
    SQLiteGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


def repository(
    tmp_path: Path,
) -> SQLiteGroundedProviderUsageCostLedgerRepository:
    return SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            tmp_path / "provider_usage.db"
        )
    )


def add(
    repo: SQLiteGroundedProviderUsageCostLedgerRepository,
    *,
    request_id: str,
    input_cost: str,
    output_cost: str,
    input_tokens: int = 1,
    output_tokens: int = 1,
) -> None:
    repo.add(
        GroundedProviderUsageCostLedgerRecord(
            request_id=request_id,
            provider_identity="OPENAI",
            model_identity="gpt-test",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            currency="EUR",
            input_cost=Decimal(input_cost),
            output_cost=Decimal(output_cost),
            total_cost=(
                Decimal(input_cost)
                + Decimal(output_cost)
            ),
            recorded_at=datetime(
                2026,
                8,
                15,
                12,
                0,
                tzinfo=timezone.utc,
            ),
        )
    )


def test_summary_preserves_decimal_precision_beyond_float(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)

    add(
        repo,
        request_id="a",
        input_cost="0.1000000000000000001",
        output_cost="0.2000000000000000002",
    )
    add(
        repo,
        request_id="b",
        input_cost="0.3000000000000000003",
        output_cost="0.4000000000000000004",
    )

    summary = repo.summarize()

    assert summary.input_cost == Decimal(
        "0.4000000000000000004"
    )
    assert summary.output_cost == Decimal(
        "0.6000000000000000006"
    )
    assert summary.total_cost == Decimal(
        "1.0000000000000000010"
    )


def test_summary_uses_single_aggregate_query_shape(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    add(
        repo,
        request_id="a",
        input_cost="0.001",
        output_cost="0.002",
    )

    statements: list[str] = []

    original_connect = repo.store.connect

    def traced_connect():
        connection = original_connect()
        connection.set_trace_callback(
            statements.append
        )
        return connection

    repo.store.connect = traced_connect  # type: ignore[method-assign]

    summary = repo.summarize()

    selects = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
    ]

    assert summary.request_count == 1
    assert len(selects) == 1
    assert "exact_decimal_sum(input_cost)" in selects[0]
    assert "exact_decimal_sum(output_cost)" in selects[0]
    assert "exact_decimal_sum(total_cost)" in selects[0]


def test_empty_summary_remains_exact_zero(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)

    summary = repo.summarize()

    assert summary.request_count == 0
    assert summary.input_cost == Decimal("0")
    assert summary.output_cost == Decimal("0")
    assert summary.total_cost == Decimal("0")
