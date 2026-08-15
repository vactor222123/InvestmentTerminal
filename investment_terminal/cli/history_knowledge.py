"""
CLI composition-boundary adapter from verified History metadata to Knowledge input.

History and Knowledge remain independent domains. This module is allowed to
depend on both and translates only the evidence fields required by the existing
Knowledge projection contract.
"""

from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
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
