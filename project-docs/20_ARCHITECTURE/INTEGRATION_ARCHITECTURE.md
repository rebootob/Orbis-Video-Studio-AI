# External Integration Architecture

> **Canonical Document Location:** [`project-docs/20_ARCHITECTURE/INTEGRATION_ARCHITECTURE.md`](project-docs/20_ARCHITECTURE/INTEGRATION_ARCHITECTURE.md)

---

## 1. Integration Boundary Principles

External systems (such as **Hermes**, **n8n**, external AI agents, and internal client applications) interact with Orbis Video Studio AI strictly through controlled API boundaries.

```mermaid
graph LR
    ExtSystem["External System (Hermes / n8n / Agent)"] -->|HTTPS + Auth Header + Idempotency Key| APIGateway["Integration API Gateway"]
    APIGateway --> SecurityCheck{Auth & Permission Guard}
    SecurityCheck -- Pass --> IdempotencyCheck{Idempotency Key Evaluated?}
    IdempotencyCheck -- New Request --> CoreOrchestrator[Core Engine Execution]
    IdempotencyCheck -- Cached Request --> ReturnCached[Return Prior Result (No Re-run)]
    
    SecurityCheck -- Fail --> Deny[401/403 Forbidden]
    
    subgraph Forbidden Zone
        DB[(Database)]
        Creds[(Secrets Store)]
        Vidu[Vidu Direct API]
    end

    ExtSystem -. Direct Access FORBIDDEN .- DB
    ExtSystem -. Direct Access FORBIDDEN .- Creds
    ExtSystem -. Direct Access FORBIDDEN .- Vidu
```

> [!IMPORTANT]
> External systems MUST NEVER be granted direct read/write access to internal PostgreSQL databases, provider credentials, object storage buckets, or video generation provider endpoints.

---

## 2. Integration Readiness vs V1 Production Scope

- **Integration-Ready Architecture (LOCKED REQUIREMENT):** The system design preserves API schemas, authentication hooks, rate limiters, and idempotency key handling so external agents (Hermes) and automation platforms (n8n) can integrate securely.
- **V1 Production Priority:** Full end-to-end V1 execution focuses on user browser workflow success. External integration connectors remain architecturally enabled without delaying core V1 release gates.

---

## 3. Supported External Operations

The API Gateway supports the following controlled actions:
1. `POST /api/v1/projects` — Create new production project.
2. `POST /api/v1/projects/{id}/documents` — Upload brief, script, or reference assets.
3. `POST /api/v1/projects/{id}/generate-story` — Request AI story generation from uploaded documents.
4. `PATCH /api/v1/projects/{id}/scenes/{scene_id}` — Modify scene structure or shot parameters.
5. `POST /api/v1/projects/{id}/shots/{shot_id}/generate` — Request single or batch shot video generation.
6. `GET /api/v1/jobs/{job_id}` — Query async generation job status and progress.
7. `POST /api/v1/projects/{id}/render` — Request final cloud MP4 video render.
8. `GET /api/v1/projects/{id}/outputs` — Retrieve rendered MP4 download links and metadata.

---

## 4. Idempotency Safeguard Policy

To prevent network retries or duplicate automation loops from triggering expensive, duplicate chargeable video generations:
- All mutation endpoints (`POST /generate`, `POST /render`) REQUIRE an `X-Idempotency-Key` HTTP header.
- The Integration Gateway logs idempotency keys in cache/storage alongside the corresponding `job_id` and response payload for 72 hours.
- Duplicate requests presenting an identical key return the existing job status without initiating new provider calls or incurring charges.
