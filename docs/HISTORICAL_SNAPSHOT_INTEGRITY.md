# Historical Snapshot Integrity

Archived review packages are immutable historical evidence.

Before a historical package is consumed by analytics, comparison, reporting,
or reconstruction workflows, its SHA-256 checksum must be verified against
the checksum stored in `HistoricalSnapshot`.

Use:

```python
from investment_terminal.history.historical_snapshot_integrity import (
    HistoricalSnapshotIntegrityVerifier,
)

archive_path = HistoricalSnapshotIntegrityVerifier(
    archive_root
).require_valid(
    snapshot
)
```

Rules:

- archive bytes remain canonical evidence;
- manifest metadata identifies the expected checksum;
- missing archive files fail explicitly;
- checksum mismatches fail before historical data is consumed;
- resolved archive paths must remain inside `archive_root`;
- symlink/path redirection outside the archive root is rejected before reads;
- verification never modifies the archive or manifest;
- integrity verification belongs to the History Domain, not CLI or review code.
