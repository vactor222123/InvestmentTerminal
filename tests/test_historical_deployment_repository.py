"""
Tests for HistoricalDeployment and HistoricalDeploymentRepository.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_deployment_models import (
    HistoricalDeployment,
)
from investment_terminal.history.historical_deployment_repository import (
    HistoricalDeploymentRepository,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)


def create_snapshot() -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.13.0",
        generated_at=datetime(
            2026,
            8,
            3,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            3,
            17,
            36,
            tzinfo=timezone.utc,
        ),
        relative_path=f"2026/08/{SNAPSHOT_ID}.json",
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def create_repository(
    tmp_path: Path,
) -> tuple[
    HistoricalSQLiteStore,
    HistoricalDeploymentRepository,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    HistoricalSnapshotRepository(
        store
    ).add(
        create_snapshot()
    )

    return (
        store,
        HistoricalDeploymentRepository(
            store
        ),
    )


def test_deployment_model_normalizes_and_detaches_payload() -> None:
    payload = {
        "nested": {
            "items": [
                1,
                2,
            ]
        }
    }
    deployment = HistoricalDeployment(
        snapshot_id=SNAPSHOT_ID.upper(),
        deployment_key=" deploy-1 ",
        amount=500,
        share=0.25,
        reason=" Core ",
        payload=payload,
    )
    payload[
        "nested"
    ][
        "items"
    ].append(
        3
    )

    assert deployment.snapshot_id == SNAPSHOT_ID
    assert deployment.deployment_key == "deploy-1"
    assert deployment.amount == 500.0
    assert deployment.share == 0.25
    assert deployment.reason == "Core"
    assert deployment.to_dict()[
        "payload"
    ] == {
        "nested": {
            "items": [
                1,
                2,
            ]
        }
    }


def test_deployment_model_accepts_absent_numeric_values() -> None:
    deployment = HistoricalDeployment(
        snapshot_id=SNAPSHOT_ID,
        deployment_key="deploy-1",
        amount=None,
        share=None,
        reason=None,
        payload={},
    )

    assert deployment.amount is None
    assert deployment.share is None


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        (
            "amount",
            -1.0,
            "amount must be a finite non-negative number or None",
        ),
        (
            "share",
            1.1,
            "share must be between 0 and 1 or None",
        ),
    ),
)
def test_deployment_model_rejects_invalid_numbers(
    field_name: str,
    value: float,
    message: str,
) -> None:
    values = {
        "snapshot_id": SNAPSHOT_ID,
        "deployment_key": "deploy-1",
        "amount": 100.0,
        "share": 0.2,
        "reason": None,
        "payload": {},
    }
    values[
        field_name
    ] = value

    with pytest.raises(
        ValueError,
        match=message,
    ):
        HistoricalDeployment(
            **values,
        )


def test_repository_returns_empty_tuple(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    assert repository.list_for_snapshot(
        SNAPSHOT_ID
    ) == ()


def test_repository_returns_key_order_and_parsed_payload(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.executemany(
            """
            INSERT INTO deployment (
                snapshot_id,
                deployment_key,
                amount,
                share,
                reason,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    SNAPSHOT_ID,
                    "ZETA",
                    200.0,
                    0.2,
                    "Later",
                    '{"bucket":"ZETA"}',
                ),
                (
                    SNAPSHOT_ID,
                    "ALPHA",
                    500.0,
                    0.5,
                    "Core",
                    '{"bucket":"ALPHA"}',
                ),
            ),
        )

    items = repository.list_for_snapshot(
        SNAPSHOT_ID.upper()
    )

    assert [
        item.deployment_key
        for item in items
    ] == [
        "ALPHA",
        "ZETA",
    ]
    assert items[
        0
    ].payload[
        "bucket"
    ] == "ALPHA"


def test_repository_rejects_invalid_persisted_json(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO deployment (
                snapshot_id,
                deployment_key,
                payload_json
            )
            VALUES (?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "BAD",
                "{invalid",
            ),
        )

    with pytest.raises(
        ValueError,
        match="must contain valid JSON",
    ):
        repository.list_for_snapshot(
            SNAPSHOT_ID
        )


def test_repository_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    with pytest.raises(
        KeyError,
        match="No historical snapshot found",
    ):
        repository.list_for_snapshot(
            "f9b7adca-2f2b-47a4-901d-05ca37c445df"
        )
