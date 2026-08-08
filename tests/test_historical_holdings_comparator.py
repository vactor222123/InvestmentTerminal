"""
Tests for HistoricalHoldingsComparator.
"""

import pytest

from investment_terminal.history.historical_holding_models import (
    HistoricalHolding,
)
from investment_terminal.history.historical_holdings_comparator import (
    HistoricalHoldingsComparator,
)


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)


def holding(
    snapshot_id: str,
    key: str,
    *,
    symbol: str | None = None,
    quantity: float = 10.0,
    unit_price: float = 100.0,
    market_value: float = 1000.0,
    weight: float = 0.1,
    sleeve: str = "CORE",
) -> HistoricalHolding:
    return HistoricalHolding(
        snapshot_id=snapshot_id,
        holding_key=key,
        symbol=symbol or key,
        name=f"{key} Fund",
        asset_type="ETF",
        sleeve=sleeve,
        strategy=None,
        currency="EUR",
        quantity=quantity,
        unit_price=unit_price,
        market_value=market_value,
        weight=weight,
    )


def test_comparator_detects_added_removed_changed_and_unchanged() -> None:
    comparator = HistoricalHoldingsComparator()

    result = comparator.compare(
        previous=(
            holding(
                FIRST_ID,
                "BOND",
            ),
            holding(
                FIRST_ID,
                "EM",
            ),
            holding(
                FIRST_ID,
                "WORLD",
            ),
        ),
        current=(
            holding(
                SECOND_ID,
                "EM",
            ),
            holding(
                SECOND_ID,
                "GOLD",
            ),
            holding(
                SECOND_ID,
                "WORLD",
                quantity=12.0,
                market_value=1200.0,
                weight=0.12,
            ),
        ),
    )

    assert [
        change.holding_key
        for change in result
    ] == [
        "BOND",
        "EM",
        "GOLD",
        "WORLD",
    ]

    by_key = {
        change.holding_key: change
        for change in result
    }

    assert by_key[
        "BOND"
    ].change_type == "REMOVED"
    assert by_key[
        "EM"
    ].change_type == "UNCHANGED"
    assert by_key[
        "GOLD"
    ].change_type == "ADDED"
    assert by_key[
        "WORLD"
    ].change_type == "CHANGED"

    assert by_key[
        "WORLD"
    ].quantity.absolute_change == 2.0
    assert by_key[
        "WORLD"
    ].market_value.percentage_change == 20.0


def test_descriptive_change_marks_holding_changed() -> None:
    result = HistoricalHoldingsComparator().compare(
        previous=(
            holding(
                FIRST_ID,
                "WORLD",
                sleeve="CORE",
            ),
        ),
        current=(
            holding(
                SECOND_ID,
                "WORLD",
                sleeve="SATELLITE",
            ),
        ),
    )

    assert result[
        0
    ].change_type == "CHANGED"
    assert result[
        0
    ].previous[
        "sleeve"
    ] == "CORE"
    assert result[
        0
    ].current[
        "sleeve"
    ] == "SATELLITE"


def test_different_keys_are_not_implicitly_matched() -> None:
    result = HistoricalHoldingsComparator().compare(
        previous=(
            holding(
                FIRST_ID,
                "OLD_KEY",
                symbol="WORLD",
            ),
        ),
        current=(
            holding(
                SECOND_ID,
                "NEW_KEY",
                symbol="WORLD",
            ),
        ),
    )

    assert [
        (
            change.holding_key,
            change.change_type,
        )
        for change in result
    ] == [
        (
            "NEW_KEY",
            "ADDED",
        ),
        (
            "OLD_KEY",
            "REMOVED",
        ),
    ]


def test_added_holding_has_absent_previous_deltas() -> None:
    result = HistoricalHoldingsComparator().compare(
        previous=(),
        current=(
            holding(
                SECOND_ID,
                "GOLD",
            ),
        ),
    )

    change = result[
        0
    ]

    assert change.change_type == "ADDED"
    assert change.previous is None
    assert change.quantity.previous is None
    assert change.quantity.absolute_change is None


def test_comparator_rejects_duplicate_keys() -> None:
    duplicate = holding(
        FIRST_ID,
        "WORLD",
    )

    with pytest.raises(
        ValueError,
        match="duplicate holding_key WORLD",
    ):
        HistoricalHoldingsComparator().compare(
            previous=(
                duplicate,
                duplicate,
            ),
            current=(),
        )


def test_comparator_rejects_non_tuple_input() -> None:
    with pytest.raises(
        TypeError,
        match="previous must be a tuple",
    ):
        HistoricalHoldingsComparator().compare(
            previous=[],  # type: ignore[arg-type]
            current=(),
        )
