import pytest

from investment_terminal.analysis.current_state_quality import (
    AnalysisDataQuality,
    AnalysisDataQualityStatus,
    require_ready_analysis_quality,
)


def test_ready_quality_is_accepted():
    require_ready_analysis_quality(
        AnalysisDataQuality(
            AnalysisDataQualityStatus.READY,
            "ok",
        )
    )


@pytest.mark.parametrize(
    "status",
    [
        AnalysisDataQualityStatus.STALE,
        AnalysisDataQualityStatus.UNAVAILABLE,
        AnalysisDataQualityStatus.PARTIAL,
    ],
)
def test_non_ready_quality_fails_closed(status):
    with pytest.raises(ValueError):
        require_ready_analysis_quality(
            AnalysisDataQuality(
                status,
                "not ready",
            )
        )
