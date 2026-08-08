"""
Tests for HistoricalPortfolioSummaryComparator.
"""

import pytest

from investment_terminal.history.historical_portfolio_summary_comparator import (
    HistoricalPortfolioSummaryComparator,
)
from investment_terminal.history.historical_portfolio_summary_models import (
    HistoricalPortfolioSummary,
)


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)


def summary(
    snapshot_id: str,
    *,
    total: float = 10000.0,
    invested: float = 9000.0,
    cash: float = 1000.0,
    contribution: float = 500.0,
    currency: str = "EUR",
    status: str = "COST_BASIS_ONLY",
) -> HistoricalPortfolioSummary:
    return HistoricalPortfolioSummary(
        snapshot_id=snapshot_id,
        portfolio_name="Main",
        base_currency=currency,
        total_value=total,
        invested_value=invested,
        cash_value=cash,
        monthly_contribution=contribution,
        source_status=status,
    )


def test_comparator_reports_value_and_weight_changes() -> None:
    previous = summary(
        FIRST_ID,
        total=10000.0,
        invested=9000.0,
        cash=1000.0,
    )
    current = summary(
        SECOND_ID,
        total=12000.0,
        invested=10200.0,
        cash=1800.0,
    )

    change = HistoricalPortfolioSummaryComparator().compare(
        previous=previous,
        current=current,
    )

    assert change.previous_exists
    assert change.current_exists
    assert change.total_value.absolute_change == 2000.0
    assert change.total_value.percentage_change == 20.0
    assert change.cash_weight.previous == pytest.approx(
        0.1
    )
    assert change.cash_weight.current == pytest.approx(
        0.15
    )
    assert change.source_status_previous == "COST_BASIS_ONLY"


def test_comparator_exposes_source_status_change() -> None:
    change = HistoricalPortfolioSummaryComparator().compare(
        previous=summary(
            FIRST_ID,
            status="COST_BASIS_ONLY",
        ),
        current=summary(
            SECOND_ID,
            status="MARKET_VALUE_CONNECTED",
        ),
    )

    assert change.source_status_previous == "COST_BASIS_ONLY"
    assert change.source_status_current == "MARKET_VALUE_CONNECTED"


def test_comparator_handles_missing_previous_summary() -> None:
    change = HistoricalPortfolioSummaryComparator().compare(
        previous=None,
        current=summary(
            SECOND_ID
        ),
    )

    assert not change.previous_exists
    assert change.current_exists
    assert change.total_value.previous is None
    assert change.total_value.current == 10000.0
    assert change.total_value.absolute_change is None
    assert change.total_value.percentage_change is None


def test_comparator_handles_missing_current_summary() -> None:
    change = HistoricalPortfolioSummaryComparator().compare(
        previous=summary(
            FIRST_ID
        ),
        current=None,
    )

    assert change.previous_exists
    assert not change.current_exists
    assert change.cash_weight.current is None


def test_comparator_handles_zero_total_weights_without_division() -> None:
    change = HistoricalPortfolioSummaryComparator().compare(
        previous=summary(
            FIRST_ID,
            total=0.0,
            invested=0.0,
            cash=0.0,
            contribution=0.0,
        ),
        current=summary(
            SECOND_ID,
            total=100.0,
            invested=80.0,
            cash=20.0,
            contribution=0.0,
        ),
    )

    assert change.cash_weight.previous is None
    assert change.cash_weight.current == pytest.approx(
        0.2
    )
    assert change.cash_weight.percentage_change is None


def test_comparator_rejects_currency_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="same base currency",
    ):
        HistoricalPortfolioSummaryComparator().compare(
            previous=summary(
                FIRST_ID,
                currency="EUR",
            ),
            current=summary(
                SECOND_ID,
                currency="USD",
            ),
        )


def test_comparator_rejects_wrong_input_type() -> None:
    with pytest.raises(
        TypeError,
        match="previous must be a HistoricalPortfolioSummary or None",
    ):
        HistoricalPortfolioSummaryComparator().compare(
            previous=object(),
            current=None,
        )
