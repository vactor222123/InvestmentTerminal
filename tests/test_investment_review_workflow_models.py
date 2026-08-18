"""Tests for the integrated investment-review workflow run contract."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json

import pytest

from investment_terminal.application.investment_review_workflow_models import (
    InvestmentReviewWorkflowRun,
    InvestmentReviewWorkflowStageResult,
    WorkflowArtifactIdentity,
)


STARTED_AT = datetime(
    2026,
    8,
    18,
    10,
    0,
    tzinfo=timezone.utc,
)


def artifact(
    artifact_type: str = "review_package",
    artifact_id: str = "review-2026-08-18",
) -> WorkflowArtifactIdentity:
    return WorkflowArtifactIdentity(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
    )


def stage_result(
    stage: str,
    *,
    status: str = "COMPLETED",
    minute: int = 1,
    artifacts: tuple[WorkflowArtifactIdentity, ...] = (),
    failure_reason: str | None = None,
    skip_reason: str | None = None,
) -> InvestmentReviewWorkflowStageResult:
    dependencies = (
        InvestmentReviewWorkflowStageResult.STAGE_DEPENDENCIES[
            stage
        ]
    )
    completed_at = STARTED_AT + timedelta(
        minutes=minute
    )
    return InvestmentReviewWorkflowStageResult(
        stage=stage,
        status=status,
        depends_on=dependencies,
        started_at=(
            None
            if status == "SKIPPED"
            else completed_at - timedelta(
                seconds=30
            )
        ),
        completed_at=completed_at,
        artifact_identities=artifacts,
        failure_reason=failure_reason,
        skip_reason=skip_reason,
    )


def completed_stages(
) -> tuple[InvestmentReviewWorkflowStageResult, ...]:
    return tuple(
        stage_result(
            stage,
            minute=index,
            artifacts=(
                (
                    artifact(),
                )
                if stage == "GENERATE_REVIEW_PACKAGE"
                else ()
            ),
        )
        for index, stage in enumerate(
            InvestmentReviewWorkflowStageResult.STAGE_ORDER,
            start=1,
        )
    )


def workflow_run(
    stages: tuple[InvestmentReviewWorkflowStageResult, ...]
    | None = None,
) -> InvestmentReviewWorkflowRun:
    return InvestmentReviewWorkflowRun(
        schema_version="1.0",
        run_id="review-run-2026-08-18",
        started_at=STARTED_AT,
        completed_at=STARTED_AT + timedelta(
            minutes=10
        ),
        stages=(
            completed_stages()
            if stages is None
            else stages
        ),
        warnings=(
            "External context coverage is partial.",
        ),
    )


def test_completed_workflow_is_immutable_and_serializable() -> None:
    result = workflow_run()

    assert result.status == "COMPLETED"
    assert result.stage(
        " generate_review_package "
    ).artifact_identities == (
        artifact(),
    )
    assert json.loads(
        json.dumps(
            result.to_dict(),
            allow_nan=False,
        )
    )["status"] == "COMPLETED"

    with pytest.raises(
        FrozenInstanceError
    ):
        result.run_id = "changed"  # type: ignore[misc]


def test_artifact_identity_normalizes_stable_text() -> None:
    identity = WorkflowArtifactIdentity(
        artifact_type=" review_package ",
        artifact_id=" package-1 ",
    )

    assert identity.identity_key == (
        "REVIEW_PACKAGE",
        "package-1",
    )
    assert identity.to_dict() == {
        "artifact_type": "REVIEW_PACKAGE",
        "artifact_id": "package-1",
    }


@pytest.mark.parametrize(
    ("status", "kwargs", "message"),
    (
        (
            "FAILED",
            {},
            "FAILED requires failure_reason",
        ),
        (
            "SKIPPED",
            {},
            "SKIPPED requires skip_reason",
        ),
        (
            "COMPLETED",
            {
                "failure_reason": "unexpected",
            },
            "failure_reason is only valid",
        ),
    ),
)
def test_stage_status_requires_matching_reason(
    status: str,
    kwargs: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        stage_result(
            "REFRESH_DATA",
            status=status,
            **kwargs,
        )


def test_skipped_stage_cannot_claim_artifacts() -> None:
    with pytest.raises(
        ValueError,
        match="SKIPPED cannot produce artifact identities",
    ):
        stage_result(
            "COMPARE_CHANGES",
            status="SKIPPED",
            skip_reason="No previous compatible snapshot.",
            artifacts=(
                artifact(
                    "comparison",
                    "comparison-1",
                ),
            ),
        )


def test_stage_rejects_incorrect_dependency_contract() -> None:
    with pytest.raises(
        ValueError,
        match="ANALYZE_MARKET depends_on",
    ):
        InvestmentReviewWorkflowStageResult(
            stage="ANALYZE_MARKET",
            status="COMPLETED",
            depends_on=(
                "REFRESH_DATA",
            ),
            started_at=STARTED_AT,
            completed_at=STARTED_AT,
        )


def test_run_requires_every_stage_in_canonical_order() -> None:
    with pytest.raises(
        ValueError,
        match="canonical order",
    ):
        workflow_run(
            stages=tuple(
                reversed(
                    completed_stages()
                )
            )
        )


def test_failed_dependency_forces_dependent_stage_to_skip() -> None:
    stages = list(
        completed_stages()
    )
    stages[1] = stage_result(
        "VALIDATE_EVIDENCE",
        status="FAILED",
        minute=2,
        failure_reason="Evidence freshness validation failed.",
    )
    stages[2] = stage_result(
        "ANALYZE_PORTFOLIO",
        status="SKIPPED",
        minute=3,
        skip_reason="Required evidence validation failed.",
    )
    stages[3] = stage_result(
        "ANALYZE_MARKET",
        status="SKIPPED",
        minute=4,
        skip_reason="Required evidence validation failed.",
    )
    for index, stage in enumerate(
        InvestmentReviewWorkflowStageResult.STAGE_ORDER[4:],
        start=5,
    ):
        stages[index - 1] = stage_result(
            stage,
            status="SKIPPED",
            minute=index,
            skip_reason="A required upstream stage did not complete.",
        )

    result = workflow_run(
        stages=tuple(
            stages
        )
    )

    assert result.status == "FAILED"
    assert result.stage(
        "VALIDATE_EVIDENCE"
    ).failure_reason is not None

    invalid = list(
        stages
    )
    invalid[2] = stage_result(
        "ANALYZE_PORTFOLIO",
        minute=3,
    )
    with pytest.raises(
        ValueError,
        match="dependencies are not completed",
    ):
        workflow_run(
            stages=tuple(
                invalid
            )
        )


def test_first_run_comparison_can_be_explicitly_skipped() -> None:
    stages = list(
        completed_stages()
    )
    stages[-1] = stage_result(
        "COMPARE_CHANGES",
        status="SKIPPED",
        minute=8,
        skip_reason="No previous compatible snapshot.",
    )

    result = workflow_run(
        stages=tuple(
            stages
        )
    )

    assert result.status == "COMPLETED_WITH_SKIPS"
    assert result.stage(
        "COMPARE_CHANGES"
    ).skip_reason == "No previous compatible snapshot."


@pytest.mark.parametrize(
    ("field", "value"),
    (
        (
            "started_at",
            datetime(
                2026,
                8,
                18,
                10,
                0,
            ),
        ),
        (
            "completed_at",
            STARTED_AT - timedelta(
                seconds=1
            ),
        ),
    ),
)
def test_run_rejects_invalid_time_boundary(
    field: str,
    value: datetime,
) -> None:
    values = {
        "schema_version": "1.0",
        "run_id": "run-1",
        "started_at": STARTED_AT,
        "completed_at": STARTED_AT + timedelta(
            minutes=10
        ),
        "stages": completed_stages(),
    }
    values[field] = value

    with pytest.raises(
        (TypeError, ValueError)
    ):
        InvestmentReviewWorkflowRun(
            **values  # type: ignore[arg-type]
        )


def test_run_rejects_unsupported_schema_version() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported workflow schema_version",
    ):
        InvestmentReviewWorkflowRun(
            schema_version="2.0",
            run_id="run-1",
            started_at=STARTED_AT,
            completed_at=STARTED_AT + timedelta(
                minutes=10
            ),
            stages=completed_stages(),
        )
