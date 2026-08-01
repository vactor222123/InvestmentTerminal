"""
Tests for UniverseAnalysisService.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from investment_terminal.exporters.analysis_exporter import (
    AnalysisExportPackage,
)
from investment_terminal.services.analysis_orchestrator import (
    AnalysisRunResult,
)
from investment_terminal.services.universe_analysis_service import (
    UniverseAnalysisService,
)


def create_run_result(
    symbol: str,
    output_dir: Path,
) -> AnalysisRunResult:
    package = Mock(
        spec=AnalysisExportPackage
    )
    package.symbol = symbol

    return AnalysisRunResult(
        package=package,
        output_path=(
            output_dir
            / f"{symbol}_analysis.json"
        ),
    )


def test_analyze_runs_all_unique_symbols(
    tmp_path,
) -> None:
    orchestrator = Mock()

    orchestrator.run.side_effect = [
        create_run_result(
            "MSFT",
            tmp_path,
        ),
        create_run_result(
            "AAPL",
            tmp_path,
        ),
        create_run_result(
            "GOOGL",
            tmp_path,
        ),
    ]

    result = UniverseAnalysisService(
        orchestrator=orchestrator
    ).analyze(
        symbols=[
            " msft ",
            "AAPL",
            "msft",
            " googl ",
        ],
        resolution=" d ",
        currency=" usd ",
        output_dir=tmp_path,
    )

    assert result.requested_symbols == (
        "MSFT",
        "AAPL",
        "GOOGL",
    )
    assert result.total_count == 3
    assert result.successful_count == 3
    assert result.failed_count == 0

    assert [
        package.symbol
        for package in result.successful_packages
    ] == [
        "MSFT",
        "AAPL",
        "GOOGL",
    ]

    assert orchestrator.run.call_count == 3

    orchestrator.run.assert_any_call(
        symbol="MSFT",
        resolution="D",
        currency="USD",
        output_dir=tmp_path,
    )
    orchestrator.run.assert_any_call(
        symbol="AAPL",
        resolution="D",
        currency="USD",
        output_dir=tmp_path,
    )
    orchestrator.run.assert_any_call(
        symbol="GOOGL",
        resolution="D",
        currency="USD",
        output_dir=tmp_path,
    )


def test_analyze_records_failure_and_continues(
    tmp_path,
) -> None:
    orchestrator = Mock()

    orchestrator.run.side_effect = [
        create_run_result(
            "MSFT",
            tmp_path,
        ),
        RuntimeError(
            "No historical candles"
        ),
        create_run_result(
            "GOOGL",
            tmp_path,
        ),
    ]

    result = UniverseAnalysisService(
        orchestrator=orchestrator
    ).analyze(
        symbols=[
            "MSFT",
            "AAPL",
            "GOOGL",
        ],
        output_dir=tmp_path,
        continue_on_error=True,
    )

    assert result.successful_count == 2
    assert result.failed_count == 1

    failure = result.failures[0]

    assert failure.symbol == "AAPL"
    assert failure.error_type == "RuntimeError"
    assert failure.message == (
        "No historical candles"
    )


def test_analyze_raises_when_continue_is_disabled(
    tmp_path,
) -> None:
    orchestrator = Mock()
    orchestrator.run.side_effect = RuntimeError(
        "Provider unavailable"
    )

    service = UniverseAnalysisService(
        orchestrator=orchestrator
    )

    with pytest.raises(
        RuntimeError,
        match="Provider unavailable",
    ):
        service.analyze(
            symbols=[
                "MSFT",
                "AAPL",
            ],
            output_dir=tmp_path,
            continue_on_error=False,
        )

    orchestrator.run.assert_called_once()


def test_analyze_preserves_requested_order(
    tmp_path,
) -> None:
    orchestrator = Mock()

    orchestrator.run.side_effect = [
        create_run_result(
            "NVDA",
            tmp_path,
        ),
        create_run_result(
            "META",
            tmp_path,
        ),
        create_run_result(
            "MSFT",
            tmp_path,
        ),
    ]

    result = UniverseAnalysisService(
        orchestrator=orchestrator
    ).analyze(
        symbols=[
            "NVDA",
            "META",
            "MSFT",
        ],
        output_dir=tmp_path,
    )

    assert result.requested_symbols == (
        "NVDA",
        "META",
        "MSFT",
    )

    assert [
        package.symbol
        for package in result.successful_packages
    ] == [
        "NVDA",
        "META",
        "MSFT",
    ]


@pytest.mark.parametrize(
    "symbols",
    [
        [],
        (),
    ],
)
def test_analyze_rejects_empty_symbols(
    symbols,
) -> None:
    service = UniverseAnalysisService(
        orchestrator=Mock()
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        service.analyze(symbols)


@pytest.mark.parametrize(
    "symbols",
    [
        "MSFT",
        {"MSFT", "AAPL"},
        None,
    ],
)
def test_analyze_rejects_invalid_collection(
    symbols,
) -> None:
    service = UniverseAnalysisService(
        orchestrator=Mock()
    )

    with pytest.raises(
        TypeError,
        match="list or tuple",
    ):
        service.analyze(symbols)


@pytest.mark.parametrize(
    "symbols",
    [
        ["MSFT", ""],
        ["MSFT", "   "],
        ["MSFT", None],
    ],
)
def test_analyze_rejects_invalid_symbol(
    symbols,
) -> None:
    service = UniverseAnalysisService(
        orchestrator=Mock()
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        service.analyze(symbols)