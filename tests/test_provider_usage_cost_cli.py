import json
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
from investment_terminal.cli.provider_usage_cost import main


def seed(
    database: Path,
) -> None:
    repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            database
        )
    )
    repository.add(
        GroundedProviderUsageCostLedgerRecord(
            request_id="request-001",
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
                0,
                tzinfo=timezone.utc,
            ),
        )
    )
    repository.add(
        GroundedProviderUsageCostLedgerRecord(
            request_id="request-002",
            provider_identity="OPENAI",
            model_identity="gpt-test",
            input_tokens=200,
            output_tokens=60,
            total_tokens=260,
            currency="EUR",
            input_cost=Decimal("0.002000"),
            output_cost=Decimal("0.003000"),
            total_cost=Decimal("0.005000"),
            recorded_at=datetime(
                2026,
                8,
                15,
                12,
                1,
                tzinfo=timezone.utc,
            ),
        )
    )


def test_json_list(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)

    main(
        [
            "--database",
            str(database),
            "--json",
            "list",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )
    assert report["count"] == 2
    assert [
        item["request_id"]
        for item in report["records"]
    ] == [
        "request-001",
        "request-002",
    ]


def test_json_show(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)

    main(
        [
            "--database",
            str(database),
            "--json",
            "show",
            "--request-id",
            "request-002",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )
    assert report["record"]["request_id"] == "request-002"
    assert report["record"]["total_cost"] == "0.005000"


def test_json_summary_uses_exact_decimal_totals(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)

    main(
        [
            "--database",
            str(database),
            "--json",
            "summary",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )
    assert report == {
        "command": "summary",
        "request_count": 2,
        "currency": "EUR",
        "input_tokens": 300,
        "output_tokens": 100,
        "total_tokens": 400,
        "input_cost": "0.003000",
        "output_cost": "0.005000",
        "total_cost": "0.008000",
    }


def test_missing_database_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--database",
                str(tmp_path / "missing.db"),
                "list",
            ]
        )


def test_missing_request_fails_closed(
    tmp_path: Path,
) -> None:
    database = tmp_path / "provider_usage_cost.db"
    seed(database)

    with pytest.raises(SystemExit):
        main(
            [
                "--database",
                str(database),
                "show",
                "--request-id",
                "missing",
            ]
        )
