"""
Tests for HistoricalPortfolioSummary and its repository.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_portfolio_summary_models import (
    HistoricalPortfolioSummary,
)
from investment_terminal.history.historical_portfolio_summary_repository import (
    HistoricalPortfolioSummaryRepository,
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
    HistoricalPortfolioSummaryRepository,
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
        HistoricalPortfolioSummaryRepository(
            store
        ),
    )


def test_summary_model_normalizes_and_computes_weights() -> None:
    summary = HistoricalPortfolioSummary(
        snapshot_id=SNAPSHOT_ID.upper(),
        portfolio_name=" Main ",
        base_currency=" eur ",
        total_value=10000,
        invested_value=9000,
        cash_value=1000,
        monthly_contribution=500,
        source_status=" cost_basis_only ",
    )

    assert summary.snapshot_id == SNAPSHOT_ID
    assert summary.portfolio_name == "Main"
    assert summary.base_currency == "EUR"
    assert summary.source_status == "COST_BASIS_ONLY"
    assert summary.cash_weight == pytest.approx(
        0.1
    )
    assert summary.invested_weight == pytest.approx(
        0.9
    )


def test_summary_model_handles_zero_total_without_division() -> None:
    summary = HistoricalPortfolioSummary(
        snapshot_id=SNAPSHOT_ID,
        portfolio_name="Main",
        base_currency="EUR",
        total_value=0,
        invested_value=0,
        cash_value=0,
        monthly_contribution=0,
        source_status="COST_BASIS_ONLY",
    )

    assert summary.cash_weight is None
    assert summary.invested_weight is None


def test_summary_model_rejects_inconsistent_total() -> None:
    with pytest.raises(
        ValueError,
        match="must equal total_value",
    ):
        HistoricalPortfolioSummary(
            snapshot_id=SNAPSHOT_ID,
            portfolio_name="Main",
            base_currency="EUR",
            total_value=100,
            invested_value=80,
            cash_value=10,
            monthly_contribution=0,
            source_status="COST_BASIS_ONLY",
        )


def test_repository_returns_none_when_summary_absent(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    assert repository.get(
        SNAPSHOT_ID
    ) is None


def test_repository_returns_typed_summary(
    tmp_path: Path,
) -> None:
    store, repository = create_repository(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id,
                portfolio_name,
                base_currency,
                total_value,
                invested_value,
                cash_value,
                monthly_contribution,
                source_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "Main",
                "EUR",
                10000.0,
                9000.0,
                1000.0,
                500.0,
                "COST_BASIS_ONLY",
            ),
        )

    summary = repository.get(
        SNAPSHOT_ID.upper()
    )

    assert isinstance(
        summary,
        HistoricalPortfolioSummary,
    )
    assert summary.total_value == 10000.0


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
        repository.get(
            "f9b7adca-2f2b-47a4-901d-05ca37c445df"
        )
