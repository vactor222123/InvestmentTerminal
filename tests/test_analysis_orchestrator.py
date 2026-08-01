"""
Tests for AnalysisOrchestrator.
"""

from unittest.mock import Mock

import pytest

from investment_terminal.exporters.analysis_exporter import (
    AnalysisExportPackage,
)
from investment_terminal.services.analysis_orchestrator import (
    AnalysisOrchestrator,
)


def create_orchestrator(
    technical_analysis_service: Mock,
    technical_score_service: Mock,
    fundamental_client: Mock,
    fundamental_score_service: Mock,
    decision_engine: Mock,
    exporter: Mock,
) -> AnalysisOrchestrator:
    return AnalysisOrchestrator(
        technical_analysis_service=(
            technical_analysis_service
        ),
        technical_score_service=(
            technical_score_service
        ),
        fundamental_client=fundamental_client,
        fundamental_score_service=(
            fundamental_score_service
        ),
        decision_engine=decision_engine,
        exporter=exporter,
    )


def test_run_executes_full_pipeline(
    tmp_path,
) -> None:
    technical_analysis = Mock()
    technical_score = Mock()
    fundamental_snapshot = Mock()
    fundamental_score = Mock()
    decision = Mock()
    package = Mock(
        spec=AnalysisExportPackage
    )

    technical_analysis_service = Mock()
    technical_analysis_service.analyze.return_value = (
        technical_analysis
    )

    technical_score_service = Mock()
    technical_score_service.score_analysis.return_value = (
        technical_score
    )

    fundamental_client = Mock()
    fundamental_client.get_fundamentals.return_value = (
        fundamental_snapshot
    )

    fundamental_score_service = Mock()
    fundamental_score_service.score_snapshot.return_value = (
        fundamental_score
    )

    decision_engine = Mock()
    decision_engine.evaluate.return_value = decision

    exporter = Mock()
    exporter.build_package.return_value = package
    exporter.save_json.return_value = (
        tmp_path / "MSFT_analysis.json"
    )

    orchestrator = create_orchestrator(
        technical_analysis_service,
        technical_score_service,
        fundamental_client,
        fundamental_score_service,
        decision_engine,
        exporter,
    )

    result = orchestrator.run(
        symbol=" msft ",
        resolution=" d ",
        currency=" usd ",
        output_dir=tmp_path,
    )

    technical_analysis_service.analyze.assert_called_once_with(
        symbol="MSFT",
        resolution="D",
    )

    technical_score_service.score_analysis.assert_called_once_with(
        technical_analysis
    )

    fundamental_client.get_fundamentals.assert_called_once_with(
        symbol="MSFT",
        currency="USD",
    )

    fundamental_score_service.score_snapshot.assert_called_once_with(
        fundamental_snapshot
    )

    decision_engine.evaluate.assert_called_once()

    decision_call = (
        decision_engine.evaluate.call_args.kwargs
    )

    assert (
        decision_call["technical_analysis"]
        is technical_analysis
    )
    assert (
        decision_call["technical_score"]
        is technical_score
    )
    assert (
        decision_call["fundamental_snapshot"]
        is fundamental_snapshot
    )
    assert (
        decision_call["fundamental_score"]
        is fundamental_score
    )

    exporter.build_package.assert_called_once()

    package_call = (
        exporter.build_package.call_args.kwargs
    )

    assert package_call["decision"] is decision
    assert (
        package_call["generated_at"]
        == decision_call["generated_at"]
    )

    exporter.save_json.assert_called_once_with(
        package=package,
        output_path=(
            tmp_path / "MSFT_analysis.json"
        ),
    )

    assert result.package is package
    assert result.output_path == (
        tmp_path / "MSFT_analysis.json"
    )


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "   ",
        None,
    ],
)
def test_run_rejects_invalid_symbol(
    symbol,
) -> None:
    orchestrator = create_orchestrator(
        Mock(),
        Mock(),
        Mock(),
        Mock(),
        Mock(),
        Mock(),
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        orchestrator.run(symbol=symbol)


def test_run_uses_json_filename(
    tmp_path,
) -> None:
    technical_analysis_service = Mock()
    technical_analysis_service.analyze.return_value = Mock()

    technical_score_service = Mock()
    technical_score_service.score_analysis.return_value = Mock()

    fundamental_client = Mock()
    fundamental_client.get_fundamentals.return_value = Mock()

    fundamental_score_service = Mock()
    fundamental_score_service.score_snapshot.return_value = Mock()

    decision_engine = Mock()
    decision_engine.evaluate.return_value = Mock()

    exporter = Mock()
    exporter.build_package.return_value = Mock()
    exporter.save_json.return_value = (
        tmp_path / "AAPL_analysis.json"
    )

    result = create_orchestrator(
        technical_analysis_service,
        technical_score_service,
        fundamental_client,
        fundamental_score_service,
        decision_engine,
        exporter,
    ).run(
        symbol="AAPL",
        output_dir=tmp_path,
    )

    assert result.output_path.name == (
        "AAPL_analysis.json"
    )