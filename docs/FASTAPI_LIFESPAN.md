# FastAPI Lifespan Contract

Sprint 32 Task 7 moves production runtime side effects out of application
construction and into explicit ASGI lifespan startup ownership.

## Construction Boundary

`production.create_app()` now performs configuration and object composition only.

It does not:

```text
prepare runtime filesystem directories
initialize provider usage/cost SQLite
initialize grounded-generation SQLite
```

This keeps repeated app construction deterministic and side-effect free with
respect to operational persistence.

Knowledge remains an external prerequisite; Task 32.7 does not create or migrate
the Knowledge database.

## Startup Ordering

Production lifespan owns:

```text
runtime filesystem prepare
→ provider usage/cost store initialize
→ grounded-generation store initialize
→ accept requests
```

A startup exception escapes the lifespan and prevents the application from
starting successfully.

## Readiness

Readiness remains a local runtime assessment.

Before startup, operational databases may be absent. After successful lifespan
startup, their schema checks are expected to report READY.

Knowledge and provider credential readiness remain independent prerequisites.

## Shutdown

The current production graph owns no long-lived SQLite connections and the
provider path uses the stateless urllib transport.

Therefore Task 32.7 does not invent a fake close operation.

The explicit lifespan shutdown boundary is retained so any future long-lived
resource introduced into production composition must be deterministically closed
there.

## TestClient Contract

Production tests that rely on startup state must use:

```python
with TestClient(app) as client:
    ...
```

The context manager enters and exits the ASGI lifespan.

Constructing `TestClient(app)` without entering it is not a valid way to assert
production startup behavior.

## Non-Goals

Task 32.7 does not add:

- backup scheduling;
- runtime deployment layout;
- Docker/container configuration;
- reverse proxy or TLS configuration;
- long-lived provider clients that do not otherwise exist.
