# CI Container Smoke Test

Sprint 32 Task 11 closes the container execution gap left intentionally open by
Task 32.9.

The normal Python regression job remains unchanged in purpose. A second CI job
now exercises the real production image on the GitHub Ubuntu runner.

## Smoke Sequence

```text
checkout
→ docker build production Dockerfile
→ create isolated runtime directory
→ provide Knowledge file prerequisite
→ docker run production image
→ wait for /health
→ assert /ready == READY
→ assert container process is non-root
→ assert operational SQLite stores exist on mounted /runtime
→ cleanup
```

## Knowledge Fixture

Readiness currently defines the Knowledge prerequisite as an existing file.

The smoke test therefore creates:

```text
/runtime/knowledge.db
```

before startup.

It does not synthesize application Knowledge content and it does not call a
grounded-generation route. This is intentionally a deployment wiring smoke test,
not a semantic Knowledge or provider integration test.

## Operational SQLite

The fixture does not pre-create:

```text
/runtime/operational/provider_usage_cost.db
/runtime/operational/grounded_generations.db
```

Those files must be initialized by the production ASGI lifespan.

After readiness succeeds, CI asserts that both files exist on the host-mounted
runtime directory.

## Secrets

CI uses literal synthetic values scoped to the ephemeral container:

```text
provider-smoke-secret
server-smoke-secret
```

No repository or environment GitHub secret is required for this smoke test.

The external provider is never called.

## Liveness vs Readiness

The smoke test checks them separately:

```text
GET /health
GET /ready
```

`/health` is used to wait for the process to become live.

`/ready` must then return the complete expected local readiness payload with all
four checks `READY`.

This preserves the Task 32.9/32.10 distinction between process liveness and
dependency readiness.

## Non-root Verification

CI executes:

```text
docker exec investment-terminal-ci id -u
```

and fails if the UID is `0`.

This verifies the Dockerfile's non-root contract against a real running image,
rather than only inspecting Dockerfile text.

## Failure Diagnostics and Cleanup

If any smoke step fails, CI captures:

```text
docker logs investment-terminal-ci
```

Cleanup runs under `if: always()` and force-removes the named container.

The runtime fixture lives under `RUNNER_TEMP` and is discarded with the
ephemeral GitHub runner.

## Non-Goals

Task 32.11 does not:

- call OpenAI or another external AI provider;
- test grounded generation semantics;
- add reverse proxy or TLS;
- publish an image;
- push to a registry;
- test backup/restore activation.

Operational backup/restore resilience remains Task 32.12.
