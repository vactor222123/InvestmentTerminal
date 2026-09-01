# Phase 7 Package 76 - Schema-4 Terminal Transition Remediation

## Classification

IMPLEMENTATION.

## Root cause and result

The numeric drain legally used attempt four, then the provider result changed
from `RESPONSE_NUMERIC` to terminal `NO_PRICE_DATA`. Schema-4 writing accepted
that transition, but subsequent checkpoint validation rejected every
non-numeric failure above attempt three. The complete drain therefore failed
before provider work while reading its valid persisted checkpoint.

Validation now allows any recognized terminal failure category at attempt four,
because schema 4 does not persist the preceding category. Non-numeric
`RETRY_PENDING` remains capped below attempt three, and terminal
`RESPONSE_NUMERIC` still requires exactly attempt four. No checkpoint migration
or schema increment is required.

## Verification

- focused scan, drain, CLI, and architecture checks: 46 passed;
- complete suite: 2,891 passed, four skipped, one existing Starlette warning;
- `git diff --check`: clean;
- no live Yahoo request or runtime mutation occurred.

## Next step

Repeat the complete eligibility drain against the unchanged private checkpoint
and return only its redacted aggregate report.
