"""Current-state analysis quality and failure-surface contracts."""

from dataclasses import dataclass
from enum import Enum


class AnalysisDataQualityStatus(str, Enum):
    READY = "READY"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True)
class AnalysisDataQuality:
    status: AnalysisDataQualityStatus
    message: str


def require_ready_analysis_quality(
    quality: AnalysisDataQuality,
) -> None:
    """Fail closed when current-state data cannot represent a live analysis."""
    if quality.status != AnalysisDataQualityStatus.READY:
        raise ValueError(
            f"current-state analysis is not ready: {quality.status}"
        )
