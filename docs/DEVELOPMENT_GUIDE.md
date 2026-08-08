# Development Guide

## Working branch

Use the `develop` branch for normal development.

```powershell
git checkout develop
git pull origin develop
```

## Virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Standard implementation cycle

```text
audit
  ↓
design
  ↓
implementation
  ↓
focused tests
  ↓
full regression suite
  ↓
documentation
  ↓
one logical commit
```

## Code structure

### Models

Models should:

- represent explicit domain concepts;
- validate invariants at construction boundaries;
- avoid filesystem, CLI, or network ownership;
- use frozen/slotted dataclasses when immutability is appropriate;
- expose stable serialization contracts explicitly.

### Services

Services should:

- orchestrate domain behavior;
- depend on narrow interfaces;
- avoid user-facing printing;
- make failure behavior explicit;
- avoid reading global settings when resolved configuration can be injected.

### Repositories

Repositories should:

- own persistence mapping and parameterized queries;
- preserve deterministic result ordering;
- validate repository boundary inputs;
- document whether they own transactions;
- avoid importing CLI or presentation code.

### CLI

CLI modules should:

- parse arguments;
- resolve paths and configuration;
- compose services;
- translate failures into useful user-facing output;
- avoid containing domain business rules.

## Validation

Use:

```python
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
    validate_score_0_100,
)
```

Use shared helpers only for stable cross-domain primitives.

Do not move business-specific validation into shared utilities.

## Datetimes

Rules:

- persisted and exported timestamps must be timezone-aware;
- use UTC for canonical persistence;
- parsing may accept valid offsets;
- serialization uses ISO-8601;
- naive datetimes must fail explicitly.

## JSON persistence

Mutable JSON documents must use:

```python
from investment_terminal.utils.atomic_write import (
    write_json_atomic,
)
```

Expected behavior:

- create parent directories;
- serialize before replacing the destination;
- reject non-finite JSON numbers;
- write UTF-8;
- finish with a newline unless a contract says otherwise;
- flush and synchronize temporary file contents before replacement;
- preserve existing destination permissions when replacing a file;
- replace atomically;
- synchronize the parent directory after replacement when the platform and filesystem support it;
- tolerate only explicit unsupported-directory-sync errors;
- propagate real directory I/O failures;
- remove temporary files after pre-replacement failures.

Use `sync_directory()` from the same module when another persistence strategy
needs an explicit directory-entry durability boundary.

A failure reported after `os.replace` may mean the new destination contents are already
visible but the final durability synchronization failed. Callers must not assume that
an exception from the post-replacement directory sync implies that the previous file
contents were restored.

Do not use atomic replacement for immutable exclusive archives or append-only manifests without a specific design decision.

## Historical persistence

### Archive

- preserve exact package bytes;
- validate the complete snapshot metadata contract before creating archive evidence;
- use exclusive creation;
- flush and synchronize archive bytes before reporting success;
- remove a newly-created archive file if the exclusive write fails before completion;
- never overwrite completed evidence;
- verify checksum before historical use.

### Manifest

- append one compact JSON object per line;
- reject duplicate snapshot IDs and archive paths;
- preserve append order;
- flush and synchronize each appended record;
- synchronize the manifest directory when the manifest file is first created;
- roll back and remove a first-created manifest if its durability boundary fails;
- do not silently rewrite history.

### SQLite

- treat it as a rebuildable analytical representation;
- keep schema ownership in the History Domain;
- use explicit transaction boundaries for multi-table imports;
- cover rollback behavior with tests.

## Serialization

- preserve public field names and structures;
- do not alter JSON shape during internal refactoring;
- use independent schema versions for independent serialized contracts;
- avoid one global product schema version.

## Testing

Each change needs focused tests.

Always run:

```powershell
python -m pytest tests\<focused-test-file>.py -q
python -m pytest -q
```

Persistence changes should cover:

- successful create;
- successful replace or append;
- invalid input;
- malformed data;
- interrupted/failing write;
- duplicate handling;
- cleanup;
- rollback or recovery.

## Commit style

Use conventional messages:

```text
feat(scope): description
fix(scope): description
refactor(scope): description
test(scope): description
docs(scope): description
```

Examples:

```text
refactor(io): use atomic JSON writes
test(history): cover import rollback
docs(architecture): record sprint 13 principles
```

## Refactoring policy

Refactor when the change:

- removes demonstrated duplication;
- closes a reliability gap;
- clarifies ownership;
- improves testability;
- reduces future maintenance cost.

Do not refactor solely for aesthetic preference.

## Documentation policy

Update documentation when changing:

- architecture;
- public contracts;
- persistence behavior;
- workflows;
