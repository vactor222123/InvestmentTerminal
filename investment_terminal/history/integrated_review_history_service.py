"""Preserve an integrated Review Package and build its History projection."""

from dataclasses import dataclass
from pathlib import Path

from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
    HistoricalImportResult,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
    ManifestImportResult,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_service import (
    HistoricalSnapshotService,
)


@dataclass(frozen=True, slots=True)
class IntegratedReviewHistoryResult:
    """Separate canonical-archive and rebuildable-projection outcomes."""

    snapshot: HistoricalSnapshot
    manifest_import: ManifestImportResult
    detail_import: HistoricalImportResult

    def __post_init__(self) -> None:
        if not isinstance(
            self.snapshot,
            HistoricalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a HistoricalSnapshot"
            )
        if not isinstance(
            self.manifest_import,
            ManifestImportResult,
        ):
            raise TypeError(
                "manifest_import must be a ManifestImportResult"
            )
        if not isinstance(
            self.detail_import,
            HistoricalImportResult,
        ):
            raise TypeError(
                "detail_import must be a HistoricalImportResult"
            )
        if self.detail_import.snapshot_id != self.snapshot.snapshot_id:
            raise ValueError(
                "detail_import must describe the preserved snapshot"
            )

    def to_dict(self) -> dict:
        return {
            "archive": {
                "status": "COMPLETED",
                "snapshot": self.snapshot.to_dict(),
            },
            "projection": {
                "status": "COMPLETED",
                "manifest_import": self.manifest_import.to_dict(),
                "detail_import": self.detail_import.to_dict(),
            },
        }


class HistoricalProjectionAfterArchiveError(RuntimeError):
    """Report projection failure without obscuring the registered archive."""

    def __init__(
        self,
        *,
        snapshot: HistoricalSnapshot,
        cause: Exception,
    ) -> None:
        self.snapshot = snapshot
        self.cause = cause
        super().__init__(
            "Review Package archive registration completed for snapshot "
            f"{snapshot.snapshot_id}, but History projection failed: "
            f"{str(cause).strip() or cause.__class__.__name__}"
        )

    def to_dict(self) -> dict:
        return {
            "archive": {
                "status": "COMPLETED",
                "snapshot": self.snapshot.to_dict(),
            },
            "projection": {
                "status": "FAILED",
                "reason": str(self.cause).strip()
                or self.cause.__class__.__name__,
            },
        }


class IntegratedReviewHistoryService:
    """Coordinate canonical preservation before rebuildable projection."""

    def __init__(
        self,
        *,
        snapshot_service: HistoricalSnapshotService,
        manifest_import_service: HistoricalManifestImportService,
        import_pipeline: HistoricalImportPipeline,
    ) -> None:
        if not isinstance(
            snapshot_service,
            HistoricalSnapshotService,
        ):
            raise TypeError(
                "snapshot_service must be a HistoricalSnapshotService"
            )
        if not isinstance(
            manifest_import_service,
            HistoricalManifestImportService,
        ):
            raise TypeError(
                "manifest_import_service must be a "
                "HistoricalManifestImportService"
            )
        if not isinstance(
            import_pipeline,
            HistoricalImportPipeline,
        ):
            raise TypeError(
                "import_pipeline must be a HistoricalImportPipeline"
            )

        self.snapshot_service = snapshot_service
        self.manifest_import_service = manifest_import_service
        self.import_pipeline = import_pipeline

    def preserve_and_project(
        self,
        source_path: str | Path,
        *,
        product_version: str | None = None,
        package_id: str | None = None,
        supersedes: str | None = None,
    ) -> IntegratedReviewHistoryResult:
        snapshot = self.snapshot_service.preserve(
            source_path,
            product_version=product_version,
            package_id=package_id,
            supersedes=supersedes,
        )

        try:
            manifest_result = (
                self.manifest_import_service.synchronize()
            )
            import_result = self.import_pipeline.import_snapshot(
                snapshot
            )
        except Exception as exc:
            raise HistoricalProjectionAfterArchiveError(
                snapshot=snapshot,
                cause=exc,
            ) from exc

        return IntegratedReviewHistoryResult(
            snapshot=snapshot,
            manifest_import=manifest_result,
            detail_import=import_result,
        )
