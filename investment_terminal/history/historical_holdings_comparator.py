"""
Pure comparator for normalized historical holdings.
"""

from investment_terminal.history.historical_comparison_models import (
    HoldingChange,
    ScalarChange,
)
from investment_terminal.history.historical_holding_models import (
    HistoricalHolding,
)


class HistoricalHoldingsComparator:
    """Compare holdings strictly by stable holding_key."""

    def compare(
        self,
        *,
        previous: tuple[HistoricalHolding, ...],
        current: tuple[HistoricalHolding, ...],
    ) -> tuple[HoldingChange, ...]:
        previous_by_key = self._index(
            previous,
            field_name="previous",
        )
        current_by_key = self._index(
            current,
            field_name="current",
        )

        keys = tuple(
            sorted(
                set(
                    previous_by_key
                )
                | set(
                    current_by_key
                )
            )
        )

        return tuple(
            self._compare_key(
                key,
                previous_by_key.get(
                    key
                ),
                current_by_key.get(
                    key
                ),
            )
            for key in keys
        )

    @classmethod
    def _compare_key(
        cls,
        key: str,
        previous: HistoricalHolding | None,
        current: HistoricalHolding | None,
    ) -> HoldingChange:
        if previous is None:
            change_type = "ADDED"
        elif current is None:
            change_type = "REMOVED"
        elif cls._equivalent(
            previous,
            current,
        ):
            change_type = "UNCHANGED"
        else:
            change_type = "CHANGED"

        return HoldingChange(
            holding_key=key,
            change_type=change_type,
            previous=(
                None
                if previous is None
                else previous.comparison_payload()
            ),
            current=(
                None
                if current is None
                else current.comparison_payload()
            ),
            quantity=ScalarChange.between(
                None
                if previous is None
                else previous.quantity,
                None
                if current is None
                else current.quantity,
            ),
            unit_price=ScalarChange.between(
                None
                if previous is None
                else previous.unit_price,
                None
                if current is None
                else current.unit_price,
            ),
            market_value=ScalarChange.between(
                None
                if previous is None
                else previous.market_value,
                None
                if current is None
                else current.market_value,
            ),
            weight=ScalarChange.between(
                None
                if previous is None
                else previous.weight,
                None
                if current is None
                else current.weight,
            ),
        )

    @staticmethod
    def _equivalent(
        previous: HistoricalHolding,
        current: HistoricalHolding,
    ) -> bool:
        return (
            previous.comparison_payload()
            == current.comparison_payload()
            and previous.quantity
            == current.quantity
            and previous.unit_price
            == current.unit_price
            and previous.market_value
            == current.market_value
            and previous.weight
            == current.weight
        )

    @staticmethod
    def _index(
        holdings: object,
        *,
        field_name: str,
    ) -> dict[str, HistoricalHolding]:
        if not isinstance(
            holdings,
            tuple,
        ):
            raise TypeError(
                f"{field_name} must be a tuple"
            )

        indexed: dict[
            str,
            HistoricalHolding,
        ] = {}

        for holding in holdings:
            if not isinstance(
                holding,
                HistoricalHolding,
            ):
                raise TypeError(
                    f"{field_name} must contain only HistoricalHolding values"
                )

            if holding.holding_key in indexed:
                raise ValueError(
                    f"{field_name} contains duplicate holding_key "
                    f"{holding.holding_key}"
                )

            indexed[
                holding.holding_key
            ] = holding

        return indexed
