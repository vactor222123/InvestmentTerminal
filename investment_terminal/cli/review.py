"""Run the integrated deterministic investment-review workflow."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from investment_terminal.application.investment_review_workflow_models import (
    InvestmentReviewWorkflowRun,
    InvestmentReviewWorkflowStageResult,
    WorkflowArtifactIdentity,
)
from investment_terminal.cli import portfolio_ranking
from investment_terminal.cli.compare_history import (
    _build_service as build_snapshot_comparison_service,
)
from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_snapshot_service import (
    HistoricalSnapshotService,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.history.integrated_review_comparison_service import (
    IntegratedReviewComparisonService,
)
from investment_terminal.history.integrated_review_history_service import (
    HistoricalProjectionAfterArchiveError,
    IntegratedReviewHistoryService,
)
from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)
from investment_terminal.review.integrated_evidence_assembly import (
    IntegratedInvestmentReviewEvidenceAssembler,
)
from investment_terminal.review.integrated_review_package_service import (
    IntegratedReviewPackageService,
)
from investment_terminal.utils.atomic_write import (
    write_json_atomic,
)


DEFAULT_REVIEW_OUTPUT = Path("output") / "investment_review_package.json"
DEFAULT_WORKFLOW_OUTPUT = Path("output") / "investment_review_workflow.json"
DEFAULT_HISTORY_ROOT = Path("data") / "history"


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    """One complete report plus an optional operational failure."""

    workflow: InvestmentReviewWorkflowRun
    error: Exception | None = None


def main(
    argv: Sequence[str] | None = None,
) -> InvestmentReviewWorkflowRun:
    parser = build_argument_parser()
    options = parser.parse_args(
        argv
    )
    try:
        execution = run(
            options
        )
    except (
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        parser.error(
            str(
                exc
            )
        )

    result = execution.workflow
    payload = result.to_dict()
    write_json_atomic(
        options.workflow_output,
        payload,
        indent=2,
        trailing_newline=True,
    )

    if execution.error is not None:
        parser.error(
            str(
                execution.error
            ).strip()
            or execution.error.__class__.__name__
        )

    if options.print_json:
        print(
            json.dumps(
                payload,
                indent=2,
                allow_nan=False,
            )
        )
    else:
        print(
            f"Workflow {result.run_id}: {result.status}"
        )
        print(
            f"Review Package: {options.review_output}"
        )
        print(
            f"Workflow report: {options.workflow_output}"
        )

    return result


def run(
    options: argparse.Namespace,
) -> WorkflowExecution:
    run_id = str(
        uuid4()
    )
    run_started = _now()
    stages: list[InvestmentReviewWorkflowStageResult] = []
    market_started = _now()
    try:
        market = portfolio_ranking.main(
            _ranking_arguments(
                options
            )
        )
    except Exception as exc:
        stages.append(
            _failed_stage(
                "REFRESH_DATA",
                started_at=market_started,
                completed_at=_now(),
                error=exc,
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    market_completed = _now()
    stages.append(
        _completed_stage(
            "REFRESH_DATA",
            started_at=market_started,
            completed_at=market_completed,
        )
    )

    portfolio_started = _now()
    try:
        current_portfolio = CurrentPortfolioLoader.load(
            options.portfolio
        )
        portfolio = PortfolioSnapshotService().build(
            current_portfolio
        )
    except Exception as exc:
        stages.append(
            _failed_stage(
                "VALIDATE_EVIDENCE",
                started_at=portfolio_started,
                completed_at=_now(),
                error=exc,
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    portfolio_completed = _now()

    evidence_started = _now()
    try:
        evidence = IntegratedInvestmentReviewEvidenceAssembler.assemble(
            assembled_at=_now(),
            portfolio=portfolio,
            current_state_market=market,
        )
    except Exception as exc:
        stages.append(
            _failed_stage(
                "VALIDATE_EVIDENCE",
                started_at=evidence_started,
                completed_at=_now(),
                error=exc,
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    evidence_completed = _now()
    stages.extend(
        (
            _completed_stage(
                "VALIDATE_EVIDENCE",
                started_at=evidence_started,
                completed_at=evidence_completed,
                warnings=tuple(
                    f"Missing optional evidence: {name}"
                    for name in evidence.missing_evidence
                ),
            ),
            _completed_stage(
                "ANALYZE_PORTFOLIO",
                started_at=portfolio_started,
                completed_at=portfolio_completed,
            ),
            _completed_stage(
                "ANALYZE_MARKET",
                started_at=market_started,
                completed_at=market_completed,
            ),
        )
    )

    review_started = _now()
    try:
        review = IntegratedReviewPackageService.generate_and_export(
            evidence,
            options.review_output,
        )
    except Exception as exc:
        stages.append(
            _failed_stage(
                "GENERATE_REVIEW_PACKAGE",
                started_at=review_started,
                completed_at=_now(),
                error=exc,
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    review_completed = _now()
    stages.append(
        _completed_stage(
            "GENERATE_REVIEW_PACKAGE",
            started_at=review_started,
            completed_at=review_completed,
            artifacts=(
                WorkflowArtifactIdentity(
                    artifact_type="REVIEW_PACKAGE",
                    artifact_id=str(
                        review.output_path
                    ),
                ),
            ),
        )
    )

    history_started = _now()
    try:
        history, comparison = _history_services(
            options
        )
        history_result = history.preserve_and_project(
            review.output_path,
            product_version=options.product_version,
            package_id=run_id,
        )
    except HistoricalProjectionAfterArchiveError as exc:
        failed_at = _now()
        stages.extend(
            (
                _completed_stage(
                    "ARCHIVE_HISTORY",
                    started_at=history_started,
                    completed_at=failed_at,
                    artifacts=(
                        WorkflowArtifactIdentity(
                            artifact_type="HISTORICAL_SNAPSHOT",
                            artifact_id=exc.snapshot.snapshot_id,
                        ),
                    ),
                ),
                _failed_stage(
                    "PROJECT_HISTORY",
                    started_at=history_started,
                    completed_at=failed_at,
                    error=exc.cause,
                ),
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    except Exception as exc:
        stages.append(
            _failed_stage(
                "ARCHIVE_HISTORY",
                started_at=history_started,
                completed_at=_now(),
                error=exc,
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    history_completed = _now()
    stages.extend(
        (
            _completed_stage(
                "ARCHIVE_HISTORY",
                started_at=history_started,
                completed_at=history_completed,
                artifacts=(
                    WorkflowArtifactIdentity(
                        artifact_type="HISTORICAL_SNAPSHOT",
                        artifact_id=history_result.snapshot.snapshot_id,
                    ),
                ),
            ),
            _completed_stage(
                "PROJECT_HISTORY",
                started_at=history_started,
                completed_at=history_completed,
                artifacts=(
                    WorkflowArtifactIdentity(
                        artifact_type="HISTORY_PROJECTION",
                        artifact_id=history_result.snapshot.snapshot_id,
                    ),
                ),
            ),
        )
    )

    comparison_started = _now()
    try:
        comparison_result = comparison.compare_previous(
            history_result.snapshot.snapshot_id
        )
    except Exception as exc:
        stages.append(
            _failed_stage(
                "COMPARE_CHANGES",
                started_at=comparison_started,
                completed_at=_now(),
                error=exc,
            )
        )
        return _failed_execution(
            run_id=run_id,
            run_started=run_started,
            stages=stages,
            error=exc,
        )
    comparison_completed = _now()
    stages.append(
        _completed_stage(
            "COMPARE_CHANGES",
            started_at=comparison_started,
            completed_at=comparison_completed,
            artifacts=(
                (
                    WorkflowArtifactIdentity(
                        artifact_type="SNAPSHOT_COMPARISON",
                        artifact_id=(
                            comparison_result.previous_snapshot_id
                            + ":"
                            + comparison_result.current_snapshot_id
                        ),
                    ),
                )
                if comparison_result.status == "COMPLETED"
                else ()
            ),
            warnings=(
                ()
                if comparison_result.status == "COMPLETED"
                else (
                    comparison_result.reason or comparison_result.status,
                )
            ),
        )
    )
    run_completed = _now()
    warnings = tuple(
        dict.fromkeys(
            warning
            for stage in tuple(
                stages
            )
            for warning in stage.warnings
        )
    )
    return WorkflowExecution(
        workflow=InvestmentReviewWorkflowRun(
            schema_version=InvestmentReviewWorkflowRun.SCHEMA_VERSION,
            run_id=run_id,
            started_at=run_started,
            completed_at=run_completed,
            stages=tuple(
                stages
            ),
            warnings=warnings,
        )
    )


def _failed_execution(
    *,
    run_id: str,
    run_started: datetime,
    stages: list[InvestmentReviewWorkflowStageResult],
    error: Exception,
) -> WorkflowExecution:
    failed_stage = stages[-1].stage
    completed_at = _now()
    existing = {
        stage.stage
        for stage in stages
    }
    for stage_name in InvestmentReviewWorkflowStageResult.STAGE_ORDER:
        if stage_name in existing:
            continue
        stages.append(
            _skipped_stage(
                stage_name,
                completed_at=completed_at,
                reason=(
                    f"Skipped because {failed_stage} failed"
                ),
            )
        )

    warnings = tuple(
        dict.fromkeys(
            warning
            for stage in stages
            for warning in stage.warnings
        )
    )
    return WorkflowExecution(
        workflow=InvestmentReviewWorkflowRun(
            schema_version=InvestmentReviewWorkflowRun.SCHEMA_VERSION,
            run_id=run_id,
            started_at=run_started,
            completed_at=completed_at,
            stages=tuple(
                stages
            ),
            warnings=warnings,
        ),
        error=error,
    )


def _history_services(
    options: argparse.Namespace,
) -> tuple[
    IntegratedReviewHistoryService,
    IntegratedReviewComparisonService,
]:
    options.history_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    store = HistoricalSQLiteStore(
        options.history_database
    )
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()
    snapshots = HistoricalSnapshotRepository(
        store
    )
    states = HistoricalImportStateRepository(
        store
    )
    history = IntegratedReviewHistoryService(
        snapshot_service=HistoricalSnapshotService(
            archive=HistoricalSnapshotArchive(
                options.history_root
            ),
            manifest=HistoricalSnapshotManifest(
                options.history_manifest
            ),
        ),
        manifest_import_service=HistoricalManifestImportService(
            manifest=HistoricalSnapshotManifest(
                options.history_manifest
            ),
            repository=snapshots,
            state_repository=states,
        ),
        import_pipeline=HistoricalImportPipeline(
            store=store,
            loader=HistoricalReviewPackageLoader(
                options.history_root
            ),
            state_repository=states,
        ),
    )
    comparison = IntegratedReviewComparisonService(
        snapshot_repository=snapshots,
        import_state_repository=states,
        comparison_service=build_snapshot_comparison_service(
            store
        ),
    )
    return history, comparison


def _completed_stage(
    stage: str,
    *,
    started_at: datetime,
    completed_at: datetime,
    artifacts: tuple[WorkflowArtifactIdentity, ...] = (),
    warnings: tuple[str, ...] = (),
) -> InvestmentReviewWorkflowStageResult:
    return InvestmentReviewWorkflowStageResult(
        stage=stage,
        status="COMPLETED",
        depends_on=InvestmentReviewWorkflowStageResult.STAGE_DEPENDENCIES[
            stage
        ],
        started_at=started_at,
        completed_at=completed_at,
        artifact_identities=artifacts,
        warnings=warnings,
    )


def _failed_stage(
    stage: str,
    *,
    started_at: datetime,
    completed_at: datetime,
    error: Exception,
) -> InvestmentReviewWorkflowStageResult:
    return InvestmentReviewWorkflowStageResult(
        stage=stage,
        status="FAILED",
        depends_on=InvestmentReviewWorkflowStageResult.STAGE_DEPENDENCIES[
            stage
        ],
        started_at=started_at,
        completed_at=completed_at,
        failure_reason=(
            str(
                error
            ).strip()
            or error.__class__.__name__
        ),
    )


def _skipped_stage(
    stage: str,
    *,
    completed_at: datetime,
    reason: str,
) -> InvestmentReviewWorkflowStageResult:
    return InvestmentReviewWorkflowStageResult(
        stage=stage,
        status="SKIPPED",
        depends_on=InvestmentReviewWorkflowStageResult.STAGE_DEPENDENCIES[
            stage
        ],
        started_at=None,
        completed_at=completed_at,
        skip_reason=reason,
    )


def _ranking_arguments(
    options: argparse.Namespace,
) -> list[str]:
    return [
        "--universe",
        options.universe,
        "--capital",
        str(
            options.capital
        ),
        "--allocation-size",
        str(
            options.allocation_size
        ),
        "--profile",
        options.profile,
        "--currency",
        options.currency,
        "--resolution",
        options.resolution,
        "--output",
        str(
            options.market_output
        ),
    ]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh and analyze market data, generate a Review Package, "
            "preserve/project History, and compare the previous snapshot."
        )
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=CurrentPortfolioLoader.DEFAULT_PATH,
    )
    parser.add_argument(
        "--universe",
        default=portfolio_ranking.DEFAULT_UNIVERSE_KEY,
    )
    parser.add_argument(
        "--capital",
        type=portfolio_ranking.positive_float,
        default=portfolio_ranking.DEFAULT_ALLOCATION_CAPITAL,
    )
    parser.add_argument(
        "--allocation-size",
        type=portfolio_ranking.positive_int,
        default=portfolio_ranking.DEFAULT_ALLOCATION_SIZE,
    )
    parser.add_argument(
        "--profile",
        choices=portfolio_ranking.ALLOCATION_PROFILES,
        default=portfolio_ranking.DEFAULT_ALLOCATION_PROFILE,
    )
    parser.add_argument(
        "--currency",
        type=portfolio_ranking.non_empty_upper_text,
        default=portfolio_ranking.DEFAULT_CURRENCY,
    )
    parser.add_argument(
        "--resolution",
        choices=portfolio_ranking.SUPPORTED_RESOLUTIONS,
        default=portfolio_ranking.DEFAULT_RESOLUTION,
    )
    parser.add_argument(
        "--market-output",
        type=Path,
        default=Path("output") / "integrated_market_analysis.json",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
    )
    parser.add_argument(
        "--history-root",
        type=Path,
        default=DEFAULT_HISTORY_ROOT,
    )
    parser.add_argument(
        "--history-manifest",
        type=Path,
        default=DEFAULT_HISTORY_ROOT / "manifest.jsonl",
    )
    parser.add_argument(
        "--history-database",
        type=Path,
        default=DEFAULT_HISTORY_ROOT / "history.db",
    )
    parser.add_argument(
        "--workflow-output",
        type=Path,
        default=DEFAULT_WORKFLOW_OUTPUT,
    )
    parser.add_argument(
        "--product-version",
        default=None,
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
    )
    return parser


def _now() -> datetime:
    return datetime.now(
        timezone.utc
    )


if __name__ == "__main__":
    main()
