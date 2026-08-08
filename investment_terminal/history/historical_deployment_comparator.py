"""
Pure comparator for normalized historical deployment records.
"""

from investment_terminal.history.historical_comparison_models import (
    DeploymentChange,
    ScalarChange,
)
from investment_terminal.history.historical_deployment_models import (
    HistoricalDeployment,
)


class HistoricalDeploymentComparator:
    """Compare deployment records strictly by stable deployment_key."""

    def compare(
        self,
        *,
        previous: tuple[HistoricalDeployment, ...],
        current: tuple[HistoricalDeployment, ...],
    ) -> tuple[DeploymentChange, ...]:
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
        previous: HistoricalDeployment | None,
        current: HistoricalDeployment | None,
    ) -> DeploymentChange:
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

        return DeploymentChange(
            deployment_key=key,
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
            amount=ScalarChange.between(
                None
                if previous is None
                else previous.amount,
                None
                if current is None
                else current.amount,
            ),
            share=ScalarChange.between(
                None
                if previous is None
                else previous.share,
                None
                if current is None
                else current.share,
            ),
        )

    @staticmethod
    def _equivalent(
        previous: HistoricalDeployment,
        current: HistoricalDeployment,
    ) -> bool:
        return (
            previous.comparison_payload()
            == current.comparison_payload()
            and previous.amount
            == current.amount
            and previous.share
            == current.share
        )

    @staticmethod
    def _index(
        deployments: object,
        *,
        field_name: str,
    ) -> dict[str, HistoricalDeployment]:
        if not isinstance(
            deployments,
            tuple,
        ):
            raise TypeError(
                f"{field_name} must be a tuple"
            )

        indexed: dict[
            str,
            HistoricalDeployment,
        ] = {}

        for deployment in deployments:
            if not isinstance(
                deployment,
                HistoricalDeployment,
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "HistoricalDeployment values"
                )

            key = deployment.deployment_key
            if key in indexed:
                raise ValueError(
                    f"{field_name} contains duplicate deployment_key {key}"
                )

            indexed[
                key
            ] = deployment

        return indexed
