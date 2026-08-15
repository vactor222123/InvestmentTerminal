"""
CLI composition-boundary History → Knowledge helpers.

History and Knowledge remain independent domains. This module is allowed to
depend on both and owns only cross-domain translation/orchestration semantics.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.knowledge.ingestion import (
    HistoricalSnapshotKnowledgeIngestionService,
)
from investment_terminal.knowledge.models import (
    KnowledgeRecord,
)
from investment_terminal.knowledge.projection import (
    HistoricalSnapshotKnowledgeSource,
)


class HistoricalSnapshotKnowledgeSourceAdapter:
    """Translate proven verified History metadata into neutral Knowledge input."""

    VERIFIED_IMPORT_STATUSES = (
        "VERIFIED",
        "IMPORTING",
        "IMPORTED",
    )

    def adapt(
        self,
        snapshot: HistoricalSnapshot,
        import_state: HistoricalImportState,
    ) -> HistoricalSnapshotKnowledgeSource:
        if not isinstance(snapshot, HistoricalSnapshot):
            raise TypeError("snapshot must be a HistoricalSnapshot")
        if not isinstance(import_state, HistoricalImportState):
            raise TypeError("import_state must be a HistoricalImportState")

        if import_state.snapshot_id != snapshot.snapshot_id:
            raise ValueError(
                "import_state.snapshot_id must match snapshot.snapshot_id"
            )

        if import_state.status not in self.VERIFIED_IMPORT_STATUSES:
            raise ValueError(
                "Historical snapshot must have verified package evidence "
                "before Knowledge adaptation"
            )

        if import_state.package_verified_at is None:
            raise ValueError(
                "Verified historical import state must include "
                "package_verified_at"
            )

        return HistoricalSnapshotKnowledgeSource(
            snapshot_id=snapshot.snapshot_id,
            package_id=snapshot.package_id,
            generated_at=snapshot.generated_at,
            archived_at=snapshot.archived_at,
            checksum_sha256=snapshot.checksum_sha256,
        )


@dataclass(frozen=True, slots=True)
class HistoricalSnapshotKnowledgeBatchItem:
    """One explicit History snapshot/import-state pair for batch ingestion."""

    snapshot: HistoricalSnapshot
    import_state: HistoricalImportState

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, HistoricalSnapshot):
            raise TypeError("snapshot must be a HistoricalSnapshot")
        if not isinstance(self.import_state, HistoricalImportState):
            raise TypeError(
                "import_state must be a HistoricalImportState"
            )
        if self.snapshot.snapshot_id != self.import_state.snapshot_id:
            raise ValueError(
                "import_state.snapshot_id must match snapshot.snapshot_id"
            )


class HistoricalSnapshotKnowledgeBatchIngestionService:
    """
    Deterministically ingest eligible verified History snapshots.

    Input order is never trusted. Eligible items are sorted using the same
    canonical snapshot chronology as HistoricalSnapshotRepository.list_all().
    Non-verified lifecycle states are skipped explicitly.
    """

    def __init__(
        self,
        *,
        ingestion_service: HistoricalSnapshotKnowledgeIngestionService,
        source_adapter: HistoricalSnapshotKnowledgeSourceAdapter | None = None,
    ) -> None:
        if not isinstance(
            ingestion_service,
            HistoricalSnapshotKnowledgeIngestionService,
        ):
            raise TypeError(
                "ingestion_service must be a "
                "HistoricalSnapshotKnowledgeIngestionService"
            )

        self._ingestion_service = ingestion_service
        self._source_adapter = (
            source_adapter
            if source_adapter is not None
            else HistoricalSnapshotKnowledgeSourceAdapter()
        )

    def ingest(
        self,
        items: Iterable[HistoricalSnapshotKnowledgeBatchItem],
        *,
        subject_key: str,
        generated_at: datetime,
        version: int = 1,
    ) -> tuple[KnowledgeRecord, ...]:
        batch = tuple(items)

        if any(
            not isinstance(
                item,
                HistoricalSnapshotKnowledgeBatchItem,
            )
            for item in batch
        ):
            raise TypeError(
                "items must contain only "
                "HistoricalSnapshotKnowledgeBatchItem values"
            )

        eligible = tuple(
            item
            for item in batch
            if item.import_state.status
            in HistoricalSnapshotKnowledgeSourceAdapter.VERIFIED_IMPORT_STATUSES
        )

        ordered = tuple(
            sorted(
                eligible,
                key=lambda item: (
                    item.snapshot.generated_at,
                    item.snapshot.archived_at,
                    item.snapshot.snapshot_id,
                ),
            )
        )

        return tuple(
            self._ingestion_service.ingest(
                self._source_adapter.adapt(
                    item.snapshot,
                    item.import_state,
                ),
                subject_key=subject_key,
                generated_at=generated_at,
                version=version,
            )
            for item in ordered
        )
