# P3-WP017 Proposal — Cloud Render Workers Architecture & Evidence Review

> **Status:** PRE1 ARCHITECTURE & EVIDENCE REVIEW / PROPOSED / NOT AUTHORIZED  
> **Reviewed Main HEAD:** `1c07b898c0b6df50649962f73e481808a561a882`  
> **Repository:** `rebootob/Orbis-Video-Studio-AI`  
> **PRE1 Verdict:** `READY_FOR_OWNER_SCOPE_LOCK`

---

## 1. Executive Summary

This architecture review establishes the technical foundation for **P3-WP017 — Cloud Render Workers** without modifying production code or creating database migrations.

By inspecting repository truth, we confirmed that Orbis already possesses:
1. **Strict Production Approval Gates** (`ApprovalRecord`, `QCService.validate_final_approval()`, `ProductionOrchestrator.approve_final_production()`).
2. **Durable Job Claim & Lease Queue Mechanics** (`GenerationJob`, `JobDispatchService` lease/claim pattern).
3. **Provider-Neutral Object Storage Boundaries** (`ObjectStorageProvider`, `S3StorageProvider`, `Asset` lineage).
4. **Granular Usage Ledger & Budget Controls** (`UsageLedger`, `CostLedgerService`, `BudgetService`).

WP017 will introduce a **stateless Cloud Render Worker** executing FFmpeg timeline assembly behind a provider-neutral `RenderExecutor` boundary, strictly gated by prior WP016 timeline approval.

---

## 2. Reusable Architecture & Repository Evidence

### A. Approval → Render Gate
- **Approved Revision Representation:** Represented by `AssemblyTimeline` ([`models/assembly.py:15-49`](../../backend/app/models/assembly.py#L15-L49)) with fields `id`, `version`, `status="APPROVED"`, `is_active=True`.
- **Approval Truth Owner:** `ApprovalRecord` ([`models/qc.py:155-195`](../../backend/app/models/qc.py#L155-L195)) created exclusively by `ProductionOrchestrator.approve_final_production()` ([`services/production_orchestrator.py:1272-1398`](../../backend/app/services/production_orchestrator.py#L1272-L1398)).
- **WP017 Render Pre-condition:** A valid `ApprovalRecord` row matching `(project_id, timeline_id, timeline_version)` with `status="APPROVED"`, plus a `QCRun` with `blocker_count=0` and 0 warnings marked `FIX_REQUIRED`.
- **Stale/Unapproved Revisions:** If `timeline_id != active_timeline.id` or no `ApprovalRecord` exists for `active_timeline.id`, submission fails closed with `400 Bad Request`.

### B. Existing Job & Queue Infrastructure
- **Reusable Patterns:** DB lease/claim semantics from `GenerationJob` ([`models/generation_job.py:18-85`](../../backend/app/models/generation_job.py#L18-L85)) and `JobDispatchService` ([`services/job_dispatch.py:1-120`](../../backend/app/services/job_dispatch.py#L1-L120)). Reusable columns: `claimed_by`, `claim_token`, `claim_expires_at`, `retry_count`, `max_retries`, `idempotency_key`, `next_retry_at`.
- **Key Differences:** `GenerationJob` is for shot-level external AI generation APIs (polling remote provider endpoints). `RenderJob` is for project/timeline-level video rendering executed directly on worker nodes via FFmpeg. `GenerationJob` has a shot-level active index; `RenderJob` requires a timeline-level active index (`uq_render_jobs_active_timeline`).

### C. Storage & Asset Lineage
- **Storage Interface:** Uses `ObjectStorageProvider` ([`services/storage/base.py`](../../backend/app/services/storage/base.py)) and `S3StorageProvider` ([`services/storage/s3.py`](../../backend/app/services/storage/s3.py)).
- **Output Key Format:** `projects/{project_id}/renders/render_{render_job_id}_v{timeline_version}.mp4`.
- **Lineage Retention:** On completion, a new `Asset` row ([`models/asset.py`](../../backend/app/models/asset.py)) is created with `asset_type="VIDEO"`, `is_locked=True`, linked to `project_id`. Prior renders remain untouched (`NO_SILENT_HISTORY_LOSS`).

---

## 3. Architecture Gaps & Missing Contracts

1. **Missing `RenderJob` Model & Migration:** No dedicated model exists for full-timeline render jobs. `GenerationJob` cannot be overloaded because it is scoped per-shot and oriented around external API polling.
2. **Missing `RenderExecutor` Boundary:** No abstract execution interface exists for video timeline rendering (downloading visual/audio placements, building FFmpeg filtergraphs, encoding master MP4).
3. **Missing Stateless Worker Process:** No worker process currently pulls render tasks, updates lease heartbeats, and uploads compiled master video assets.
4. **Missing Render API Endpoints:** `/api/v1/projects/{project_id}/renders` endpoints do not yet exist.

---

## 4. Proposed WP017 Architecture

```text
Orbis Control Plane
 -> ProductionOrchestrator / QC Validation (WP016 Approval Gating)
 -> POST /api/v1/projects/{project_id}/renders/submit
 -> RenderJob (DB state: QUEUED)
 -> Stateless Cloud Render Worker (Claim via DB FOR UPDATE SKIP LOCKED)
 -> RenderJob (DB state: CLAIMED -> RUNNING)
 -> Download Visual & Audio placement assets from Object Storage
 -> FFmpegRenderExecutor (Filtergraph build + render + encode)
 -> Upload final MP4 to S3 Storage
 -> Create Asset row (is_locked=True) & update RenderJob to COMPLETED
 -> UsageLedger (Log compute render cost)
```

---

## 5. RenderJob Contract & State Model

### A. Minimum Field Contract
```python
class RenderJob(Base):
    __tablename__ = "render_jobs"
    id: Mapped[uuid.UUID]                # PG_UUID primary key
    project_id: Mapped[uuid.UUID]        # FK projects.id
    timeline_id: Mapped[uuid.UUID]       # FK assembly_timelines.id
    timeline_version: Mapped[int]        # Exact revision version
    approval_id: Mapped[uuid.UUID]       # FK production_approvals.id
    render_profile: Mapped[str]          # "MASTER_HD" (default)
    status: Mapped[str]                  # QUEUED, CLAIMED, RUNNING, COMPLETED, FAILED, CANCELLED, RECONCILIATION_REQUIRED
    idempotency_key: Mapped[str]         # Indexed string
    output_asset_id: Mapped[uuid.UUID]   # FK assets.id (nullable)
    progress: Mapped[float]              # 0.0 to 100.0
    claimed_by: Mapped[str]              # Worker hostname/pod
    claim_token: Mapped[str]             # Lease token
    claim_expires_at: Mapped[datetime]   # Lease expiration
    retry_count: Mapped[int]             # Default 0
    max_retries: Mapped[int]             # Default 3
    error_message: Mapped[str]           # Failure details
    render_metadata: Mapped[dict]        # Spec metadata (JSON)
    created_at, started_at, completed_at, updated_at
```

### B. Canonical State Vocabulary
- `QUEUED`: Submitted and waiting for worker claim.
- `CLAIMED`: Claimed by worker; assets downloading to worker scratch space.
- `RUNNING`: FFmpeg process executing.
- `COMPLETED`: Render finished, master MP4 uploaded to storage, DB committed.
- `FAILED`: Terminal failure or max retries exceeded.
- `RECONCILIATION_REQUIRED`: Ambiguous failure (e.g. S3 upload succeeded but worker crashed before DB commit).
- `CANCELLED`: Explicitly cancelled before execution.

---

## 6. Idempotency & Concurrency Strategy

- **Request Identity:** `idempotency_key = f"{project_id}:{timeline_id}:{timeline_version}:{render_profile}"`.
- **Repeated Submissions:** If a `RenderJob` for `(project_id, timeline_id)` is currently active (`QUEUED`, `CLAIMED`, `RUNNING`), re-submitting returns the active `RenderJob` (NO_OP replay).
- **Explicit Re-render:** If the active revision is already `COMPLETED` and the user explicitly triggers a new render, a new timestamped `idempotency_key` is assigned, producing a new `RenderJob` and new `Asset` row (`FULL_HISTORY_RETENTION`).
- **Worker Claiming:** Atomic `FOR UPDATE SKIP LOCKED` query guarantees at most 1 worker claims a job.

---

## 7. Storage Lineage & Asset Management

- **Storage Key Pattern:** `projects/{project_id}/renders/render_{render_job_id}_v{timeline_version}.mp4`.
- **Lineage Retention:** On completion, a new `Asset` row ([`models/asset.py`](../../backend/app/models/asset.py)) is created with `asset_type="VIDEO"`, `is_locked=True`, linked to `project_id`. Prior renders remain untouched (`NO_SILENT_HISTORY_LOSS`).

---

## 8. Failure & Reconciliation Matrix

| Failure Case | Canonical Truth | Recovery & Reconciliation Behavior | Automatic Retry? |
| :--- | :--- | :--- | :--- |
| Worker dies before render starts | DB Lease | Lease expires (`claim_expires_at < now`). Recovery resets to `QUEUED`. | Yes (if `retry_count < max_retries`) |
| Worker dies mid-FFmpeg render | DB Lease | Lease expires. Recovery resets to `QUEUED`, cleans scratch dir. | Yes (if `retry_count < max_retries`) |
| Output uploaded to S3, DB update crashes | Object Storage | Recovery finds S3 object matching checksum -> completes DB commit to `COMPLETED` & links `Asset`. | Reconcile to `COMPLETED` |
| DB says `RUNNING`, worker missing | Heartbeat | Lease expires -> check S3 -> re-queue or reconcile. | Yes |
| Duplicate API submit call | `idempotency_key` | Active job check returns existing `RenderJob` (NO_OP). | N/A (Idempotent) |
| FFmpeg exits with non-zero code | FFmpeg Process | Worker captures `stderr` -> updates `error_message` -> re-queues or marks `FAILED`. | Yes (if `retry_count < max_retries`) |
| Timeline modified while render queued | Timeline Version | Worker compares `timeline.version` with `render_job.timeline_version`. If mismatched, cancels job with `REVISION_SUPERSEDED`. | No (Cancelled) |

---

## 9. Proposed API & Frontend UX

### A. API Endpoints (`/api/v1/projects/{project_id}/renders`)
- `POST /projects/{project_id}/renders/submit`: Submit render job for approved timeline.
- `GET /projects/{project_id}/renders/latest`: Fetch status/progress of current render.
- `GET /projects/{project_id}/renders/{render_id}`: Fetch detailed render job state.
- `GET /projects/{project_id}/renders`: List paginated render job history.
- `POST /projects/{project_id}/renders/{render_id}/cancel`: Cancel queued/running render job.
- `POST /projects/{project_id}/renders/{render_id}/retry`: Retry failed render job.

### B. Frontend UX (Simple Mode)
- Default Flow: Approved QC -> `[Render Final Video]` -> `Rendering 42% ...` -> `Completed` -> `[Preview Master Video]`.
- Hiding Technical Noise: Normal users are never exposed to FFmpeg flags, CRF values, codec choices, thread counts, or cloud worker instance types.

---

## 10. Performance, Scalability & Security Controls

- **Streaming Storage:** Source assets are downloaded directly to local scratch disk files; outputs stream to storage (never loaded entirely into RAM).
- **No N+1 Queries:** Placement assets fetched in set-based queries.
- **Paginated History:** Render history endpoints strictly bounded (`offset`, `limit <= 100`).
- **Usage Ledger:** Logs compute render time to `UsageLedger` upon completion.
- **Budget Guard:** `BudgetService.get_budget_status()` prevents render submission if hard limit is breached.
- **Timeouts:** Hard render execution timeout (30 minutes).

---

## 11. Migration & Schema Impact (Evidence Only)

- Single new database table `render_jobs` with foreign keys to `projects`, `assembly_timelines`, `production_approvals`, and `assets`.
- Partial unique index `uq_render_jobs_active_timeline` on `(project_id, timeline_id)` for active statuses.

---

## 12. Acceptance Test Plan

1. **Unapproved Timeline Gate:** Attempting to render an unapproved timeline revision fails closed with `400 Bad Request`.
2. **Exact Revision Binding:** `RenderJob` stores exact `timeline_id` and `timeline_version`.
3. **Idempotency Replay:** Duplicate POST returns existing active job without creating duplicate DB rows or worker jobs.
4. **Single Worker Lease:** Concurrent worker claim queries use `FOR UPDATE SKIP LOCKED` so only 1 worker claims a job.
5. **Stale Lease Recovery:** Simulated worker crash triggers lease expiration and safe re-queue.
6. **Full History Retention:** Re-rendering an approved timeline creates a new `RenderJob` and new `Asset` without deleting old outputs.
7. **Budget Lock:** Submitting a render when hard budget limit is exceeded fails with `400 Bad Request`.
8. **Cross-Project Isolation:** Attempting to query or cancel another project's render job returns `404 Not Found`.

---

## 13. In Scope vs. Out of Scope

### IN SCOPE (WP017)
- `RenderJob` model, migration, DB indices, and idempotency logic.
- `RenderExecutor` boundary & concrete `FFmpegRenderExecutor`.
- `RenderJobService` with lease/claim/heartbeat mechanics.
- Stateless worker execution loop (`render_worker.py`).
- S3 asset download, FFmpeg rendering, output upload, and `Asset` creation.
- Production approval gating (`ApprovalRecord` validation).
- Backend API endpoints (`/api/v1/projects/{project_id}/renders/*`).
- Frontend Simple Mode render workspace UI integration.
- Unit and integration test suite.

### OUT OF SCOPE (Keep for WP018+)
- Multi-output variant rendering (16:9 / 9:16 / 1:1 platform presets) -> **P4-WP018**.
- Platform export presets (YouTube / TikTok / Instagram) -> **P4-WP018**.
- Project export/import package `.orbis` -> **P4-WP019**.
- ComfyUI or local AI model generation.
- Paid AI generation provider integrations.
- Advanced NLE DAW controls.

---

## 14. Implementation Breakdown Recommendation

When WP017 is explicitly authorized by the Owner, implementation should proceed in 4 ordered passes:
1. **Pass 1 — Data Model & Migration:** `RenderJob` entity, Alembic migration, repository schemas.
2. **Pass 2 — Core Render Engine & Worker Service:** `RenderExecutor`, `FFmpegRenderExecutor`, `RenderJobService` claim/lease/reconciliation mechanics.
3. **Pass 3 — API & Production Orchestrator Integration:** `/projects/{project_id}/renders` endpoints, QC/approval pre-condition checks, usage ledger logging.
4. **Pass 4 — Frontend Workspace & Verification Suite:** Simple Mode render UX, full automated backend & frontend test suite.

---

## 15. PRE1 Deliverable Verdict

```text
WP017_PRE1_VERDICT: READY_FOR_OWNER_SCOPE_LOCK
```
