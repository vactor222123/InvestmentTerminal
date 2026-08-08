# Verified Historical Snapshot Reads

Historical review packages must not be consumed directly from archive paths.

The read boundary is:

```text
manifest lookup
    -> snapshot metadata
    -> SHA-256 integrity verification
    -> JSON deserialization
    -> historical consumer
```

Use `HistoricalSnapshotReader` for historical package reads.

Rules:

- snapshot identity is resolved through the append-only manifest;
- archived bytes are verified before deserialization;
- checksum mismatch stops the read;
- missing archive evidence stops the read;
- malformed JSON stops the read explicitly;
- the package root must remain a JSON object;
- the reader never modifies archive evidence or manifest metadata;
- analytics, comparison, reporting, and reconstruction workflows should depend
  on this verified read boundary rather than reading archive files directly.
