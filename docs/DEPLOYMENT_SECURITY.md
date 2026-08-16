# Deployment Security Contract

Sprint 32 Task 10 defines security ownership for the production deployment
boundary.

The contract deliberately separates application security from deployment
infrastructure security.

## Canonical Topology

```text
public client
    ↓ HTTPS
reverse proxy / platform ingress
    ↓ private HTTP
Investment Terminal container
```

The canonical production deployment does **not** expose the application
container directly to the public Internet.

## TLS Ownership

TLS terminates at:

```text
reverse proxy
or
platform-managed ingress/load balancer
```

The application server does not implement its own TLS listener merely to
duplicate infrastructure responsibility.

This is consistent with the existing security-header middleware: HSTS is not
emitted by the application because it cannot safely assume that the request
arrived over end-to-end TLS.

The TLS-owning proxy/platform is responsible for HTTPS policy, certificate
management, protocol/cipher policy, and HSTS when appropriate.

## Internal Transport

Canonical transport from the TLS termination boundary to the application is:

```text
private/internal HTTP
```

That connection must be restricted by deployment networking so arbitrary public
clients cannot bypass the TLS/authentication ingress and connect directly to the
container port.

A platform that requires encrypted east-west traffic may use infrastructure
mTLS/TLS, but that remains a deployment responsibility rather than an
application TLS implementation.

## Forwarded Headers

The application does not currently use proxy-derived client identity.

The server CLI explicitly starts Uvicorn with:

```text
proxy_headers=False
```

Therefore arbitrary:

```text
X-Forwarded-For
X-Forwarded-Proto
X-Forwarded-Host
Forwarded
```

headers are not implicitly trusted by the ASGI server.

If a future feature requires trusted proxy-derived client IP/scheme/host, that
must be introduced with an explicit trusted-proxy configuration and tests. Do
not simply enable broad forwarded-header trust.

## Application Authentication

Application API-key authentication remains mandatory defense in depth even
behind the private proxy boundary.

Authenticated application routes include:

```text
POST /v1/grounded-ai
GET  /v1/grounded-generations
GET  /v1/grounded-generations/{request_id}
```

The deployment proxy must not be treated as a replacement for application
authentication.

## Endpoint Exposure

Application route behavior and deployment exposure are separate concerns.

### `/health`

Purpose:

```text
liveness
```

Application authentication is not required.

It may be consumed by the local container runtime, node agent, or restricted
platform health checker. Public Internet exposure is unnecessary.

### `/ready`

Purpose:

```text
dependency/readiness assessment
```

Application authentication is currently not required, but deployment policy
must keep this endpoint private to the orchestrator/operator network.

Readiness may reveal which prerequisite category is unavailable, so it is not a
public diagnostic endpoint.

### `/openapi.json`

The application exposes the schema without application authentication and
disables interactive `/docs` and `/redoc`.

Canonical production deployment policy keeps `/openapi.json` private to
operator/developer access unless a deliberate public API documentation decision
is made later.

### `/v1/*`

Publicly reachable API traffic may be forwarded through the TLS ingress, but
application API-key authentication remains required.

## Secrets

The current secret authority remains:

```text
deployment secret manager / environment injection
→ process environment
→ existing runtime config selects the environment variable name
```

Task 32.10 does not add automatic `/secrets/...` file reads.

This avoids creating two competing secret authorities.

Production requirements:

```text
do not bake API keys into the image
do not commit real secret values
do not persist API keys under /runtime
do not place real secrets in backup sets
inject secret values only at runtime
```

`/secrets` remains a deployment-owned mount boundary for platforms that use
secret files internally, but a deployment adapter must explicitly translate
those values into the established process-environment contract if needed.

## Security Headers

The application continues to emit:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Cache-Control: no-store
Pragma: no-cache
```

HSTS belongs to the TLS termination boundary.

## Trusted Network Assumptions

The production contract assumes:

```text
container port is not directly public
only trusted ingress/platform components can reach application transport
/runtime and /backups are not network-shared with untrusted workloads
/config and /secrets are deployment-controlled
operator backup/restore commands run in an administrative context
```

These are deployment requirements, not facts the Python process can infer.

## Failure Model

If the reverse proxy/TLS layer is absent, misconfigured, or bypassable, the
deployment is **not compliant** with the canonical security contract even though
application API-key authentication still provides defense in depth.

If the application API key is missing, production `create_app()` fails before
serving authenticated API traffic.

## Non-Goals

Task 32.10 does not add:

- nginx/Traefik/Caddy configuration;
- Kubernetes Ingress manifests;
- certificate automation;
- application-level TLS;
- trusted forwarded-header parsing;
- OAuth/OIDC;
- secret-file loading;
- IP allowlists;
- WAF rules.

Those may be introduced later if a concrete deployment target requires them.

Task 32.11 owns image build/start smoke verification.
Task 32.12 owns operational backup/restore resilience E2E.
