"""
Tests for UniversePreparationService.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.preparation.preparation_models import (
    PreparationAssetResult,
)
from investment_terminal.preparation.universe_preparation_service import (
    UniversePreparationService,
)


START = datetime(
    2025,
    8,
    1,
    tzinfo=timezone.utc,
)

END = datetime(
    2026,
    8,
    1,
    tzinfo=timezone.utc,
)

RUN_STARTED = datetime(
    2026,
    8,
    1,
    10,
    0,
    tzinfo=timezone.utc,
)

RUN_FINISHED = RUN_STARTED + timedelta(
    seconds=5,
)


def create_clock():
    values = iter(
        [
            RUN_STARTED,
            RUN_FINISHED,
        ]
    )

    return lambda: next(values)


def create_asset_result(
    symbol: str,
    success: bool = True,
) -> PreparationAssetResult:
    return PreparationAssetResult(
        symbol=symbol,
        success=success,
        downloaded=251 if success else 0,
        inserted=2 if success else 0,
        duplicates=249 if success else 0,
        started_at=RUN_STARTED,
        finished_at=(
            RUN_STARTED
            + timedelta(seconds=1)
        ),
        error_type=(
            None
            if success
            else "RuntimeError"
        ),
        error_message=(
            None
            if success
            else "Provider unavailable"
        ),
    )


def test_prepare_runs_all_unique_symbols() -> None:
    asset_service = Mock()

    asset_service.prepare.side_effect = [
        create_asset_result("MSFT"),
        create_asset_result("AAPL"),
        create_asset_result("GOOGL"),
    ]

    result = UniversePreparationService(
        asset_service=asset_service,
        clock=create_clock(),
    ).prepare(
        symbols=[
            " msft ",
            "AAPL",
            "msft",
            " googl ",
        ],
        resolution=" d ",
        start=START,
        end=END,
        currency=" usd ",
    )

    assert result.total_symbols == 3
    assert result.successful_count == 3
    assert result.failed_count == 0
    assert result.elapsed_seconds == 5.0

    assert [
        asset.symbol
        for asset in result.assets
    ] == [
        "MSFT",
        "AAPL",
        "GOOGL",
    ]

    assert asset_service.prepare.call_count == 3

    asset_service.prepare.assert_any_call(
        symbol="MSFT",
        resolution="D",
        start=START,
        end=END,
        currency="USD",
    )


def test_prepare_collects_failures() -> None:
    asset_service = Mock()

    asset_service.prepare.side_effect = [
        create_asset_result("MSFT"),
        create_asset_result(
            "AAPL",
            success=False,
        ),
        create_asset_result("GOOGL"),
    ]

    result = UniversePreparationService(
        asset_service=asset_service,
        clock=create_clock(),
    ).prepare(
        symbols=[
            "MSFT",
            "AAPL",
            "GOOGL",
        ],
        resolution="D",
        start=START,
        end=END,
        continue_on_error=True,
    )

    assert result.successful_count == 2
    assert result.failed_count == 1
    assert result.assets[1].symbol == "AAPL"
    assert result.assets[1].success is False


def test_prepare_raises_when_continue_is_disabled() -> None:
    asset_service = Mock()

    asset_service.prepare.side_effect = [
        create_asset_result("MSFT"),
        create_asset_result(
            "AAPL",
            success=False,
        ),
    ]

    service = UniversePreparationService(
        asset_service=asset_service,
        clock=create_clock(),
    )

    with pytest.raises(
        RuntimeError,
        match="Preparation failed for AAPL",
    ):
        service.prepare(
            symbols=[
                "MSFT",
                "AAPL",
                "GOOGL",
            ],
            resolution="D",
            start=START,
            end=END,
            continue_on_error=False,
        )

    assert asset_service.prepare.call_count == 2


@pytest.mark.parametrize(
    "symbols",
    [
        [],
        (),
    ],
)
def test_prepare_rejects_empty_symbols(
    symbols,
) -> None:
    service = UniversePreparationService(
        asset_service=Mock(),
        clock=create_clock(),
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        service.prepare(
            symbols=symbols,
            resolution="D",
            start=START,
            end=END,
        )


@pytest.mark.parametrize(
    "symbols",
    [
        "MSFT",
        {"MSFT", "AAPL"},
        None,
    ],
)
def test_prepare_rejects_invalid_collection(
    symbols,
) -> None:
    service = UniversePreparationService(
        asset_service=Mock(),
        clock=create_clock(),
    )

    with pytest.raises(
        TypeError,
        match="list or tuple",
    ):
        service.prepare(
            symbols=symbols,
            resolution="D",
            start=START,
            end=END,
        )


def test_prepare_rejects_invalid_date_range() -> None:
    service = UniversePreparationService(
        asset_service=Mock(),
        clock=create_clock(),
    )

    with pytest.raises(
        ValueError,
        match="end must be after start",
    ):
        service.prepare(
            symbols=["MSFT"],
            resolution="D",
            start=END,
            end=START,
        )


def test_prepare_rejects_invalid_continue_flag() -> None:
    service = UniversePreparationService(
        asset_service=Mock(),
        clock=create_clock(),
    )

    with pytest.raises(
        TypeError,
        match="continue_on_error",
    ):
        service.prepare(
            symbols=["MSFT"],
            resolution="D",
            start=START,
            end=END,
            continue_on_error="yes",
        )