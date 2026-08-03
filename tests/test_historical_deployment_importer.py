"""
Tests for HistoricalDeploymentImporter.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_deployment_importer import (
    HistoricalDeploymentImporter,
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
        product_version="0.12.0",
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
        relative_path=(
            f"2026/08/{SNAPSHOT_ID}.json"
        ),
        checksum_sha256="a" * 64,
        supersedes=None,
        status="ARCHIVED",
    )


def deployment_payload() -> dict:
    return {
        "sections": {
            "machine_recommendations": {
                "status": "CONNECTED",
                "recommendations": {},
                "allocation": {
                    "items": [
                        {
                            "symbol": "BABA",
                            "amount": 600.0,
                            "share": 0.30,
                            "reason": (
                                "Highest tactical opportunity score."
                            ),
                        },
                        {
                            "bucket": "CASH",
                            "allocation_amount": 400.0,
                            "weight": 0.20,
                            "rationale": (
                                "Reserve capital for a market pullback."
                            ),
                        },
                    ]
                },
            }
        }
    }


def create_importer(
    tmp_path: Path,
) -> tuple[
    HistoricalDeploymentImporter,
    HistoricalSQLiteStore,
    HistoricalSnapshot,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    snapshot = create_snapshot()
    HistoricalSnapshotRepository(
        store
    ).add(
        snapshot
    )

    return (
        HistoricalDeploymentImporter(
            store
        ),
        store,
        snapshot,
    )


def read_deployment(
    store: HistoricalSQLiteStore,
) -> list[dict]:
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM deployment
            ORDER BY deployment_key
            """
        ).fetchall()

    return [
        dict(
            row
        )
        for row in rows
    ]


def test_importer_stores_normalized_deployment(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )

    imported = importer.import_deployment(
        snapshot=snapshot,
        payload=deployment_payload(),
    )

    rows = read_deployment(
        store
    )

    assert imported == 2
    assert len(
        rows
    ) == 2

    baba = next(
        row
        for row in rows
        if row["deployment_key"].startswith(
            "BABA:"
        )
    )
    assert baba["amount"] == 600.0
    assert baba["share"] == 0.30
    assert "tactical" in baba["reason"]
    assert json.loads(
        baba["payload_json"]
    )["symbol"] == "BABA"


def test_importer_accepts_direct_list(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )
    payload = deployment_payload()
    payload["sections"]["machine_recommendations"][
        "allocation"
    ] = [
        {
            "ticker": "GOOGL",
            "capital": 500.0,
            "allocation_share": 0.25,
        }
    ]

    imported = importer.import_deployment(
        snapshot=snapshot,
        payload=payload,
    )

    row = read_deployment(
        store
    )[0]

    assert imported == 1
    assert row["deployment_key"].startswith(
        "GOOGL:"
    )
    assert row["amount"] == 500.0
    assert row["share"] == 0.25


def test_importer_accepts_single_dictionary(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )
    payload = deployment_payload()
    payload["sections"]["machine_recommendations"][
        "allocation"
    ] = {
        "allocation_id": "cash-reserve",
        "bucket": "CASH",
        "value": 300.0,
    }

    imported = importer.import_deployment(
        snapshot=snapshot,
        payload=payload,
    )

    row = read_deployment(
        store
    )[0]

    assert imported == 1
    assert row["deployment_key"] == "cash-reserve"
    assert row["amount"] == 300.0


def test_disconnected_section_imports_zero(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )
    payload = {
        "sections": {
            "machine_recommendations": {
                "status": "NOT_CONNECTED",
                "allocation": {},
            }
        }
    }

    imported = importer.import_deployment(
        snapshot=snapshot,
        payload=payload,
    )

    assert imported == 0
    assert read_deployment(
        store
    ) == []


def test_importer_rejects_duplicate_explicit_keys(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = deployment_payload()
    items = payload["sections"][
        "machine_recommendations"
    ]["allocation"]["items"]
    items[0]["deployment_id"] = "same-id"
    items[1]["deployment_id"] = "same-id"

    with pytest.raises(
        ValueError,
        match="unique keys",
    ):
        importer.import_deployment(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_invalid_share(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = deployment_payload()
    payload["sections"]["machine_recommendations"][
        "allocation"
    ]["items"][0]["share"] = 1.5

    with pytest.raises(
        ValueError,
        match="share must be between 0 and 1",
    ):
        importer.import_deployment(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_repeat_import(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )

    importer.import_deployment(
        snapshot=snapshot,
        payload=deployment_payload(),
    )

    with pytest.raises(
        ValueError,
        match="deployment records may already exist",
    ):
        importer.import_deployment(
            snapshot=snapshot,
            payload=deployment_payload(),
        )


def test_importer_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    importer = HistoricalDeploymentImporter(
        store
    )

    with pytest.raises(
        ValueError,
        match="snapshot may be missing",
    ):
        importer.import_deployment(
            snapshot=create_snapshot(),
            payload=deployment_payload(),
        )


def test_importer_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "store must be a HistoricalSQLiteStore"
        ),
    ):
        HistoricalDeploymentImporter(
            object()  # type: ignore[arg-type]
        )
