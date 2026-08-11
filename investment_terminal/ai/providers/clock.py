"""
Provider-neutral clock boundary for deterministic time-dependent transport logic.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class GroundedProviderClock(ABC):
    @abstractmethod
    def now_utc(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""


class SystemGroundedProviderClock(
    GroundedProviderClock
):
    def now_utc(self) -> datetime:
        return datetime.now(
            timezone.utc
        )
