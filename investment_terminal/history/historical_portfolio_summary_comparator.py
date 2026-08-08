"""
Pure comparator for normalized historical portfolio summaries.
"""

from investment_terminal.history.historical_comparison_models import (
    PortfolioSummaryChange,
    ScalarChange,
)
from investment_terminal.history.historical_portfolio_summary_models import (
    HistoricalPortfolioSummary,
)


class HistoricalPortfolioSummaryComparator:
    """
    Compare two normalized portfolio summaries without making performance claims.

    The comparator reports value and allocation differences only. Snapshot-level
    chronology, schema support and identity compatibility belong to the
    compatibility service.
    """

    def compare(
        self,
        *,
        previous: HistoricalPortfolioSummary | None,
        current: HistoricalPortfolioSummary | None,
    ) -> PortfolioSummaryChange:
        self._validate_optional_summary(
            previous,
            field_name="previous",
        )
        self._validate_optional_summary(
            current,
            field_name="current",
        )

        if (
            previous is not None
            and current is not None
            and previous.base_currency
            != current.base_currency
        ):
            raise ValueError(
                "Portfolio summaries must use the same base currency"
            )

        return PortfolioSummaryChange(
            previous_exists=previous is not None,
            current_exists=current is not None,
            base_currency_previous=(
                None
                if previous is None
                else previous.base_currency
            ),
            base_currency_current=(
                None
                if current is None
                else current.base_currency
            ),
            source_status_previous=(
                None
                if previous is None
                else previous.source_status
            ),
            source_status_current=(
                None
                if current is None
                else current.source_status
            ),
            total_value=ScalarChange.between(
                None
                if previous is None
                else previous.total_value,
                None
                if current is None
                else current.total_value,
            ),
            invested_value=ScalarChange.between(
                None
                if previous is None
                else previous.invested_value,
                None
                if current is None
                else current.invested_value,
            ),
            cash_value=ScalarChange.between(
                None
                if previous is None
                else previous.cash_value,
                None
                if current is None
                else current.cash_value,
            ),
            monthly_contribution=ScalarChange.between(
                None
                if previous is None
                else previous.monthly_contribution,
                None
                if current is None
                else current.monthly_contribution,
            ),
            cash_weight=ScalarChange.between(
                None
                if previous is None
                else previous.cash_weight,
                None
                if current is None
                else current.cash_weight,
            ),
            invested_weight=ScalarChange.between(
                None
                if previous is None
                else previous.invested_weight,
                None
                if current is None
                else current.invested_weight,
            ),
        )

    @staticmethod
    def _validate_optional_summary(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if (
            value is not None
            and not isinstance(
                value,
                HistoricalPortfolioSummary,
            )
        ):
            raise TypeError(
                f"{field_name} must be a HistoricalPortfolioSummary or None"
            )
