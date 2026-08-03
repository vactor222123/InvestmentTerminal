"""
Tests for HistoricalRecommendationsImporter.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_recommendations_importer import (
    HistoricalRecommendationsImporter,
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


def recommendation_payload() -> dict:
    return {
        "sections": {
            "machine_recommendations": {
                "status": "CONNECTED",
                "recommendations": {
                    "items": [
                        {
                            "symbol": "BABA",
                            "recommendation": "BUY",
                            "score": 82.5,
                            "confidence": 0.76,
                            "rationale": (
                                "Attractive valuation and improving "
                                "cloud momentum."
                            ),
                        },
                        {
                            "ticker": "GOOGL",
                            "action": "ACCUMULATE",
                            "ranking_score": 78.0,
                            "confidence_score": 0.69,
                            "reason": (
                                "Strong cash generation with AI upside."
                            ),
                        },
                    ]
                },
                "allocation": {},
            }
        }
    }


def create_importer(
    tmp_path: Path,
) -> tuple[
    HistoricalRecommendationsImporter,
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
        HistoricalRecommendationsImporter(
            store
        ),
        store,
        snapshot,
    )


def read_recommendations(
    store: HistoricalSQLiteStore,
) -> list[dict]:
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM recommendations
            ORDER BY recommendation_key
            """
        ).fetchall()

    return [
        dict(
            row
        )
        for row in rows
    ]


def test_importer_stores_normalized_recommendations(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )

    imported = importer.import_recommendations(
        snapshot=snapshot,
        payload=recommendation_payload(),
    )

    rows = read_recommendations(
        store
    )

    assert imported == 2
    assert len(
        rows
    ) == 2

    baba = next(
        row
        for row in rows
        if row["symbol"] == "BABA"
    )
    assert baba["action"] == "BUY"
    assert baba["score"] == 82.5
    assert baba["confidence"] == 0.76
    assert "valuation" in baba["rationale"]
    assert json.loads(
        baba["payload_json"]
    )["symbol"] == "BABA"


def test_importer_accepts_direct_list(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )
    payload = recommendation_payload()
    payload["sections"]["machine_recommendations"][
        "recommendations"
    ] = [
        {
            "symbol": "SAP",
            "label": "HOLD",
        }
    ]

    imported = importer.import_recommendations(
        snapshot=snapshot,
        payload=payload,
    )

    row = read_recommendations(
        store
    )[0]

    assert imported == 1
    assert row["symbol"] == "SAP"
    assert row["action"] == "HOLD"
    assert row["score"] is None
    assert row["confidence"] is None


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
                "recommendations": {},
            }
        }
    }

    imported = importer.import_recommendations(
        snapshot=snapshot,
        payload=payload,
    )

    assert imported == 0
    assert read_recommendations(
        store
    ) == []


def test_importer_rejects_duplicate_explicit_keys(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = recommendation_payload()
    items = payload["sections"][
        "machine_recommendations"
    ]["recommendations"]["items"]
    items[0]["recommendation_id"] = "same-id"
    items[1]["recommendation_id"] = "same-id"

    with pytest.raises(
        ValueError,
        match="unique keys",
    ):
        importer.import_recommendations(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_repeat_import(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )

    importer.import_recommendations(
        snapshot=snapshot,
        payload=recommendation_payload(),
    )

    with pytest.raises(
        ValueError,
        match="recommendations may already exist",
    ):
        importer.import_recommendations(
            snapshot=snapshot,
            payload=recommendation_payload(),
        )


def test_importer_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    importer = HistoricalRecommendationsImporter(
        store
    )

    with pytest.raises(
        ValueError,
        match="snapshot may be missing",
    ):
        importer.import_recommendations(
            snapshot=create_snapshot(),
            payload=recommendation_payload(),
        )


def test_importer_rejects_invalid_score(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = recommendation_payload()
    payload["sections"]["machine_recommendations"][
        "recommendations"
    ]["items"][0]["score"] = "high"

    with pytest.raises(
        ValueError,
        match="score must be a finite number",
    ):
        importer.import_recommendations(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "store must be a HistoricalSQLiteStore"
        ),
    ):
        HistoricalRecommendationsImporter(
            object()  # type: ignore[arg-type]
        )
