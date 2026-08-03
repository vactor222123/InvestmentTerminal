"""
Tests for HistoricalPortfolioSummaryImporter.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_portfolio_summary_importer import (
    HistoricalPortfolioSummaryImporter,
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


def cost_basis_payload() -> dict:
    return {
        "sections": {
            "portfolio": {
                "status": "COST_BASIS_ONLY",
                "cost_basis_snapshot": {
                    "portfolio_name": "Test Portfolio",
                    "base_currency": "EUR",
                    "total_value": 10000.0,
                    "invested_value": 8500.0,
                    "cash_value": 1500.0,
                    "monthly_contribution": 1200.0,
                },
                "market_value": None,
            }
        }
    }


def market_value_payload() -> dict:
    return {
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
                },
            }
        }
    }


def create_importer(
    tmp_path: Path,
) -> tuple[
    HistoricalPortfolioSummaryImporter,
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
        HistoricalPortfolioSummaryImporter(
            store
        ),
        store,
        snapshot,
    )


def read_summary(
    store: HistoricalSQLiteStore,
) -> dict:
    with store.connect() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM portfolio_summary
            WHERE snapshot_id = ?
            """,
            (
                SNAPSHOT_ID,
            ),
        ).fetchone()

    return dict(
        row
    )


def test_importer_stores_cost_basis_summary(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )

    importer.import_summary(
        snapshot=snapshot,
        payload=cost_basis_payload(),
    )

    row = read_summary(
        store
    )

    assert row["portfolio_name"] == "Test Portfolio"
    assert row["base_currency"] == "EUR"
    assert row["total_value"] == 10000.0
    assert row["invested_value"] == 8500.0
    assert row["cash_value"] == 1500.0
    assert row["monthly_contribution"] == 1200.0
    assert row["source_status"] == "COST_BASIS_ONLY"


def test_importer_prefers_market_value_summary(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )

    importer.import_summary(
        snapshot=snapshot,
        payload=market_value_payload(),
    )

    row = read_summary(
        store
    )

    assert row["total_value"] == 10700.0
    assert row["invested_value"] == 9200.0
    assert row["cash_value"] == 1500.0
    assert row["source_status"] == (
        "MARKET_VALUE_CONNECTED"
    )


def test_importer_rejects_duplicate_summary(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )

    importer.import_summary(
        snapshot=snapshot,
        payload=cost_basis_payload(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "snapshot may be missing or already imported"
        ),
    ):
        importer.import_summary(
            snapshot=snapshot,
            payload=cost_basis_payload(),
        )


def test_importer_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    importer = HistoricalPortfolioSummaryImporter(
        store
    )

    with pytest.raises(
        ValueError,
        match=(
            "snapshot may be missing or already imported"
        ),
    ):
        importer.import_summary(
            snapshot=create_snapshot(),
            payload=cost_basis_payload(),
        )


def test_importer_rejects_inconsistent_totals(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = cost_basis_payload()
    payload["sections"]["portfolio"][
        "cost_basis_snapshot"
    ]["total_value"] = 9999.0

    with pytest.raises(
        ValueError,
        match=(
            "invested_value and cash_value "
            "must equal total_value"
        ),
    ):
        importer.import_summary(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_unknown_status(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = cost_basis_payload()
    payload["sections"]["portfolio"][
        "status"
    ] = "UNKNOWN"

    with pytest.raises(
        ValueError,
        match=(
            "portfolio.status must be COST_BASIS_ONLY "
            "or MARKET_VALUE_CONNECTED"
        ),
    ):
        importer.import_summary(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_market_identity_mismatch(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = market_value_payload()
    payload["sections"]["portfolio"][
        "market_value"
    ]["portfolio_name"] = "Other Portfolio"

    with pytest.raises(
        ValueError,
        match=(
            "Market-value portfolio name must match"
        ),
    ):
        importer.import_summary(
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
        HistoricalPortfolioSummaryImporter(
            object()  # type: ignore[arg-type]
        )
