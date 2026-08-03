"""
Tests for HistoricalImportPipeline.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
    HistoricalImportResult,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
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
GENERATED_AT = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    17,
    36,
    tzinfo=timezone.utc,
)
RELATIVE_PATH = "2026/08/review.json"


def package_payload() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": (
            "2026-08-03T17:35:00+00:00"
        ),
        "sections": {
            "portfolio": {
                "status": "MARKET_VALUE_CONNECTED",
                "cost_basis_snapshot": {
                    "portfolio_name": "Test Portfolio",
                    "base_currency": "EUR",
                    "total_value": 10000.0,
                    "invested_value": 8500.0,
                    "cash_value": 1500.0,
                    "monthly_contribution": 1200.0,
                },
                "market_value": {
                    "portfolio_name": "Test Portfolio",
                    "base_currency": "EUR",
                    "invested_market_value": 9200.0,
                    "cash_value": 1500.0,
                    "total_market_value": 10700.0,
                    "positions": [
                        {
                            "symbol": "WORLD",
                            "name": "World ETF",
                            "asset_type": "ETF",
                            "sleeve": "CORE",
                            "quantity": 50.0,
                            "market_price": 120.0,
                            "market_value": 6000.0,
                            "currency": "EUR",
                            "instrument_key": "IE00B4L5Y983",
                        }
                    ],
                },
            },
            "machine_recommendations": {
                "status": "CONNECTED",
                "recommendations": {
                    "items": [
                        {
                            "symbol": "BABA",
                            "recommendation": "BUY",
                            "score": 82.5,
                            "confidence": 0.76,
                            "rationale": "Attractive valuation.",
                        }
                    ]
                },
                "allocation": {
                    "items": [
                        {
                            "symbol": "BABA",
                            "amount": 600.0,
                            "share": 0.30,
                            "reason": "Highest opportunity score.",
                        }
                    ]
                },
            },
        },
    }


def create_pipeline(
    tmp_path: Path,
    *,
    payload: dict | None = None,
    register_snapshot: bool = True,
) -> tuple[
    HistoricalImportPipeline,
    HistoricalSQLiteStore,
    HistoricalSnapshot,
]:
    archive_root = tmp_path / "history"
    package_path = archive_root / RELATIVE_PATH
    package_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    package_bytes = (
        json.dumps(
            payload or package_payload(),
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )
    package_path.write_bytes(
        package_bytes
    )

    snapshot = HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=GENERATED_AT,
        archived_at=ARCHIVED_AT,
        relative_path=RELATIVE_PATH,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
        supersedes=None,
        status="ARCHIVED",
    )
    store = HistoricalSQLiteStore(
        archive_root / "history.db"
    )

    if register_snapshot:
        HistoricalSnapshotRepository(
            store
        ).add(
            snapshot
        )

    pipeline = HistoricalImportPipeline(
        store=store,
        loader=HistoricalReviewPackageLoader(
            archive_root
        ),
    )

    return pipeline, store, snapshot


def table_count(
    store: HistoricalSQLiteStore,
    table: str,
) -> int:
    with store.connect() as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS row_count
            FROM {table}
            """
        ).fetchone()

    return int(
        row["row_count"]
    )


def test_pipeline_imports_complete_snapshot(
    tmp_path: Path,
) -> None:
    pipeline, store, snapshot = create_pipeline(
        tmp_path
    )

    result = pipeline.import_snapshot(
        snapshot
    )

    assert result == HistoricalImportResult(
        snapshot_id=SNAPSHOT_ID,
        holdings_imported=1,
        recommendations_imported=1,
        deployment_imported=1,
        timeline_events_created=5,
    )
    assert table_count(
        store,
        "portfolio_summary",
    ) == 1
    assert table_count(
        store,
        "holdings",
    ) == 1
    assert table_count(
        store,
        "recommendations",
    ) == 1
    assert table_count(
        store,
        "deployment",
    ) == 1
    assert table_count(
        store,
        "timeline_events",
    ) == 5


def test_pipeline_rejects_unregistered_snapshot(
    tmp_path: Path,
) -> None:
    pipeline, _, snapshot = create_pipeline(
        tmp_path,
        register_snapshot=False,
    )

    with pytest.raises(
        ValueError,
        match="Snapshot metadata must exist",
    ):
        pipeline.import_snapshot(
            snapshot
        )


def test_pipeline_rejects_repeat_import(
    tmp_path: Path,
) -> None:
    pipeline, _, snapshot = create_pipeline(
        tmp_path
    )

    pipeline.import_snapshot(
        snapshot
    )

    with pytest.raises(
        ValueError,
        match="details have already been imported",
    ):
        pipeline.import_snapshot(
            snapshot
        )


def test_pipeline_removes_partial_rows_on_failure(
    tmp_path: Path,
) -> None:
    payload = package_payload()
    payload["sections"]["machine_recommendations"][
        "recommendations"
    ]["items"][0]["score"] = "invalid"

    pipeline, store, snapshot = create_pipeline(
        tmp_path,
        payload=payload,
    )

    with pytest.raises(
        ValueError,
        match="score must be a finite number",
    ):
        pipeline.import_snapshot(
            snapshot
        )

    for table in (
        "portfolio_summary",
        "holdings",
        "recommendations",
        "deployment",
        "timeline_events",
    ):
        assert table_count(
            store,
            table,
        ) == 0

    assert table_count(
        store,
        "snapshots",
    ) == 1


def test_import_result_serializes() -> None:
    result = HistoricalImportResult(
        snapshot_id=SNAPSHOT_ID,
        holdings_imported=2,
        recommendations_imported=3,
        deployment_imported=1,
        timeline_events_created=8,
    )

    assert result.to_dict() == {
        "snapshot_id": SNAPSHOT_ID,
        "holdings_imported": 2,
        "recommendations_imported": 3,
        "deployment_imported": 1,
        "timeline_events_created": 8,
    }


def test_pipeline_rejects_invalid_store(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="store must be a HistoricalSQLiteStore",
    ):
        HistoricalImportPipeline(
            store=object(),  # type: ignore[arg-type]
            loader=HistoricalReviewPackageLoader(
                tmp_path
            ),
        )


def test_pipeline_rejects_invalid_loader(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "loader must be a HistoricalReviewPackageLoader"
        ),
    ):
        HistoricalImportPipeline(
            store=HistoricalSQLiteStore(
                tmp_path / "history.db"
            ),
            loader=object(),  # type: ignore[arg-type]
        )
