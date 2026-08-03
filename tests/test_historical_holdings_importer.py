"""
Tests for HistoricalHoldingsImporter.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_holdings_importer import (
    HistoricalHoldingsImporter,
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


def market_payload() -> dict:
    return {
        "sections": {
            "portfolio": {
                "status": "MARKET_VALUE_CONNECTED",
                "cost_basis_snapshot": {
                    "total_value": 10000.0,
                },
                "market_value": {
                    "total_market_value": 11000.0,
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
                            "exchange_ticker": "EUNL",
                        },
                        {
                            "symbol": "MSFT",
                            "name": "Microsoft",
                            "asset_type": "STOCK",
                            "sleeve": "TACTICAL",
                            "quantity": 10.0,
                            "market_price": 400.0,
                            "market_value": 4000.0,
                            "currency": "EUR",
                            "instrument_key": "MSFT",
                            "exchange_ticker": "MSFT",
                        },
                    ],
                },
            }
        }
    }


def cost_basis_payload() -> dict:
    return {
        "sections": {
            "portfolio": {
                "status": "COST_BASIS_ONLY",
                "cost_basis_snapshot": {
                    "total_value": 10000.0,
                },
                "cost_basis_holdings": [
                    {
                        "symbol": "WORLD",
                        "name": "World ETF",
                        "asset_type": "ETF",
                        "sleeve": "CORE",
                        "strategy": "LONG_TERM",
                        "quantity": 50.0,
                        "average_cost": 100.0,
                        "cost_basis": 5000.0,
                        "currency": "EUR",
                        "isin": "IE00B4L5Y983",
                    }
                ],
                "market_value": None,
            }
        }
    }


def create_importer(
    tmp_path: Path,
) -> tuple[
    HistoricalHoldingsImporter,
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
        HistoricalHoldingsImporter(
            store
        ),
        store,
        snapshot,
    )


def read_holdings(
    store: HistoricalSQLiteStore,
) -> list[dict]:
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM holdings
            ORDER BY holding_key
            """
        ).fetchall()

    return [
        dict(
            row
        )
        for row in rows
    ]


def test_importer_stores_market_positions(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )

    imported = importer.import_holdings(
        snapshot=snapshot,
        payload=market_payload(),
    )

    rows = read_holdings(
        store
    )

    assert imported == 2
    assert len(
        rows
    ) == 2
    assert rows[0]["holding_key"] == "IE00B4L5Y983"
    assert rows[0]["unit_price"] == 120.0
    assert rows[0]["market_value"] == 6000.0
    assert rows[0]["weight"] == round(
        6000.0 / 11000.0,
        8,
    )


def test_importer_stores_cost_basis_positions(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )

    imported = importer.import_holdings(
        snapshot=snapshot,
        payload=cost_basis_payload(),
    )

    row = read_holdings(
        store
    )[0]

    assert imported == 1
    assert row["holding_key"] == "IE00B4L5Y983"
    assert row["unit_price"] == 100.0
    assert row["market_value"] == 5000.0
    assert row["strategy"] == "LONG_TERM"
    assert row["weight"] == 0.5


def test_cost_basis_without_holding_detail_imports_zero(
    tmp_path: Path,
) -> None:
    importer, store, snapshot = create_importer(
        tmp_path
    )
    payload = cost_basis_payload()
    del payload["sections"]["portfolio"][
        "cost_basis_holdings"
    ]

    imported = importer.import_holdings(
        snapshot=snapshot,
        payload=payload,
    )

    assert imported == 0
    assert read_holdings(
        store
    ) == []


def test_importer_rejects_duplicate_holding_keys(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = market_payload()
    payload["sections"]["portfolio"][
        "market_value"
    ]["positions"][1]["instrument_key"] = (
        "IE00B4L5Y983"
    )

    with pytest.raises(
        ValueError,
        match="unique holding keys",
    ):
        importer.import_holdings(
            snapshot=snapshot,
            payload=payload,
        )


def test_importer_rejects_repeat_import(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )

    importer.import_holdings(
        snapshot=snapshot,
        payload=market_payload(),
    )

    with pytest.raises(
        ValueError,
        match="holdings may already exist",
    ):
        importer.import_holdings(
            snapshot=snapshot,
            payload=market_payload(),
        )


def test_importer_rejects_missing_snapshot(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    importer = HistoricalHoldingsImporter(
        store
    )

    with pytest.raises(
        ValueError,
        match="snapshot may be missing",
    ):
        importer.import_holdings(
            snapshot=create_snapshot(),
            payload=market_payload(),
        )


def test_importer_rejects_unknown_status(
    tmp_path: Path,
) -> None:
    importer, _, snapshot = create_importer(
        tmp_path
    )
    payload = market_payload()
    payload["sections"]["portfolio"][
        "status"
    ] = "UNKNOWN"

    with pytest.raises(
        ValueError,
        match="portfolio.status must be",
    ):
        importer.import_holdings(
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
        HistoricalHoldingsImporter(
            object()  # type: ignore[arg-type]
        )
