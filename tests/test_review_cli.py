"""Hermetic end-to-end tests for the integrated review command."""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.review import (
    main,
)
from investment_terminal.history.integrated_review_history_service import (
    HistoricalProjectionAfterArchiveError,
)
from tests.test_compare_history_cli import (
    BASE_TIME,
    FIRST_ID,
    snapshot,
)
from tests.test_integrated_evidence_assembly import (
    assemble,
)


def arguments(
    tmp_path: Path,
) -> list[str]:
    history = tmp_path / "history"
    return [
        "--portfolio",
        "data/portfolios/current_portfolio.example.json",
        "--market-output",
        str(
            tmp_path / "market.json"
        ),
        "--review-output",
        str(
            tmp_path / "review.json"
        ),
        "--history-root",
        str(
            history
        ),
        "--history-manifest",
        str(
            history / "manifest.jsonl"
        ),
        "--history-database",
        str(
            history / "history.db"
        ),
        "--workflow-output",
        str(
            tmp_path / "workflow.json"
        ),
        "--product-version",
        "6.6.0",
    ]


def test_command_runs_complete_first_review_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market = assemble().current_state_market
    monkeypatch.setattr(
        "investment_terminal.cli.review.portfolio_ranking.main",
        lambda argv: market,
    )

    result = main(
        arguments(
            tmp_path
        )
    )

    assert result.status == "COMPLETED"
    assert all(
        stage.status == "COMPLETED"
        for stage in result.stages
    )
    assert (
        "No earlier historical snapshot exists"
        in result.stage(
            "COMPARE_CHANGES"
        ).warnings
    )
    review = json.loads(
        (tmp_path / "review.json").read_text(
            encoding="utf-8",
        )
    )
    assert review["schema_version"] == "1.0"
    assert len(review["sections"]) == 9
    report = json.loads(
        (tmp_path / "workflow.json").read_text(
            encoding="utf-8",
        )
    )
    assert report == result.to_dict()
    assert len(
        list(
            (tmp_path / "history").glob(
                "*/*/*.json"
            )
        )
    ) == 1


def test_second_command_run_produces_read_only_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market = assemble().current_state_market
    monkeypatch.setattr(
        "investment_terminal.cli.review.portfolio_ranking.main",
        lambda argv: market,
    )
    argv = arguments(
        tmp_path
    )

    first = main(
        argv
    )
    second = main(
        argv
    )

    comparison = second.stage(
        "COMPARE_CHANGES"
    )
    assert comparison.status == "COMPLETED"
    assert comparison.warnings == ()
    assert len(
        comparison.artifact_identities
    ) == 1
    assert first.run_id != second.run_id
    assert len(
        list(
            (tmp_path / "history").glob(
                "*/*/*.json"
            )
        )
    ) == 2


def test_argument_parser_reports_missing_portfolio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market = assemble().current_state_market
    monkeypatch.setattr(
        "investment_terminal.cli.review.portfolio_ranking.main",
        lambda argv: market,
    )
    argv = arguments(
        tmp_path
    )
    argv[1] = str(
        tmp_path / "missing.json"
    )

    with pytest.raises(
        SystemExit,
    ) as raised:
        main(
            argv
        )

    assert raised.value.code == 2
    report = json.loads(
        (tmp_path / "workflow.json").read_text(
            encoding="utf-8",
        )
    )
    statuses = {
        stage["stage"]: stage["status"]
        for stage in report["stages"]
    }
    assert statuses["REFRESH_DATA"] == "COMPLETED"
    assert statuses["VALIDATE_EVIDENCE"] == "FAILED"
    assert statuses["ANALYZE_PORTFOLIO"] == "SKIPPED"
    assert statuses["COMPARE_CHANGES"] == "SKIPPED"


def test_projection_failure_reports_registered_archive_before_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market = assemble().current_state_market
    archived = snapshot(
        FIRST_ID,
        generated_at=BASE_TIME,
    )

    class FailingHistory:
        def preserve_and_project(
            self,
            *args: object,
            **kwargs: object,
        ) -> None:
            cause = OSError(
                "projection unavailable"
            )
            raise HistoricalProjectionAfterArchiveError(
                snapshot=archived,
                cause=cause,
            )

    monkeypatch.setattr(
        "investment_terminal.cli.review.portfolio_ranking.main",
        lambda argv: market,
    )
    monkeypatch.setattr(
        "investment_terminal.cli.review._history_services",
        lambda options: (
            FailingHistory(),
            object(),
        ),
    )

    with pytest.raises(
        SystemExit,
    ) as raised:
        main(
            arguments(
                tmp_path
            )
        )

    assert raised.value.code == 2
    report = json.loads(
        (tmp_path / "workflow.json").read_text(
            encoding="utf-8",
        )
    )
    stages = {
        stage["stage"]: stage
        for stage in report["stages"]
    }
    assert stages["ARCHIVE_HISTORY"]["status"] == "COMPLETED"
    assert stages["ARCHIVE_HISTORY"]["artifact_identities"] == [
        {
            "artifact_type": "HISTORICAL_SNAPSHOT",
            "artifact_id": FIRST_ID,
        }
    ]
    assert stages["PROJECT_HISTORY"]["status"] == "FAILED"
    assert (
        stages["PROJECT_HISTORY"]["failure_reason"]
        == "projection unavailable"
    )
    assert stages["COMPARE_CHANGES"]["status"] == "SKIPPED"
