# P4-WP020-LIVE-R5-VIDU2-REC1-PREP — Recovery Tooling & Contract Review

## Status

```text
PROJECT: Orbis Video Studio AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-PREP
TYPE: NO-PAID / NO-PROVIDER Recovery Tooling & Contract Review
OWNER_AUTHORIZED: YES (Issue #63 comment 5646093066)
AUTHORIZED_BASE_MAIN_SHA: 8cae4bd72bd447470f214cf852b516b856638b7f
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-prep

HISTORICAL_VIDU2_EXECUTION:
  EXECUTION_ID: LIVE-20260910-VIDU2-R5
  WORKFLOW_RUN_ID: 34569728383
  PROVIDER_JOB_ID: 995880130565918720
  PROVIDER_STATUS: success
  VIDEO_URL_PRESENT: true
  RETAINED_RECOVERABLE_URL: NOT PROVEN
  DURABLE_VIDEO_ASSET: NOT PROVEN
  VIDU2_PROVIDER_CREDITS_REPORTED: 30.0
  VIDU2_ACTUAL_CREDITS_CONSUMED: UNKNOWN / NOT CONFIRMED
  VIDU2_USD_EQUIVALENT: UNKNOWN / NOT CONVERTED

PREP_EXECUTION_INVARIANTS:
  VIDU_GET_CALLS: 0 (Mocks only; zero real calls executed)
  VIDU_POST_CALLS: 0 (Strictly disallowed)
  PROVIDER_CALLS: 0
  WORKFLOW_DISPATCHES: 0
  PAID_CALLS: 0

P4-WP020: ACTIVE / NOT CLOSED
CORE_V1_PROGRESS: 19 / 20 (95%)
CORE_V1_RELEASE: NOT DECLARED
NEXT_PAID_LIVE_EXECUTION: NONE / NOT AUTHORIZED
PROPOSED_FUTURE_GATE: P4-WP020-LIVE-R5-VIDU2-REC1-RUN1 (Requires separate Owner authorization)
```

---

## 1. Background & Purpose

Under Owner authorization in Issue #63 comment `5646093066`, this gate `P4-WP020-LIVE-R5-VIDU2-REC1-PREP` designs and validates the bounded, GET-only recovery tooling for historical Vidu Provider Job ID `995880130565918720` (Run `34569728383`).

The historical run demonstrated successful provider-side generation (`state: success`, `video_url_present: true`), but ephemeral runner DB/MinIO termination and telemetry URL masking prevented the media from being durably persisted into an Orbis `Asset`.

This gate defines and implements the exact code and test harness for GET-only retrieval without triggering any provider POST, regeneration, or credit consumption.

---

## 2. Technical Review & Verification Findings

### A. Existing Provider Adapter Behavior
- Inspected `backend/app/providers/vidu.py`:
  - `check_job_status(provider_job_id)` calls `_request("GET", f"/tasks/{quote(provider_job_id, safe='')}/creations", job_id=provider_job_id)`.
  - There is **ZERO** code path in `check_job_status()` that invokes POST, triggers `/text2video` or `/reference2video`, or calls `submit_generation_job()`.
  - Input validation sanitizes `provider_job_id` via regex `[A-Za-z0-9_-]{1,255}`.

### B. Video Materialization Capability
- Inspected `backend/app/services/video_materialization.py`:
  - `materialize_completed_result()` safely validates public HTTPS URLs, blocks private/local IP ranges (SSRF protection), enforces a 1 GiB size boundary, streams media to temporary disk, uploads to Orbis object storage (`projects/{project_id}/generated-video/{job_id}/{checksum[:16]}.{ext}`), and registers a deterministic `Asset` (ID: `uuid5(NAMESPACE_URL, "orbis://video-generation/{job.id}")`).
  - Idempotency is enforced: if the deterministic `Asset` exists and is already linked to the `GenerationJob` and `Shot`, it returns immediately without re-downloading.

### C. Ephemeral DB Reconstruction Strategy
- Because PostgreSQL in Run `34569728383` was ephemeral, the original DB rows were destroyed.
- Attempting recovery in a fresh session requires reconstructing the parent `Project`, `Scene`, `Shot`, and `GenerationJob` hierarchy:
  - Reconstruction uses deterministic UUIDs derived via `uuid5` from `provider_job_id`:
    - `project_id = uuid5(NAMESPACE_URL, "orbis://vidu-recovery/project/{provider_job_id}")`
    - `scene_id = uuid5(NAMESPACE_URL, "orbis://vidu-recovery/scene/{provider_job_id}/{scene_number}")`
    - `shot_id = uuid5(NAMESPACE_URL, "orbis://vidu-recovery/shot/{provider_job_id}/{shot_number}")`
    - `job_id = uuid5(NAMESPACE_URL, "orbis://vidu-recovery/job/{provider_job_id}")`
  - This guarantees that repeated recovery execution against the same database is strictly idempotent and cannot produce duplicate entities or conflicting bindings.
  - Reconstruction explicitly tracks that the DB record is a reconstructed harness for historical Job ID `995880130565918720`, preserving audit honesty.

### D. Billing Semantics & Credit Interpretation
- If the provider GET response reports `credits: 30.0`:
  - It reflects historical provider-side telemetry from the original task creation.
  - A GET query does NOT consume new credits.
  - Under conservative billing rules, the recovery service preserves:
    - `VIDU2_PROVIDER_CREDITS_REPORTED = 30.0`
    - `VIDU2_ACTUAL_CREDITS_CONSUMED = UNKNOWN / NOT CONFIRMED`
    - `VIDU2_USD_EQUIVALENT = UNKNOWN / NOT CONVERTED`
  - Contract Criterion #2 remains `PARTIAL`. No claim is made that exactly 30 credits were deducted from prepaid balance or that USD cost is 0.

### E. Error & STOP Conditions
Recovery will stop safely with zero side effects under any of the following:
1. Provider reports `TASK_NOT_FOUND` / HTTP 404 -> STOP with `ViduJobNotFoundError`.
2. Provider reports status other than `COMPLETED` -> STOP with `ViduJobNotCompletedError`.
3. Provider returns no creation URL or URL expired -> STOP with `ViduMissingOutputUrlError`.
4. URL resolves to private/loopback IP -> STOP with SSRF validation error.
5. Download failure or checksum mismatch -> Rollback DB transaction; STOP safely.
6. **NO FALLBACK GENERATION** is permitted.

---

## 3. Implementation Details

1. **Recovery Service Module**: `backend/app/services/vidu_recovery.py`
   - Class `ViduExistingJobRecoveryService`:
     - Method `ensure_or_reconstruct_lineage(db, provider_job_id)`
     - Method `recover_existing_job(db, provider_job_id, adapter, storage_provider, downloader)`
   - Invariant: Zero POST calls (`posts_attempted = 0`), strictly invokes `check_job_status` (GET).

2. **Test Suite**: `backend/tests/test_vidu_recovery.py`
   - Tests mock all provider interactions. Zero network calls to Vidu API.
   - Proves:
     - GET-only request path in `check_job_status`.
     - Creation of deterministic lineage (`Project` -> `Scene` -> `Shot` -> `GenerationJob` -> `VIDEO Asset`).
     - Idempotency across multiple recovery invocations (no duplicate assets or jobs).
     - Safe error handling for job not found, missing URL, incomplete state, and private/unsafe URLs.
     - Conservative credit reporting.

---

## 4. Test Evidence

Executed targeted test suites:
- `backend/tests/test_vidu_recovery.py`: 7 passed
- `backend/tests/test_video_materialization.py`: 3 passed
- `backend/tests/test_wp020_live_r5_vidu2_contract.py`: 22 passed
- `backend/tests/test_production_orchestrator.py`: 22 passed
- `backend/tests/test_wp020a_zero_billing_e2e.py`: 6 passed

**Total Targeted Backend Tests Passing: 60 passed (100%)**

Zero real provider calls were made.

---

## 5. Proposed Future Gate: `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`

*(Proposed only; execution requires explicit Owner authorization)*

### Bounded Scope:
1. **Target**: Existing Provider Job ID `995880130565918720`.
2. **Method**: Single GET query via `ViduExistingJobRecoveryService.recover_existing_job`.
3. **Hard Bounds**:
   - `VIDU_GENERATION_POSTS = 0`
   - `VIDU_GET_CALLS <= 1`
   - `NEW_PROVIDER_JOBS = 0`
   - `FALLBACK_GENERATIONS = 0`
4. **Outcome Assessment**:
   - If URL is still active and media downloads: persists to Orbis object storage, creates durable `Asset`, binds to `Shot`, achieving `PROVEN` video retention.
   - If URL expired (e.g. Vidu retention window exceeded) or task not found: stops safely with documented proof, confirming that provider ephemeral retention has lapsed without spending credits or retrying.
5. **STOP Condition**: Collect evidence, record output in control docs, and stop for ChatGPT review.
