"""
Provider-neutral retry sleeper boundary.

The abstract sleeper keeps execution tests deterministic. The production
implementation delegates to time.sleep only when explicitly wired.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
import time


class GroundedProviderSleeper(ABC):
    """Boundary for applying one retry delay."""

    @abstractmethod
    def sleep(
        self,
        *,
        delay_seconds: Decimal,
    ) -> None:
        """Apply one non-negative retry delay."""


class TimeGroundedProviderSleeper(
    GroundedProviderSleeper
):
    """Production sleeper backed by time.sleep."""

    def sleep(
        self,
        *,
        delay_seconds: Decimal,
    ) -> None:
        if (
            not isinstance(delay_seconds, Decimal)
            or not delay_seconds.is_finite()
            or delay_seconds < 0
        ):
            raise ValueError(
                "delay_seconds must be a finite non-negative Decimal"
            )
        time.sleep(float(delay_seconds))
