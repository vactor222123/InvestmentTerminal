"""
Tests for AssetAnalysisService.
"""

from unittest.mock import Mock

from investment_terminal.services.asset_analysis_service import (
    AssetAnalysisService,
)


def test_analyze_executes_complete_pipeline() -> None:
    technical_analysis = Mock()
    technical_score = Mock()
    fundamental_snapshot = Mock()
    fundamental_score = Mock()
    decision = Mock()

    technical_service = Mock()
    technical_service.analyze.return_value = (
        technical_analysis
    )

    fundamental_client = Mock()
    fundamental_client.get_fundamentals.return_value = (
        fundamental_snapshot
    )

    service = AssetAnalysisService(
        technical_analysis_service=technical_service,
        fundamental_client=fundamental_client,
    )

    service.technical_score_service = Mock()
    service.technical_score_service.score_analysis.return_value = (
        technical_score
    )

    service.fundamental_score_service = Mock()
    service.fundamental_score_service.score_snapshot.return_value = (
        fundamental_score
    )

    service.decision_engine = Mock()
    service.decision_engine.evaluate.return_value = (
        decision
    )

    result = service.analyze(
        symbol="MSFT",
        resolution="D",
        currency="USD",
    )

    assert result is decision

    technical_service.analyze.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
    )

    fundamental_client.get_fundamentals.assert_called_once_with(
        symbol="MSFT",
        currency="USD",
    )

    service.technical_score_service.score_analysis.assert_called_once_with(
        technical_analysis
    )

    service.fundamental_score_service.score_snapshot.assert_called_once_with(
        fundamental_snapshot
    )

    service.decision_engine.evaluate.assert_called_once()