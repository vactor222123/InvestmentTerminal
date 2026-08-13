"""
Production monotonic Decimal clock for process-local rate limiting.
"""

from collections.abc import Callable
from decimal import Decimal
from time import monotonic


class GroundedAIServerMonotonicDecimalClock:
    def __init__(
        self,
        *,
        monotonic_source: Callable[[], float] = monotonic,
    ) -> None:
        if not callable(monotonic_source):
            raise TypeError(
                "monotonic_source must be callable"
            )
        self._source = monotonic_source

    def __call__(self) -> Decimal:
        value = self._source()
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                "monotonic source must return int or float"
            )
        return Decimal(
            str(value)
        )
