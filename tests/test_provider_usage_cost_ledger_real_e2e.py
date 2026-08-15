from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from investment_terminal.ai.model_adapter import GroundedProviderUsage
from investment_terminal.ai.providers.pricing import GroundedProviderCost
from investment_terminal.ai.providers.usage_ledger_recording import (
    GroundedProviderUsageCostLedgerRecordingService,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_repository import (
    SQLiteGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


def test_real_recording_service_to_sqlite_ledger_end_to_end(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=repository
    )

    first = service.record(
        request_id="request-001",
        usage=GroundedProviderUsage(
            input_tokens=100,
            output_tokens=40,
            total_tokens=140,
        ),
        cost=GroundedProviderCost(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            currency="EUR",
            input_cost=Decimal("0.001000"),
            output_cost=Decimal("0.002000"),
            total_cost=Decimal("0.003000"),
        ),
        recorded_at=datetime(
            2026, 8, 15, 12, 0, tzinfo=timezone.utc
        ),
    )

    assert database.is_file()

    reopened = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    persisted = reopened.require("request-001")

    assert persisted == first
    assert persisted.to_dict() == {
        "request_id": "request-001",
        "provider_identity": "OPENAI",
        "model_identity": "gpt-test",
        "input_tokens": 100,
        "output_tokens": 40,
        "total_tokens": 140,
        "currency": "EUR",
        "input_cost": "0.001000",
        "output_cost": "0.002000",
        "total_cost": "0.003000",
        "recorded_at": "2026-08-15T12:00:00+00:00",
    }


def test_real_ledger_preserves_multiple_requests_in_deterministic_order(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=repository
    )

    for request_id, minute in (
        ("request-b", 1),
        ("request-z", 0),
        ("request-a", 1),
    ):
        service.record(
            request_id=request_id,
            usage=GroundedProviderUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            ),
            cost=GroundedProviderCost(
                provider_identity="OPENAI",
                model_identity="gpt-test",
                currency="EUR",
                input_cost=Decimal("0.000100"),
                output_cost=Decimal("0.000200"),
                total_cost=Decimal("0.000300"),
            ),
            recorded_at=datetime(
                2026, 8, 15, 12, minute, tzinfo=timezone.utc
            ),
        )

    reopened = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )

    assert [
        record.request_id
        for record in reopened.list_all()
    ] == [
        "request-z",
        "request-a",
        "request-b",
    ]


def test_real_ledger_duplicate_request_is_fail_closed_and_preserves_original(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    service = GroundedProviderUsageCostLedgerRecordingService(
        repository=repository
    )

    original = service.record(
        request_id="request-001",
        usage=GroundedProviderUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        ),
        cost=GroundedProviderCost(
            provider_identity="OPENAI",
            model_identity="gpt-test",
            currency="EUR",
            input_cost=Decimal("0.000100"),
            output_cost=Decimal("0.000200"),
            total_cost=Decimal("0.000300"),
        ),
        recorded_at=datetime(
            2026, 8, 15, 12, 0, tzinfo=timezone.utc
        ),
    )

    try:
        service.record(
            request_id="request-001",
            usage=GroundedProviderUsage(
                input_tokens=20,
                output_tokens=10,
                total_tokens=30,
            ),
            cost=GroundedProviderCost(
                provider_identity="OPENAI",
                model_identity="gpt-test",
                currency="EUR",
                input_cost=Decimal("0.000200"),
                output_cost=Decimal("0.000400"),
                total_cost=Decimal("0.000600"),
            ),
            recorded_at=datetime(
                2026, 8, 15, 12, 1, tzinfo=timezone.utc
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "duplicate request identity must fail closed"
        )

    reopened = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    assert reopened.list_all() == (original,)
