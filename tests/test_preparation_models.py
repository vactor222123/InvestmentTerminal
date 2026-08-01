"""
Tests for data-preparation result models.
"""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.preparation.preparation_models import (
    PreparationAssetResult,
    UniversePreparationResult,
)


STARTED_AT = datetime(
    2026,
    8,
    1,
    10,
    0,
    tzinfo=timezone.utc,
)

FINISHED_AT = STARTED_AT + timedelta(
    seconds=2.5
)


def create_success(
    symbol: str = "MSFT",
) -> PreparationAssetResult:
    return PreparationAssetResult(
        symbol=symbol,
        success=True,
        downloaded=251,
        inserted=2,
        duplicates=249,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
    )


def create_failure(
    symbol: str = "AAPL",
) -> PreparationAssetResult:
    return PreparationAssetResult(
        symbol=symbol,
        success=False,
        downloaded=0,
        inserted=0,
        duplicates=0,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        error_type="RuntimeError",
        error_message="Provider unavailable",
    )


def test_asset_result_normalizes_symbol() -> None:
    result = create_success(" msft ")

    assert result.symbol == "MSFT"
    assert result.elapsed_seconds == 2.5


def test_failed_asset_requires_error_information() -> None:
    with pytest.raises(
        ValueError,
        match="error_type",
    ):
        PreparationAssetResult(
            symbol="AAPL",
            success=False,
            downloaded=0,
            inserted=0,
            duplicates=0,
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
        )


def test_successful_asset_rejects_error_information() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain",
    ):
        replace(
            create_success(),
            error_type="UnexpectedError",
        )


def test_asset_rejects_negative_count() -> None:
    with pytest.raises(
        ValueError,
        match="inserted",
    ):
        replace(
            create_success(),
            inserted=-1,
        )


def test_universe_result_calculates_totals() -> None:
    result = UniversePreparationResult(
        started_at=STARTED_AT,
        finished_at=(
            STARTED_AT
            + timedelta(seconds=5)
        ),
        assets=(
            create_success("MSFT"),
            PreparationAssetResult(
                symbol="GOOGL",
                success=True,
                downloaded=250,
                inserted=3,
                duplicates=247,
                started_at=STARTED_AT,
                finished_at=FINISHED_AT,
            ),
            create_failure("AAPL"),
        ),
    )

    assert result.total_symbols == 3
    assert result.successful_count == 2
    assert result.failed_count == 1

    assert result.total_downloaded == 501
    assert result.total_inserted == 5
    assert result.total_duplicates == 496
    assert result.elapsed_seconds == 5.0


def test_universe_result_rejects_duplicate_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="unique symbols",
    ):
        UniversePreparationResult(
            started_at=STARTED_AT,
            finished_at=FINISHED_AT,
            assets=(
                create_success("MSFT"),
                create_failure("MSFT"),
            ),
        )


def test_universe_result_is_json_serializable() -> None:
    result = UniversePreparationResult(
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        assets=(
            create_success(),
            create_failure(),
        ),
    )

    payload = result.to_dict()
    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert '"total_symbols": 2' in serialized
    assert payload["successful_count"] == 1
    assert payload["failed_count"] == 1
    assert isinstance(payload["assets"], list)