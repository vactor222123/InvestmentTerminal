from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_terminal.ai.providers.usage_ledger import (
    GroundedProviderUsageCostLedgerRecord,
)
from investment_terminal.ai.providers.usage_ledger_repository import (
    GroundedProviderUsageCostLedgerRepository,
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
    minute: int = 0,
    input_cost: Decimal = Decimal("0.001000"),
    output_cost: Decimal = Decimal("0.002000"),
) -> GroundedProviderUsageCostLedgerRecord:
    return GroundedProviderUsageCostLedgerRecord(
        request_id=request_id,
        provider_identity="OPENAI",
        model_identity="gpt-test",
        input_tokens=100,
        output_tokens=40,
        total_tokens=140,
        currency="EUR",
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        recorded_at=datetime(
            2026,
            8,
            15,
            12,
            minute,
            tzinfo=timezone.utc,
        ),
    )


def repository(
    tmp_path: Path,
) -> SQLiteGroundedProviderUsageCostLedgerRepository:
    result = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            tmp_path / "provider_usage.db"
        )
    )
    assert isinstance(
        result,
        GroundedProviderUsageCostLedgerRepository,
    )
    return result


def test_repository_requires_sqlite_store() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedProviderUsageCostLedgerSQLiteStore",
    ):
        SQLiteGroundedProviderUsageCostLedgerRepository(
            object()  # type: ignore[arg-type]
        )


def test_add_and_get_round_trip_exact_record(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    expected = record("request-001")

    assert repo.add(expected) is expected
    assert repo.get("request-001") == expected


def test_get_returns_none_when_absent(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)

    assert repo.get("missing") is None


def test_require_uses_repository_contract(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    expected = record("request-001")
    repo.add(expected)

    assert repo.require("request-001") == expected


def test_duplicate_request_identity_is_rejected(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
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


def test_add_rejects_wrong_record_type(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)

    with pytest.raises(
        TypeError,
        match="GroundedProviderUsageCostLedgerRecord",
    ):
        repo.add(object())  # type: ignore[arg-type]


def test_list_all_is_deterministic(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)

    second_same_time = record(
        "request-b",
        minute=1,
    )
    earlier = record(
        "request-z",
        minute=0,
    )
    first_same_time = record(
        "request-a",
        minute=1,
    )

    repo.add(second_same_time)
    repo.add(earlier)
    repo.add(first_same_time)

    assert repo.list_all() == (
        earlier,
        first_same_time,
        second_same_time,
    )


def test_decimal_text_round_trip_preserves_exact_values(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    expected = record(
        "request-001",
        input_cost=Decimal("0.00123000"),
        output_cost=Decimal("0.00456000"),
    )

    repo.add(expected)
    actual = repo.require("request-001")

    assert actual.input_cost == Decimal("0.00123000")
    assert actual.output_cost == Decimal("0.00456000")
    assert actual.total_cost == Decimal("0.00579000")
    assert actual.to_dict() == expected.to_dict()


def test_get_normalizes_request_identity(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path)
    expected = record("request-001")
    repo.add(expected)

    assert repo.get("  request-001  ") == expected


def test_records_survive_repository_recreation(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage.db"
    first = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    expected = record("request-001")
    first.add(expected)

    second = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )

    assert second.require("request-001") == expected
