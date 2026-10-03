# Phase 7 — generic profile-backed research run

Classification: `IMPLEMENTATION`. Fresh clean GitHub `develop` matched
`b647aa773bf2f2850cf4f1b86f4fb1e9ddccfcf4` before changes. No private
runtime file, provider, or operational SQLite database was accessed or changed.

The existing `instrument_research_export` accepts any explicitly selected
manifest symbol, but requires twelve path/binding parameters. The new
`python -m investment_terminal.cli.instrument_research_run` is a thin CLI
composition over that exact export. It uses the existing schema-1 private
`WEEKLY_RUN_PROFILE` to derive manifest, checksum, source directory, SQLite
database, and the weekly checkpoint corresponding to the explicit UTC-midnight
`--end`. The caller still supplies `--projection`, its exact-byte
`--projection-sha256`, `--symbol`, `--history-start`, `--end`, and distinct
`--private-output` and `--report-output` paths. The private output must share
the projection's parent directory; the report must be directly under the
profile's report directory. This prevents accidental private export into the
redacted-report directory.

The command delegates all manifest, checkpoint, projection, selected latest-200
SMA parity, SQLite read-only, row validation, atomic output, and overwrite
checks to the established export boundary. It changes no schema-1 private or
report field. Preflight failures reveal no private path or symbol; a delegated
failure can produce only the existing generic redacted `FAILED` report. A
`SEND` line is printed only when the report file exists; the private profile,
projection, export, checkpoints, and SQLite database remain `DO NOT SEND`.

This is an operator convenience for any selected instrument, not MCD-specific
logic, automatic data acquisition, a ranking engine, ChatGPT interpretation,
or a scheduler. The current raw-close price basis does not establish adjusted
returns or exchange-session completeness. Next qualify one invocation against
the user's private evidence and independently check SQLite integrity before
considering a wider query surface or scheduled refresh.
