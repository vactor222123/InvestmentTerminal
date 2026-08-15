# Investment Terminal — Architecture Context

## Status

**Document type:** Supporting architecture context  
**Document status:** Synchronized supporting document  
**Primary authority:** `Architecture.md` at repository root  
**Current baseline:** Sprint 31 closure

If this file and root `Architecture.md` disagree, the root document is
authoritative.

## Authority Flow

```text
Current analytical domains
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded generation
→ grounding validation
→ ADMISSIBLE generated evidence
→ durable grounded-generation persistence
```

Authority does not flow backwards.

## Major Boundaries

- Review assembles current evidence.
- History owns canonical historical evidence and rebuildable projections.
- Knowledge owns explicit versioned evidence-backed derived knowledge.
- Grounded AI consumes Knowledge and validates provider output.
- Persisted grounded generations are downstream generated evidence.
- Provider usage/cost accounting is parallel operational accounting.
- Application/API/Server layers orchestrate and transport; they do not own
  historical or Knowledge authority.

## Generated-Evidence Integrity

Persisted grounded generations are:

- ADMISSIBLE-only;
- deeply immutable in memory;
- strict-JSON validated;
- detached on external serialization;
- durably stored in a dedicated SQLite boundary.

They are not promoted into History or Knowledge automatically.

## Dependency Direction

Executable architecture tests enforce:

```text
History
  ✗ Knowledge / AI / Application / API / Server

Knowledge
  ✗ AI / Application / API / Server

AI
  ✓ Knowledge
  ✗ History / Review / Application / API / Server / CLI

Application
  ✓ AI / Knowledge
  ✗ Server / CLI / History internals

API
  ✓ Application
  ✗ Server / CLI / History internals

Server
  ✓ Application / API / AI / Knowledge composition
  ✗ History internals
```

## Reproducible Delivery

Sprint 31 adds a repository-owned delivery contract:

```text
Python 3.13.x
→ direct dependency source manifests
→ exact-pinned resolver/compiler
→ hash-locked runtime/dev dependencies
→ clean Linux GitHub Actions
→ focused architecture/dependency checks
→ full pytest
→ git diff --check
```

Tests must not depend on developer-local personal data.

## Current Limitations

Still intentional:

- process-local rate limiting and one-worker production runtime;
- no distributed admission state;
- no container/infrastructure deployment contract;
- no backup/restore operational contract;
- API-key authentication without richer authorization scopes;
- no automatic generated-evidence promotion;
- no broker execution.
