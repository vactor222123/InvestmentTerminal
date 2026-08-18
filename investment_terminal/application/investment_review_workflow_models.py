"""Contracts for one integrated investment-review workflow run."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class WorkflowArtifactIdentity:
    """Stable identity of an artifact produced by one workflow stage."""

    artifact_type: str
    artifact_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_type",
            normalize_required_text(
                self.artifact_type,
                field_name="artifact_type",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "artifact_id",
            normalize_required_text(
                self.artifact_id,
                field_name="artifact_id",
            ),
        )

    @property
    def identity_key(self) -> tuple[str, str]:
        return (
            self.artifact_type,
            self.artifact_id,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
        }


@dataclass(frozen=True, slots=True)
class InvestmentReviewWorkflowStageResult:
    """Immutable outcome of one canonical workflow stage."""

    stage: str
    status: str
    depends_on: tuple[str, ...]
    completed_at: datetime
    started_at: datetime | None = None
    artifact_identities: tuple[WorkflowArtifactIdentity, ...] = ()
    warnings: tuple[str, ...] = ()
    failure_reason: str | None = None
    skip_reason: str | None = None

    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = (
        "COMPLETED",
        "SKIPPED",
        "FAILED",
    )
    STAGE_DEPENDENCIES: ClassVar[dict[str, tuple[str, ...]]] = {
        "REFRESH_DATA": (),
        "VALIDATE_EVIDENCE": (
            "REFRESH_DATA",
        ),
        "ANALYZE_PORTFOLIO": (
            "VALIDATE_EVIDENCE",
        ),
        "ANALYZE_MARKET": (
            "VALIDATE_EVIDENCE",
        ),
        "GENERATE_REVIEW_PACKAGE": (
            "ANALYZE_PORTFOLIO",
            "ANALYZE_MARKET",
        ),
        "ARCHIVE_HISTORY": (
            "GENERATE_REVIEW_PACKAGE",
        ),
        "PROJECT_HISTORY": (
            "ARCHIVE_HISTORY",
        ),
        "COMPARE_CHANGES": (
            "PROJECT_HISTORY",
        ),
    }
    STAGE_ORDER: ClassVar[tuple[str, ...]] = tuple(
        STAGE_DEPENDENCIES
    )

    def __post_init__(self) -> None:
        normalized_stage = normalize_required_text(
            self.stage,
            field_name="stage",
            uppercase=True,
        )
        if normalized_stage not in self.STAGE_DEPENDENCIES:
            raise ValueError(
                "stage must be one of: "
                + ", ".join(
                    self.STAGE_ORDER
                )
            )
        object.__setattr__(
            self,
            "stage",
            normalized_stage,
        )

        normalized_status = normalize_required_text(
            self.status,
            field_name="status",
            uppercase=True,
        )
        if normalized_status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(
                    self.SUPPORTED_STATUSES
                )
            )
        object.__setattr__(
            self,
            "status",
            normalized_status,
        )

        normalized_dependencies = self._normalize_text_tuple(
            self.depends_on,
            field_name="depends_on",
            uppercase=True,
        )
        expected_dependencies = self.STAGE_DEPENDENCIES[
            normalized_stage
        ]
        if normalized_dependencies != expected_dependencies:
            raise ValueError(
                f"{normalized_stage} depends_on must equal "
                f"{expected_dependencies}"
            )
        object.__setattr__(
            self,
            "depends_on",
            normalized_dependencies,
        )

        validate_aware_datetime(
            self.completed_at,
            field_name="completed_at",
        )
        if self.started_at is not None:
            validate_aware_datetime(
                self.started_at,
                field_name="started_at",
            )
            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at must not be earlier than started_at"
                )

        if not isinstance(
            self.artifact_identities,
            tuple,
        ):
            raise TypeError(
                "artifact_identities must be a tuple"
            )
        if any(
            not isinstance(
                artifact,
                WorkflowArtifactIdentity,
            )
            for artifact in self.artifact_identities
        ):
            raise TypeError(
                "artifact_identities must contain only "
                "WorkflowArtifactIdentity objects"
            )
        artifact_keys = tuple(
            artifact.identity_key
            for artifact in self.artifact_identities
        )
        if len(artifact_keys) != len(
            set(artifact_keys)
        ):
            raise ValueError(
                "artifact_identities must be unique"
            )

        object.__setattr__(
            self,
            "warnings",
            self._normalize_text_tuple(
                self.warnings,
                field_name="warnings",
            ),
        )
        object.__setattr__(
            self,
            "failure_reason",
            normalize_optional_text(
                self.failure_reason,
                field_name="failure_reason",
            ),
        )
        object.__setattr__(
            self,
            "skip_reason",
            normalize_optional_text(
                self.skip_reason,
                field_name="skip_reason",
            ),
        )

        if normalized_status == "SKIPPED":
            if self.started_at is not None:
                raise ValueError(
                    "SKIPPED requires started_at to be None"
                )
            if self.skip_reason is None:
                raise ValueError(
                    "SKIPPED requires skip_reason"
                )
            if self.artifact_identities:
                raise ValueError(
                    "SKIPPED cannot produce artifact identities"
                )
        elif self.started_at is None:
            raise ValueError(
                f"{normalized_status} requires started_at"
            )

        if normalized_status == "FAILED":
            if self.failure_reason is None:
                raise ValueError(
                    "FAILED requires failure_reason"
                )
        elif self.failure_reason is not None:
            raise ValueError(
                "failure_reason is only valid for FAILED"
            )

        if (
            normalized_status != "SKIPPED"
            and self.skip_reason is not None
        ):
            raise ValueError(
                "skip_reason is only valid for SKIPPED"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "depends_on": list(
                self.depends_on
            ),
            "started_at": (
                None
                if self.started_at is None
                else self.started_at.isoformat()
            ),
            "completed_at": self.completed_at.isoformat(),
            "artifact_identities": [
                artifact.to_dict()
                for artifact in self.artifact_identities
            ],
            "warnings": list(
                self.warnings
            ),
            "failure_reason": self.failure_reason,
            "skip_reason": self.skip_reason,
        }

    @staticmethod
    def _normalize_text_tuple(
        value: object,
        *,
        field_name: str,
        uppercase: bool = False,
    ) -> tuple[str, ...]:
        if not isinstance(
            value,
            tuple,
        ):
            raise TypeError(
                f"{field_name} must be a tuple"
            )

        normalized = tuple(
            normalize_required_text(
                item,
                field_name=field_name,
                uppercase=uppercase,
            )
            for item in value
        )
        if len(normalized) != len(
            set(normalized)
        ):
            raise ValueError(
                f"{field_name} must contain unique values"
            )
        return normalized


@dataclass(frozen=True, slots=True)
class InvestmentReviewWorkflowRun:
    """Versioned, immutable report for one complete workflow attempt."""

    schema_version: str
    run_id: str
    started_at: datetime
    completed_at: datetime
    stages: tuple[InvestmentReviewWorkflowStageResult, ...]
    warnings: tuple[str, ...] = ()

    SCHEMA_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        normalized_version = normalize_required_text(
            self.schema_version,
            field_name="schema_version",
        )
        if normalized_version != self.SCHEMA_VERSION:
            raise ValueError(
                "unsupported workflow schema_version: "
                f"{normalized_version}"
            )
        object.__setattr__(
            self,
            "schema_version",
            normalized_version,
        )
        object.__setattr__(
            self,
            "run_id",
            normalize_required_text(
                self.run_id,
                field_name="run_id",
            ),
        )

        validate_aware_datetime(
            self.started_at,
            field_name="started_at",
        )
        validate_aware_datetime(
            self.completed_at,
            field_name="completed_at",
        )
        if self.completed_at < self.started_at:
            raise ValueError(
                "completed_at must not be earlier than started_at"
            )

        if not isinstance(
            self.stages,
            tuple,
        ):
            raise TypeError(
                "stages must be a tuple"
            )
        if any(
            not isinstance(
                stage,
                InvestmentReviewWorkflowStageResult,
            )
            for stage in self.stages
        ):
            raise TypeError(
                "stages must contain only "
                "InvestmentReviewWorkflowStageResult objects"
            )

        stage_names = tuple(
            stage.stage
            for stage in self.stages
        )
        expected_order = (
            InvestmentReviewWorkflowStageResult.STAGE_ORDER
        )
        if stage_names != expected_order:
            raise ValueError(
                "stages must contain every workflow stage in "
                f"canonical order: {expected_order}"
            )

        results_by_stage = {
            stage.stage: stage
            for stage in self.stages
        }
        for stage in self.stages:
            if not (
                self.started_at
                <= stage.completed_at
                <= self.completed_at
            ):
                raise ValueError(
                    f"{stage.stage} completed_at must be within "
                    "the workflow run interval"
                )
            if (
                stage.started_at is not None
                and stage.started_at < self.started_at
            ):
                raise ValueError(
                    f"{stage.stage} started_at must be within "
                    "the workflow run interval"
                )
            if stage.status in (
                "COMPLETED",
                "FAILED",
            ):
                incomplete_dependencies = tuple(
                    dependency
                    for dependency in stage.depends_on
                    if results_by_stage[
                        dependency
                    ].status
                    != "COMPLETED"
                )
                if incomplete_dependencies:
                    raise ValueError(
                        f"{stage.stage} cannot be {stage.status} "
                        "because dependencies are not completed: "
                        + ", ".join(
                            incomplete_dependencies
                        )
                    )

        object.__setattr__(
            self,
            "warnings",
            InvestmentReviewWorkflowStageResult._normalize_text_tuple(
                self.warnings,
                field_name="warnings",
            ),
        )

    @property
    def status(self) -> str:
        if any(
            stage.status == "FAILED"
            for stage in self.stages
        ):
            return "FAILED"
        if any(
            stage.status == "SKIPPED"
            for stage in self.stages
        ):
            return "COMPLETED_WITH_SKIPS"
        return "COMPLETED"

    def stage(
        self,
        stage: str,
    ) -> InvestmentReviewWorkflowStageResult:
        normalized = normalize_required_text(
            stage,
            field_name="stage",
            uppercase=True,
        )
        for result in self.stages:
            if result.stage == normalized:
                return result
        raise KeyError(
            f"workflow stage is not present: {normalized}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "stages": [
                stage.to_dict()
                for stage in self.stages
            ],
            "warnings": list(
                self.warnings
            ),
        }
