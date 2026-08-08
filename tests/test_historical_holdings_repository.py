"""
Tests for HistoricalHolding and HistoricalHoldingsRepository.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_holding_models import (
    HistoricalHolding,
)
from investment_terminal.history.historical_holdings_repository import (
    HistoricalHoldingsRepository,
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
    HistoricalHoldingsRepository,
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
        HistoricalHoldingsRepository(
            store
        ),
    )


def test_holding_model_normalizes() -> None:
    holding = HistoricalHolding(
        snapshot_id=SNAPSHOT_ID.upper(),
        holding_key=" world ",
        symbol=" world ",
        name=" World ETF ",
        asset_type=" etf ",
        sleeve=" core ",
        strategy=" long_term ",
        currency=" eur ",
        quantity=10,
        unit_price=100,
        market_value=1000,
        weight=0.1,
    )

    assert holding.snapshot_id == SNAPSHOT_ID
    assert holding.holding_key == "WORLD"
    assert holding.symbol == "WORLD"
    assert holding.asset_type == "ETF"
    assert holding.strategy == "LONG_TERM"
    assert holding.currency == "EUR"


def test_holding_model_rejects_weight_above_one() -> None:
    with pytest.raises(
        ValueError,
        match="weight must not exceed 1",
    ):
        HistoricalHolding(
            snapshot_id=SNAPSHOT_ID,
            holding_key="WORLD",
            symbol="WORLD",
            name="World ETF",
            asset_type="ETF",
            sleeve="CORE",
            strategy=None,
            currency="EUR",
            quantity=1,
            unit_price=100,
            market_value=100,
            weight=1.1,
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


def test_repository_returns_holdings_in_key_order(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.executemany(
            """
            INSERT INTO holdings (
                snapshot_id,
                holding_key,
                symbol,
                name,
                asset_type,
                sleeve,
                strategy,
                currency,
                quantity,
                unit_price,
                market_value,
                weight
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    SNAPSHOT_ID,
                    "WORLD",
                    "WORLD",
                    "World ETF",
                    "ETF",
                    "CORE",
                    None,
                    "EUR",
                    10.0,
                    100.0,
                    1000.0,
                    0.1,
                ),
                (
                    SNAPSHOT_ID,
                    "BOND",
                    "BOND",
                    "Bond ETF",
                    "ETF",
                    "DEFENSIVE",
                    None,
                    "EUR",
                    5.0,
                    100.0,
                    500.0,
                    0.05,
                ),
            ),
        )

    holdings = repository.list_for_snapshot(
        SNAPSHOT_ID.upper()
    )

    assert [
        holding.holding_key
        for holding in holdings
    ] == [
        "BOND",
        "WORLD",
    ]


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
