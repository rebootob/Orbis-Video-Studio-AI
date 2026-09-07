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
4. **Granular Usage Ledger & Budget Controls** (`UsageLedger`, `CostLedgerService`, `BudgetService.check_budget_before_dispatch()`).

WP017 will introduce a **stateless Cloud Render Worker** executing FFmpeg timeline assembly behind a provider-neutral `RenderExecutor` boundary, strictly gated by prior WP016 timeline approval and fail-closed pre-execution cost reservations.

---

## 2. Reusable Architecture & Repository Evidence

### A. Approval → Render Gate
- **Approved Revision Representation:** Represented by `AssemblyTimeline` ([`models/assembly.py:15-49`](../../backend/app/models/assembly.py#L15-L49)) with fields `id`, `version`, `status="APPROVED"`, `is_active=True`.
- **Approval Truth Owner:** `ApprovalRecord` ([`models/qc.py:155-195`](../../backend/app/models/qc.py#L155-L195)) created exclusively by `ProductionOrchestrator.approve_final_production()` ([`services/production_orchestrator.py:1272-1398`](../../backend/app/services/production_orchestrator.py#L1272-L1398)).
- **WP017 Render Pre-condition:** A valid existing `ApprovalRecord` row bound to exact `(project_id, timeline_id, timeline_version)` with `status="APPROVED"`.
- **QC Evidence Lineage:** `ApprovalRecord.qc_run_id` serves as the immutable QC evidence that justified approval.
- **Idempotent Approval Truth:** Rendering an already-approved timeline revision DOES NOT require a newer or re-evaluated `QCRun` to pass again. Once `ApprovalRecord` exists for exact `(project_id, timeline_id, timeline_version)`, it is authoritative. Requiring re-evaluation would break WP016 idempotent approval replay.
- **Cross-Project Fail-Closed Security:** Attempting to render or query an `ApprovalRecord` or `AssemblyTimeline` belonging to a different `project_id` fails closed with `404 Not Found` or `400 Bad Request`.

### B. Existing Job & Queue Infrastructure
- **EXISTING REPOSITORY EVIDENCE:** DB lease and claim semantics in `GenerationJob` ([`models/generation_job.py:18-85`](../../backend/app/models/generation_job.py#L18-L85)) and `JobDispatchService` ([`services/job_dispatch.py:100-120`](../../backend/app/services/job_dispatch.py#L100-L120)) use a Compare-And-Set (CAS) atomic update pattern via `change(db, filters, values)` with `claimed_by=None` and `claim_expires_at <= now`. Existing code does NOT use `FOR UPDATE SKIP LOCKED`.
- **PROPOSED NEW DESIGN CHOICE (WP017):** For `RenderJob`, we propose PostgreSQL `FOR UPDATE SKIP LOCKED` explicitly as a NEW WP017 design choice for worker claim loops to eliminate optimistic claim contention under high worker concurrency, while retaining fallback compatibility with the existing CAS lease pattern.
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
4. **Missing `UsageLedger` Linkage to `RenderJob`:** `UsageLedger` currently has `job_id` linked to `generation_jobs`. `UsageLedger` needs a `render_job_id` column (FK `render_jobs.id`) to durably link render cost entries.
5. **Missing Render API Endpoints:** `/api/v1/projects/{project_id}/renders` endpoints do not yet exist.

---

## 4. Proposed WP017 Architecture

```text
Orbis Control Plane
 -> ProductionOrchestrator / Approval Validation (WP016 Approval Gating)
 -> POST /api/v1/projects/{project_id}/renders/submit
 -> BudgetService.check_budget_before_dispatch(lock_row=True)
 -> Pre-compute Cost Reservation (UsageLedger cost_status: ESTIMATED, render_job_id)
 -> RenderJob (DB state: QUEUED)
 -> Stateless Cloud Render Worker (Claim via FOR UPDATE SKIP LOCKED or CAS)
 -> RenderJob (DB state: CLAIMED -> RUNNING)
 -> Download Visual & Audio placement assets from Object Storage
 -> FFmpegRenderExecutor (Filtergraph build + render + encode)
 -> Upload final MP4 to S3 Storage
 -> Create Asset row (is_locked=True) & update RenderJob to COMPLETED
 -> UsageLedger (Reconcile cost_status: CONFIRMED, actual_cost populated)
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
    estimated_cost_usd: Mapped[float]    # Pre-execution reserved compute cost
    actual_cost_usd: Mapped[float]       # Post-execution settled compute cost
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

## 6. Idempotency & Worker Claim Strategy

- **Request Identity:** `idempotency_key = f"{project_id}:{timeline_id}:{timeline_version}:{render_profile}"`.
- **Repeated Submissions:** If a `RenderJob` for `(project_id, timeline_id)` is currently active (`QUEUED`, `CLAIMED`, `RUNNING`), re-submitting returns the active `RenderJob` (NO_OP replay).
- **Explicit Re-render:** If the active revision is already `COMPLETED` and the user explicitly triggers a new render, a new timestamped `idempotency_key` is assigned, producing a new `RenderJob` and new `Asset` row (`FULL_HISTORY_RETENTION`).
- **Worker Claiming:**
  - *Existing Evidence:* CAS compare-and-set update via `change(db, filters, values)` where `claimed_by IS NULL` or `claim_expires_at <= now`.
  - *Proposed New Design Choice:* PostgreSQL `FOR UPDATE SKIP LOCKED` query for high-throughput worker pools.

---

## 7. Storage Lineage & Asset Management

- **Storage Key Pattern:** `projects/{project_id}/renders/render_{render_job_id}_v{timeline_version}.mp4`.
- **Lineage Retention:** On completion, a new `Asset` row ([`models/asset.py`](../../backend/app/models/asset.py)) is created with `asset_type="VIDEO"`, `is_locked=True`, linked to `project_id`. Prior renders remain untouched (`NO_SILENT_HISTORY_LOSS`).

---

## 8. Failure & Reconciliation Matrix

| Failure Case | Canonical Truth | Recovery & Cost Reconciliation Behavior | Automatic Retry? |
| :--- | :--- | :--- | :--- |
| Worker dies before render starts | DB Lease | Lease expires (`claim_expires_at < now`). Recovery resets to `QUEUED`. Reserved `ESTIMATED` cost remains active. | Yes (if `retry_count < max_retries`) |
| Worker dies mid-FFmpeg render | DB Lease | Lease expires. Recovery resets to `QUEUED`, cleans scratch dir. Reserved `ESTIMATED` cost remains active. | Yes (if `retry_count < max_retries`) |
| Output uploaded to S3, DB update crashes | Object Storage | Recovery finds S3 object matching checksum -> completes DB commit to `COMPLETED`, links `Asset`, settles `cost_status="CONFIRMED"`. | Reconcile to `COMPLETED` |
| DB says `RUNNING`, worker missing | Heartbeat | Lease expires -> check S3 -> re-queue or reconcile. | Yes |
| Duplicate API submit call | `idempotency_key` | Active job check returns existing `RenderJob` (NO_OP). | N/A (Idempotent) |
| Safe pre-execution cancellation / failure | DB Status | Safe pre-execution failure releases reserved cost (`cost_status="ADJUSTED"`, `actual_cost=0.0`). | No |
| Ambiguous execution failure | DB Status | `RECONCILIATION_REQUIRED`: `ESTIMATED` cost entry MUST NOT be silently released. Remains committed until manual/auto reconciliation. | No (Manual / Automated Recon) |
| Timeline modified while render queued | Timeline Version | Worker compares `timeline.version` with `render_job.timeline_version`. If mismatched, cancels job with `REVISION_SUPERSEDED`. | No (Cancelled) |

---

## 9. Pre-Compute Cost Reservation & Concurrency-Safe Budget Check

- **Option A Minimal Cost Lifecycle Alignment:**
  - `UsageLedger` ([`models/usage_ledger.py`](../../backend/app/models/usage_ledger.py)) uses `CostStatus` enum values (`ESTIMATED`, `CONFIRMED`, `ADJUSTED`, `UNKNOWN`).
  - Pre-render reservation: Insert `UsageLedger` entry with `cost_status = "ESTIMATED"`, `estimated_cost = estimated_usd`, `actual_cost = None`, `operation = "RENDER_VIDEO"`, linking `render_job_id` (FK `render_jobs.id`).
  - Budget inclusion: `BudgetService.get_project_committed_cost()` ([`services/budget.py:21-30`](../../backend/app/services/budget.py#L21-L30)) sums `CONFIRMED`, `ADJUSTED`, and `ESTIMATED` costs, ensuring active render reservations immediately count toward committed project spend.
  - Completion settlement: Reconcile `UsageLedger` entry to `cost_status = "CONFIRMED"`, setting `actual_cost = actual_usd`.
  - Pre-execution cancellation/failure: Adjust entry to `cost_status = "ADJUSTED"`, setting `actual_cost = 0.0`.
  - Ambiguous failure: `RECONCILIATION_REQUIRED` keeps `cost_status = "ESTIMATED"` committed until reconciliation.
- **Concurrency-Safe Atomic Transaction:**
  - Pre-render submission MUST NOT rely on `get_budget_status()` alone.
  - Submit endpoint executes `BudgetService.check_budget_before_dispatch(db=db, project_id=project_id, estimated_cost=estimated_usd, lock_row=True)` ([`services/budget.py:99-138`](../../backend/app/services/budget.py#L99-L138)).
  - Executed atomically in ONE DB transaction:
    1. Acquire row lock on `Project` via `SELECT FOR UPDATE` (`lock_row=True`).
    2. Compute committed spend (`CONFIRMED` + `ADJUSTED` + active `ESTIMATED`) and verify `committed + estimated_usd <= project.budget_limit`.
    3. Insert `UsageLedger` pre-render reservation entry (`cost_status = "ESTIMATED"`).
    4. Insert `RenderJob` entity (`status = "QUEUED"`).
  - Two concurrent submit calls against the same project budget execute sequentially against the row-locked `Project` row; the second request sees the first request's `ESTIMATED` entry in committed cost and fails closed with `400 Bad Request` if remaining budget is exceeded.

---

## 10. Proposed API & Frontend UX

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

## 11. Performance, Scalability & Security Controls

- **Streaming Storage:** Source assets stream to worker local scratch disk; output streams to S3 (never loaded into RAM).
- **Zero N+1 Queries:** Placement assets fetched in set-based queries.
- **Paginated History:** Render history strictly bounded (`offset`, `limit <= 100`).
- **Usage Ledger:** Pre-execution cost reservation (`ESTIMATED`) and post-execution settlement (`CONFIRMED`).
- **Budget Guard:** `BudgetService.check_budget_before_dispatch(lock_row=True)` blocks render submission if hard limit is breached.
- **Timeouts:** Hard execution timeout (30 minutes).

---

## 12. Migration & Schema Impact (Evidence Only)

The exact database migration scope for WP017 comprises:
1. **NEW table `render_jobs`**:
   - Columns: `id`, `project_id`, `timeline_id`, `timeline_version`, `approval_id`, `render_profile`, `status`, `idempotency_key`, `output_asset_id`, `progress`, `claimed_by`, `claim_token`, `claim_expires_at`, `retry_count`, `max_retries`, `estimated_cost_usd`, `actual_cost_usd`, `error_message`, `render_metadata`, `created_at`, `started_at`, `completed_at`, `updated_at`.
   - Foreign Keys: `projects.id` (CASCADE), `assembly_timelines.id` (CASCADE), `production_approvals.id` (CASCADE), `assets.id` (SET NULL).
   - Indexes: `ix_render_jobs_project_id`, `ix_render_jobs_timeline_id`, `ix_render_jobs_status`, `ix_render_jobs_idempotency_key`.
   - Partial Unique Index: `uq_render_jobs_active_timeline` on `(project_id, timeline_id)` WHERE `status IN ('QUEUED', 'CLAIMED', 'RUNNING')`.
2. **MODIFIED table `usage_ledger`**:
   - Column Addition: `render_job_id` (`PG_UUID`, nullable, Foreign Key `render_jobs.id` `ondelete="SET NULL"`, index `ix_usage_ledger_render_job_id`).

---

## 13. Acceptance Test Plan

1. **Unapproved Timeline Gate:** Attempting to render an unapproved timeline revision fails closed with `400 Bad Request`.
2. **Exact Revision Binding:** `RenderJob` stores exact `timeline_id` and `timeline_version`.
3. **Existing Approval Verification:** Render authorization verifies existing `ApprovalRecord` for exact `(project_id, timeline_id, timeline_version)`. Does NOT require a new QC run to re-pass.
4. **Idempotency Replay:** Duplicate POST returns existing active job without creating duplicate DB rows or worker jobs.
5. **Worker Lease Claim:** Propose `FOR UPDATE SKIP LOCKED` or CAS claim query guarantees at most 1 worker claims a job.
6. **Pre-Compute Cost Reservation:** Submitting a render job creates an `ESTIMATED` `UsageLedger` entry counting toward budget limit before worker execution.
7. **Cost Reconciliation:** Settles `ESTIMATED` reservation to `CONFIRMED` actual cost on completion; pre-execution failures adjust entry to `ADJUSTED` (0.0 cost).
8. **Ambiguous Failure Cost Guard:** `RECONCILIATION_REQUIRED` status preserves `ESTIMATED` cost reservation without silent release.
9. **Concurrent Budget Reservation Test:** Two concurrent render submit calls against the same project budget evaluate against the row-locked project row (`BudgetService.check_budget_before_dispatch(lock_row=True)`); atomic reservation applies so only the allowed submission succeeds, and total committed estimated render cost cannot exceed hard budget limit.
10. **Full History Retention:** Re-rendering creates new `Asset` without overwriting prior outputs.
11. **Budget Lock:** Submitting a render when hard budget limit is exceeded fails with `400 Bad Request`.
12. **Cross-Project Isolation:** Attempting to query or cancel another project's render job returns `404 Not Found`.

---

## 14. In Scope vs. Out of Scope

### IN SCOPE (WP017)
- `RenderJob` model, migration, DB indices, and idempotency logic.
- `RenderExecutor` boundary & concrete `FFmpegRenderExecutor`.
- `RenderJobService` with lease/claim/heartbeat mechanics.
- Stateless worker execution loop (`render_worker.py`).
- S3 asset download, FFmpeg rendering, output upload, and `Asset` creation.
- Production approval gating (`ApprovalRecord` validation).
- Pre-execution cost reservation (`ESTIMATED`) and settlement (`CONFIRMED`) lifecycle in `UsageLedger`.
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

## 15. Implementation Breakdown Recommendation

When WP017 is explicitly authorized by the Owner, implementation should proceed in 4 ordered passes:
1. **Pass 1 — Data Model & Migration:** `RenderJob` entity, `usage_ledger.render_job_id` column addition, Alembic migration, repository schemas.
2. **Pass 2 — Core Render Engine & Worker Service:** `RenderExecutor`, `FFmpegRenderExecutor`, `RenderJobService` claim/lease/reconciliation mechanics.
3. **Pass 3 — API & Pre-Compute Cost Reservation:** `/projects/{project_id}/renders` endpoints, approval pre-condition checks, `BudgetService.check_budget_before_dispatch(lock_row=True)` & `UsageLedger` `ESTIMATED`/`CONFIRMED` lifecycle.
4. **Pass 4 — Frontend Workspace & Verification Suite:** Simple Mode render UX, full automated backend & frontend test suite.

---

## 16. PRE1 Deliverable Verdict

```text
WP017_PRE1_VERDICT: READY_FOR_OWNER_SCOPE_LOCK
```
