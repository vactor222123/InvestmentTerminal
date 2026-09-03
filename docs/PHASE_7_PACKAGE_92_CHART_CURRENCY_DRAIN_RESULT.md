# Phase 7 Package 92 — Complete Chart-Currency Drain Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`df9d42129549089e550c05c3bf8fcd10d5185353`.

Only the explicitly returned redacted aggregate report was reviewed. The
eligibility-success projection and mutable currency checkpoint remained private.

The bounded schema-version-1 drain report returned `COMPLETE` after 120 slices
and 2,550.785615 seconds. Starting coverage was 101 successes and 11,919
never-attempted members. The run made 11,921 provider requests: one request for
each previously unattempted member plus two additional capped attempts for the
single final failure.

Ending coverage accounts for all 12,020 members: 12,019 `SUCCESS`, one isolated
`FINAL_FAILED/INVALID_RESPONSE`, zero retry-pending, and zero never-attempted.
No rate-limit halt occurred. The request checksum is
`48afacd783db4a639080a3a75a12315cff0d1e2d5bf31be9401251b90a757a66`;
the projection checksum is
`d0709f8e83a9f0820327001162fe371129c9c01203112f28e11da0c9ce1f28ea`.
The reviewed report SHA-256 is
`171ab5c3d5ce64c3cb3369fb59847e74f4fcffcbea7377ee19b8d2b4c644b664`.

This establishes complete terminal currency qualification, not universal
success. The one failure remains explicit and excluded from downstream success
projection. Next, run the same coordinator with a one-item budget and require
`COMPLETE`, zero attempted items, and zero provider requests. Batch generation,
candle retrieval, and ingestion remain blocked until that exact-resume evidence
is reviewed.
