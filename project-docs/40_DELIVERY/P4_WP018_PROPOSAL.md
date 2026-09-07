# P4-WP018 Proposal — Multi-Output & Platform Export Presets Architecture & Evidence Review

> **Status:** PRE1 ARCHITECTURE & EVIDENCE REVIEW (CORRECTED) / PROPOSED / NOT AUTHORIZED
> **Reviewed Main HEAD:** `07ba0fdaf1719a7d6ed882155dfb113a4729d55a`  
> **Repository:** `rebootob/Orbis-Video-Studio-AI`  
> **PRE1 Verdict:** `READY_FOR_OWNER_SCOPE_LOCK`

---

## 1. Executive Summary

This updated proposal establishes the technical architecture, data contracts, reuse opportunities, and acceptance criteria for **P4-WP018 — Multi-Output & Platform Export Presets** without modifying production source code or executing database migrations.

By inspecting live repository truth (including WP015 timeline assembly, WP016 QC/approval, and WP017 cloud render workers), we confirmed that Orbis possesses:
1. **Master Production Approval Gates:** Gated timeline revision approval truth in `ApprovalRecord` ([`models/qc.py`](../../backend/app/models/qc.py)).
2. **Durable Cloud Render Infrastructure:** `RenderJob` entity, stateless `CloudRenderWorker`, worker lease/claim fencing, attempt-specific `UsageLedger` accounting, and `FFmpegRenderExecutor` process execution ([`models/render_job.py`](../../backend/app/models/render_job.py), [`services/render_job.py`](../../backend/app/services/render_job.py), [`services/render_worker.py`](../../backend/app/services/render_worker.py)).
3. **Provider-Neutral Storage & Immutable Asset Registration:** `ObjectStorageProvider` and immutable `Asset` records ([`models/asset.py`](../../backend/app/models/asset.py), [`services/storage/`](../../backend/app/services/storage/)).
4. **Concurrency-Safe Cost Ledger & Budget Service:** Pre-execution budget validation and attempt cost reservation ([`services/budget.py`](../../backend/app/services/budget.py)).

WP018 extends this foundation to support **multi-output aspect ratio, resolution, and platform export presets** (such as 16:9 YouTube Master 4K/1080p, 9:16 TikTok/Reels/Shorts, 1:1 Instagram Square, and 720p LMS/Web variants) from ONE approved master project timeline.

---

## 2. Scope Alignment & Evidence Review

### A. Strictly Bounded WP018 Scope (REQUIRED)
To prevent unproven scope expansion, WP018 is strictly bounded to features supported by current repository evidence:
- **Aspect Ratio Variants:** `16:9` (Widescreen), `9:16` (Vertical), `1:1` (Square).
- **Resolution Presets:** 4K (`3840x2160`), Full HD (`1920x1080`), Vertical HD (`1080x1920`), Square HD (`1080x1080`), Web SD (`1280x720`).
- **Bitrate & Quality Profiles:** High (25 Mbps), Standard (10 Mbps), Mobile (8 Mbps), Web (3 Mbps).
- **Platform-Oriented Export Presets:** `YT_MASTER_4K`, `YT_STANDARD_1080P`, `TIKTOK_REELS_9X16`, `INSTAGRAM_SQUARE`, `LMS_WEB_720P`.
- **Multi-Variant Batch Submission:** Atomic submission and progress tracking for N requested variants from one approved timeline.
- **Immutable Output & History:** Each export creates a distinct `RenderJob` and `Asset` record (`FULL_HISTORY_RETENTION`).
- **Budget & Cost Truth:** Pre-execution batch cost validation and attempt-specific `UsageLedger` reservations.

### B. Features Classified as FUTURE / OPTIONAL / OUT OF SCOPE
The following capabilities require metadata models or pipeline features that do not exist in current canonical repository truth and are explicitly demoted to **FUTURE / OPTIONAL / OUT OF SCOPE**:
- Multi-language audio stem selection & dynamic dub swapping (`-> FUTURE / OUT OF SCOPE`).
- Subtitle generation, SRT/VTT sidecars, or burned-in subtitles (`-> FUTURE / OUT OF SCOPE`).
- Dual-language subtitle / audio export (`-> FUTURE / OUT OF SCOPE`).
- Image/logo watermarking pipeline (`-> FUTURE / OUT OF SCOPE`).

---

## 3. Reusable WP017 Infrastructure & Architecture

WP018 reuses 100% of WP017 cloud render worker machinery rather than creating duplicate worker queues or re-implementing job fencing.

```mermaid
graph TD
    Project[Approved Project & Timeline vN] --> ExportUI[Frontend Export Preset Workspace]
    ExportUI --> BatchSubmit["POST /api/v1/projects/{id}/renders/export-batch"]
    
    subgraph Atomic DB Transaction
        BatchSubmit --> ProjectLock["DB Row Lock: Project (with_for_update)"]
        ProjectLock --> BudgetCheck["BudgetService: Validate Combined Batch Estimated Cost"]
        BudgetCheck --> CreateBatch["Create RenderBatch Record"]
        CreateBatch --> LoopJobs["For Each Preset: Create RenderJob (render_variant_key) + UsageLedger Reservation"]
        LoopJobs --> AtomicCommit["Commit Transaction ONCE (Rollback All on Any Error)"]
    end
    
    AtomicCommit --> Job1["RenderJob 1: render_variant_key = YT_STANDARD_1080P:hash1"]
    AtomicCommit --> Job2["RenderJob 2: render_variant_key = TIKTOK_REELS_9X16:hash2"]
    AtomicCommit --> Job3["RenderJob 3: render_variant_key = INSTAGRAM_SQUARE:hash3"]
    
    Job1 --> WorkerQueue[Stateless CloudRenderWorker Pool]
    Job2 --> WorkerQueue
    Job3 --> WorkerQueue
    
    WorkerQueue --> FFmpegEngine[FFmpegRenderExecutor: Aspect Scaling & Padding Filtergraph]
    FFmpegEngine --> S3Storage[Object Storage: projects/{id}/exports/vN/{preset}_{job_id}.mp4]
    S3Storage --> AssetEntry[Immutable Asset Creation: asset_type=EXPORT_VIDEO]
    AssetEntry --> SettledLedger[UsageLedger Cost Reconciliation: CONFIRMED]
```

### Infrastructure Reused from WP017:
- **`RenderJob` Table & State Machine:** States (`QUEUED`, `CLAIMED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `RECONCILIATION_REQUIRED`) remain identical.
- **Worker Claim & Lease Fencing:** `claim_next_render_job()`, worker heartbeat, lease expiration reclaims, and `max_retries = 3` policy are 100% reused.
- **`CloudRenderWorker` Lifecycle:** Scratch disk creation, S3 asset downloads, streaming uploads, error handling, and cleanup logic are 100% reused.
- **`FFmpegRenderExecutor` Process Execution:** Core process execution is reused; filtergraph generation is extended to support aspect scaling, pillarboxing, letterboxing, and cropping.
- **Budget & Usage Ledger:** `BudgetService` pre-execution check and attempt-specific `UsageLedger` reservations (`cost_status="ESTIMATED"` -> `cost_status="CONFIRMED"`) are 100% reused.

---

## 4. Key Architectural Decisions (A through I)

### Question A: Render Source — Timeline vs Master Asset
- **Decision:** Render directly from **Approved Assembly Timeline & raw shot assets** via single-pass FFmpeg filtergraphs (with optional master asset fallback if raw assets are purged).
- **Rationale:** 
  1. **Visual Quality:** Re-encoding an already H.264 compressed master MP4 file introduces macroblocking, color space degradation, and generation loss. Single-pass encoding directly from raw shot assets yields pristine 4K/1080p outputs.
  2. **Framing Flexibility:** Pan-and-scan, pillarboxing, and center-cropping operate cleanly when scaling raw clip streams directly in FFmpeg.

### Question B: Preset Identity & Snapshot Model
- **Decision:** Dual-level preset identity with **immutable submission snapshots**.
  1. **System Presets:** Built-in standard profiles (`YT_MASTER_4K`, `YT_STANDARD_1080P`, `TIKTOK_REELS_9X16`, `INSTAGRAM_SQUARE`, `LMS_WEB_720P`).
  2. **Custom Overrides:** User-specified parameters (resolution, target bitrate, custom dimensions).
  3. **Immutable Snapshot on Submission:** When a job is submitted, the full resolved preset specification is serialized into `RenderJob.render_metadata["preset_snapshot"]`. Future updates to system preset definitions will never alter historical render execution behavior.

### Question C: Idempotency Identity & DB Uniqueness Model
- **Decision:** Durable `render_variant_key` column on `RenderJob` + replacement of partial unique index.
  - Column addition: `render_variant_key: Mapped[str] = mapped_column(String(100), default="MASTER", nullable=False)`
  - Value for WP017 Master render: `"MASTER"`
  - Value for WP018 Export variants: `f"{preset_id}:{preset_snapshot_hash}"`
- **DB Unique Index Replacement:**
  Replace `uq_render_jobs_active_timeline` (`project_id`, `timeline_id`) with `uq_render_jobs_active_variant` over:
  `("project_id", "timeline_id", "render_variant_key")`
  Partial WHERE clause: `status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')`
- **Safety Semantics:**
  - **A. SAME timeline + DIFFERENT preset variants (`render_variant_key`):** May coexist concurrently in `QUEUED`/`RUNNING` without index conflict.
  - **B. SAME timeline + SAME preset snapshot (`render_variant_key`):** Submitting identical preset variant returns active job idempotently (NO_OP replay). DB index prevents duplicate inserts.
  - **C. RECONCILIATION_REQUIRED isolation:** `RECONCILIATION_REQUIRED` status blocks submission of THAT SAME variant key only, leaving unrelated sibling variants unblocked.
  - **D. WP017 MASTER Protection:** Master renders use `render_variant_key = "MASTER"`, preserving at most ONE active MASTER render per timeline.
  - **E. Concurrency Safety:** Uniqueness is enforced at the DB level, preventing race-based duplicate variant job creation.

### Question D: History & Re-render Semantics
- **Decision:** Strict adherence to `FULL_HISTORY_RETENTION` and `NO_SILENT_HISTORY_LOSS`.
- **Behavior:** Prior export files, failed attempts, and historical `RenderJob` records are NEVER overwritten or deleted. Every export run generates a distinct `RenderJob` record, distinct `UsageLedger` entry, and distinct `Asset` row.

### Question E: Multiple Variants Submission Model & Atomic Authorization
- **Decision:** Parent **`RenderBatch`** grouping with independent **`RenderJob`** worker execution, created under a single atomic DB transaction.
- **API Endpoint:** `POST /api/v1/projects/{project_id}/renders/export-batch`
- **Atomic Transaction Sequence:**
  1. Acquire project DB lock (`Project` row `with_for_update()`).
  2. Validate combined estimated cost of ALL requested variants against remaining project budget via `BudgetService.check_budget_before_dispatch()`.
  3. Create `RenderBatch` row in `PROCESSING` status.
  4. For each requested preset variant:
     - Compute variant key: `render_variant_key = f"{preset_id}:{preset_snapshot_hash}"`.
     - Create child `RenderJob` in `QUEUED` status with `render_variant_key`.
     - Create `UsageLedger` pre-execution cost reservation entry (`cost_status="ESTIMATED"`).
     - Bind `RenderJob.current_usage_ledger_id = ledger_entry.id`.
  5. **COMMIT ONCE** at the end of the transaction.
- **Rollback Guarantee:** If ANY child creation or ledger reservation fails during authorization, `db.rollback()` executes, reverting all changes in the transaction. Zero partial batches, zero orphan jobs, and zero budget oversubscription under concurrency.

### Question F: Partial Failure Isolation
- **Decision:** 100% isolation between child variant jobs after batch authorization completes.
- **Behavior:** Each variant `RenderJob` executes independently on worker nodes. If `TIKTOK_REELS_9X16` fails during rendering (e.g. FFmpeg error), `YT_STANDARD_1080P` and `INSTAGRAM_SQUARE` continue executing and completing normally. The parent batch reflects a partial success state (`COMPLETED_WITH_ERRORS`).

### Question G: Cost Accounting & Budget Safety
- **Decision:** Pre-execution batch validation + attempt-specific reservations per variant.
- **Behavior:**
  1. `BudgetService` verifies project remaining budget covers the sum of estimated costs for ALL requested variants in the batch before any job is created.
  2. Each variant `RenderJob` creates its own `UsageLedger` reservation entry (`idempotency_key="export_reserve_{job_id}_attempt_{attempt_num}"`).
  3. Final actual compute cost is reconciled upon job completion.

### Question H: Storage Key Naming & Asset Lineage Contract
- **Decision:** Use **Design B (Lineage in `RenderJob.render_metadata` + Immutable `Asset` Relation)**.
- **Evidence Review:** The canonical `Asset` model ([`models/asset.py`](../../backend/app/models/asset.py)) contains NO `metadata` column. To avoid inventing unproven schema changes, preset/output lineage is stored in existing `RenderJob.render_metadata` (JSON column on `RenderJob`), while the output file is registered as an immutable `Asset` row linked via `RenderJob.output_asset_id`.
- **Storage Key Pattern:** `projects/{project_id}/exports/v{timeline_version}/{preset_id}_{job_id}.mp4`
- **Asset Registration:** Completed exports create an `Asset` row with:
  - `asset_type = "EXPORT_VIDEO"`
  - `is_locked = True`
  - `name = f"export_{preset_id}_v{timeline_version}.mp4"`
  - `original_filename = f"{preset_id}.mp4"`
- **`RenderJob.render_metadata` Lineage Content:**
  ```json
  {
    "preset_id": "TIKTOK_REELS_9X16",
    "render_variant_key": "TIKTOK_REELS_9X16:a1b2c3d4",
    "aspect_ratio": "9:16",
    "resolution": "1080x1920",
    "bitrate_kbps": 8000,
    "timeline_version": 2,
    "preset_snapshot": {
      "preset_id": "TIKTOK_REELS_9X16",
      "target_platform": "TikTok / Shorts / Reels",
      "width": 1080,
      "height": 1920,
      "video_codec": "h264",
      "audio_codec": "aac"
    }
  }
  ```

### Question I: User Experience (UX) Flow
- **Decision:** Integrated **Export Workspace Modal** on top of Simple and Advanced Timeline views.
  1. User clicks **"Export & Platform Presets"** on an approved timeline.
  2. Modal presents preset options:
     - [x] YouTube Standard 1080p (16:9) — Est. $0.50
     - [x] TikTok / Reels (9:16) — Est. $0.50
     - [ ] Instagram Square (1:1) — Est. $0.50
  3. Displays Total Estimated Cost ($1.00) and Project Remaining Budget.
  4. Single click on **"Confirm & Export (2 Variants)"** triggers atomic batch submission.
  5. Modal switches to real-time progress view displaying progress bars and download buttons for completed variants.

---

## 5. Platform Presets & Parameter Specifications

| Preset ID | Target Platform | Aspect Ratio | Dimensions | Video Codec | Audio Codec | Bitrate Profile | Framing Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `YT_MASTER_4K` | YouTube Master | `16:9` | 3840x2160 | H.264 (High) | AAC 320k | 25 Mbps | Native 16:9 |
| `YT_STANDARD_1080P`| YouTube Standard | `16:9` | 1920x1080 | H.264 (Main) | AAC 192k | 10 Mbps | Native 16:9 |
| `TIKTOK_REELS_9X16`| TikTok / Shorts / Reels | `9:16` | 1080x1920 | H.264 (Main) | AAC 192k | 8 Mbps | Center-Crop / Padding |
| `INSTAGRAM_SQUARE` | Instagram Feed | `1:1` | 1080x1080 | H.264 (Main) | AAC 160k | 6 Mbps | Pillarbox / Center-Crop |
| `LMS_WEB_720P` | Corporate LMS / Web | `16:9` | 1280x720 | H.264 (Baseline)| AAC 128k | 3 Mbps | Native 16:9 |

---

## 6. Data Model & Migration Contract

### A. Proposed Database Additions (WP018 Migration):
```python
# app/models/render_batch.py
class RenderBatch(Base):
    __tablename__ = "render_batches"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    timeline_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assembly_timelines.id", ondelete="CASCADE"), nullable=False)
    timeline_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PROCESSING", nullable=False)  # PROCESSING, COMPLETED, COMPLETED_WITH_ERRORS, FAILED
    total_variants: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_variants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_variants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
```

`RenderJob` table additions:
```python
# Column addition on RenderJob model
render_variant_key: Mapped[str] = mapped_column(
    String(100), default="MASTER", nullable=False
)
batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    PG_UUID(as_uuid=True), ForeignKey("render_batches.id", ondelete="SET NULL"), nullable=True
)
```

### B. Alembic Migration Execution Plan (`018_export_presets_and_variant_key.py`):

#### 1. Upgrade Sequence:
1. `op.create_table("render_batches", ...)`
2. `op.add_column("render_jobs", sa.Column("render_variant_key", sa.String(100), nullable=False, server_default="MASTER"))`
3. `op.add_column("render_jobs", sa.Column("batch_id", sa.UUID(), sa.ForeignKey("render_batches.id", ondelete="SET NULL"), nullable=True))`
4. `op.drop_index("uq_render_jobs_active_timeline", table_name="render_jobs")`
5. `op.create_index("uq_render_jobs_active_variant", "render_jobs", ["project_id", "timeline_id", "render_variant_key"], unique=True, postgresql_where=text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"), sqlite_where=text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"))`

#### 2. Legacy Row Migration Truth:
- All existing WP017 `render_jobs` rows receive `render_variant_key = "MASTER"` via `server_default="MASTER"`.
- Legacy WP017 master render jobs map 1:1 to `render_variant_key = "MASTER"`, preserving 100% of WP017 duplicate master render protection.

#### 3. Downgrade / Reversibility Plan:
1. `op.drop_index("uq_render_jobs_active_variant", table_name="render_jobs")`
2. `op.create_index("uq_render_jobs_active_timeline", "render_jobs", ["project_id", "timeline_id"], unique=True, postgresql_where=text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"), sqlite_where=text("status IN ('QUEUED', 'CLAIMED', 'RUNNING', 'RECONCILIATION_REQUIRED')"))`
3. `op.drop_column("render_jobs", "batch_id")`
4. `op.drop_column("render_jobs", "render_variant_key")`
5. `op.drop_table("render_batches")`

### C. Proposed API Endpoints:
- `POST /api/v1/projects/{project_id}/renders/export-batch` — Submit multi-variant export batch under single atomic DB transaction.
- `GET /api/v1/projects/{project_id}/renders/batches/{batch_id}` — Get batch status summary and variant job list.
- `GET /api/v1/renders/presets` — List available system export presets and target specifications.

---

## 7. Explicit Acceptance Criteria & Required Tests for WP018

### A. Acceptance Criteria:
1. **Preset Aspect & Resolution Accuracy:** Generating outputs for `YT_STANDARD_1080P`, `TIKTOK_REELS_9X16`, and `INSTAGRAM_SQUARE` produces valid MP4 video files matching exact target dimensions (`1920x1080`, `1080x1920`, `1080x1080`).
2. **Approval Gate Enforcement:** Attempting to submit an export batch for an unapproved timeline revision fails closed with `400 Bad Request`.
3. **Atomic Batch Authorization:** Submitting a batch request executes under a single DB transaction. If total estimated batch cost exceeds project remaining budget, submission fails closed with `400 Bad Request` before creating any `RenderJob` rows or `UsageLedger` entries.
4. **Zero Partial State on Authorization Failure:** If an authorization error occurs during batch creation, `db.rollback()` executes; zero child jobs, zero `RenderBatch` rows, and zero `UsageLedger` reservations are created.
5. **Successful Batch Integrity:** A successful batch submission of N variants creates exactly 1 `RenderBatch`, exactly N child `RenderJob` rows, and exactly N initial `UsageLedger` reservations bound atomically.
6. **Concurrency Safety:** Concurrent batch submission requests against the same project cannot oversubscribe project budget due to DB row locking on `Project`.
7. **Partial Worker Failure Resilience:** If one variant fails during worker rendering, remaining sibling variants in the batch complete successfully and enter `COMPLETED` status.
8. **Full History Retention & Design B Lineage:** Multiple exports of the same timeline revision create distinct `RenderJob` and `Asset` rows without overwriting prior outputs. Asset lineage is truthfully preserved via `RenderJob.render_metadata` and `output_asset_id`.
9. **Worker Fencing & Lease Recovery:** Stale export worker claims expire safely and are reclaimed by available workers without losing attempt ledger tracking.
10. **Frontend Usability:** The Export & Platform Presets UI modal displays accurate cost estimates, allows selecting target presets, and updates variant progress live.

### B. Required Automated Test Suite (WP018 Implementation Contract):
1. **Concurrent Variant Submissions Test:** 3 different presets (`YT_STANDARD_1080P`, `TIKTOK_REELS_9X16`, `INSTAGRAM_SQUARE`) for the same timeline revision can be `QUEUED` concurrently without violating DB uniqueness constraints.
2. **Idempotent Variant Replay Test:** Submitting the exact same preset snapshot twice for the same timeline revision returns the same active `RenderJob`.
3. **Concurrent Same-Preset Submit Test:** Submitting the exact same preset variant concurrently from two independent DB sessions creates exactly 1 `RenderJob` due to DB unique index authority.
4. **Variant Independence Test:** Different preset variants do not block each other's submission, worker claim, execution, or completion.
5. **Reconciliation Variant Isolation Test:** A `RECONCILIATION_REQUIRED` state on one variant blocks only new attempts of that SAME variant key, leaving sibling variants unblocked.
6. **MASTER Protection Regression Test:** WP017 MASTER duplicate render protection remains 100% intact (`render_variant_key="MASTER"`).
7. **Migration Upgrade Test:** Alembic migration upgrade preserves all existing WP017 `RenderJob` rows with `render_variant_key="MASTER"`.
8. **Migration Downgrade Test:** Alembic migration downgrade restores `uq_render_jobs_active_timeline` safely and reversibly.

---

## 8. Recommended WP018 Implementation Contract

```text
WP018 CONTRACT VERDICT: READY FOR OWNER AUTHORIZATION

Target Work Package: P4-WP018 — Multi-Output & Platform Export Presets
Dependencies: P3-WP017 (Cloud Render Workers) MERGED in main at 07ba0fdaf1719a7d6ed882155dfb113a4729d55a
Scope: Multi-variant aspect/resolution export presets (16:9, 9:16, 1:1), FFmpeg scaling/cropping, render_variant_key DB uniqueness index, atomic batch export submission, Design B Asset lineage in RenderJob.render_metadata, frontend export modal.
Out of Scope: Subtitles/audio stems/watermarking (FUTURE), .orbis archive (WP019), release closure (WP020), raw AI video generation, ComfyUI, social auto-posting.
Execution Plane: Antigravity (when explicitly authorized by Owner).
```
