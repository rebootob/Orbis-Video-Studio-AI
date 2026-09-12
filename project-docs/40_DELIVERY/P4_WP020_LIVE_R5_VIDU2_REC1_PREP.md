# P4-WP020-LIVE-R5-VIDU2-REC1-PREP — Recovery Tooling & Contract Review

## Status

```text
PROJECT: Orbis Video Studio AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-PREP
TYPE: NO-PAID / NO-PROVIDER Recovery Tooling & Contract Review (Corrective Updated)
OWNER_AUTHORIZED: YES (Issue #63 comment 5646093066)
AUTHORIZED_BASE_MAIN_SHA: 8cae4bd72bd447470f214cf852b516b856638b7f
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-prep
CHATGPT_REVIEW_CORRECTED: Review ID 5186528822 (CHANGES REQUIRED addressed)

HISTORICAL_VIDU2_EXECUTION:
  EXECUTION_ID: LIVE-20260910-VIDU2-R5
  WORKFLOW_RUN_ID: 34569728383
  TARGET_HISTORICAL_PROVIDER_JOB_ID: 995880130565918720
  PROVIDER_STATUS: success
  VIDEO_URL_PRESENT: true
  RETAINED_RECOVERABLE_URL: NOT PROVEN
  DURABLE_VIDEO_ASSET: NOT PROVEN
  VIDU2_PROVIDER_CREDITS_REPORTED: 30.0
  VIDU2_ACTUAL_CREDITS_CONSUMED: UNKNOWN / NOT CONFIRMED
  VIDU2_USD_EQUIVALENT: UNKNOWN / NOT CONVERTED

PREP_EXECUTION_INVARIANTS:
  VIDU_GET_CALLS: 0 (Unit test fakes/mocks only; zero real provider calls executed)
  VIDU_POST_CALLS: 0 (Strictly disallowed)
  REAL_PROVIDER_CALLS: 0
  WORKFLOW_DISPATCHES: 0
  PAID_CALLS: 0

P4-WP020: ACTIVE / NOT CLOSED
CORE_V1_PROGRESS: 19 / 20 (95%)
CORE_V1_RELEASE: NOT DECLARED
NEXT_PAID_LIVE_EXECUTION: NONE / NOT AUTHORIZED
PROPOSED_FUTURE_GATE: P4-WP020-LIVE-R5-VIDU2-REC1-RUN1 (Proposed only; requires separate Owner authorization)
```

---

## 1. Background & Purpose

Under Owner authorization in Issue #63 comment `5646093066` and addressing ChatGPT Review ID `5186528822`, this gate `P4-WP020-LIVE-R5-VIDU2-REC1-PREP` implements and tests bounded recovery tooling for historical Vidu Provider Job ID `995880130565918720` (Run `34569728383`).

Historical generation succeeded on the provider side (`state: success`, `video_url_present: true`), but runner ephemeral DB/MinIO teardown and URL masking prevented persistent media retention into an Orbis `Asset`.

This gate prepares zero-cost recovery tooling with strict invariants:
- Zero real provider GET calls
- Zero provider POST / generation calls
- Zero new provider jobs
- Zero workflow dispatches
- Zero live budget additions or reservations

---

## 2. Technical Implementation & Corrective Architecture

### A. Hard Bounding to Exact Historical Provider Job ID
- `ViduExistingJobRecoveryService.validate_authorized_job_id()` checks that `provider_job_id == "995880130565918720"`.
- Any other ID immediately raises `ViduUnauthorizedJobError` **before**:
  - Any network/provider GET
  - Any database query or lineage creation
  - Any object storage access

### B. Historical Execution Fencing
- Reconstructed `GenerationJob` explicitly enforces:
  - `imported_historical = True`
  - `execution_disabled = True`
- Proved via unit tests that the reconstructed job cannot:
  - Be claimed by dispatch workers (`imported_historical.isnot(True)`)
  - Be submitted, retried, or dispatched
  - Be counted as an active/live production job

### C. Transaction Atomicity & Clean Rollback (No Ghost Lineage)
- Preferred sequence implemented in `ViduExistingJobRecoveryService.recover_existing_job`:
  1. Validate authorized `provider_job_id`.
  2. Bounded GET query & status check against provider (`COMPLETED` with usable HTTPS URL).
  3. Pre-check idempotency (if already recovered, reuse existing asset).
  4. Materialize durable video into object storage.
  5. Open DB savepoint: reconstruct deterministic lineage (`Project`, `Scene`, `Shot`, `GenerationJob`), register `Asset`, and record zero-cost `UsageLedger`.
  6. On any failure (task not found, non-completed, missing/unsafe URL, download failure, DB exception):
     - Rollback database transaction/savepoint completely.
     - Remove/compensate newly uploaded storage objects if DB transaction fails.
     - Never delete previously existing idempotent objects.
     - Leave exactly 0 partial Projects, 0 Scenes, 0 Shots, 0 GenerationJobs, 0 orphaned objects.

### D. Durable Billing & Audit Truth
- Preserves conservative audit truth:
  - `provider_job_id = 995880130565918720`
  - `recovery_method = "GET_ONLY_EXISTING_JOB"`
  - `new_generation_posts = 0`
  - `provider_credits_reported = 30.0` (only if returned by provider)
  - `actual_credits_consumed = "UNKNOWN / NOT CONFIRMED"`
  - `usd_equivalent = "UNKNOWN / NOT CONVERTED"`
  - `imported_historical = True`
  - `execution_disabled = True`
- `UsageLedger` record created with:
  - `imported_historical = True`
  - `actual_cost = None`, `estimated_cost = None`, `cost_status = "CONFIRMED"`
  - `BudgetService.get_project_committed_cost()` returns `$0.00`
  - Does NOT increase live committed spend or reserve budget.
  - Strictly idempotent across repeated calls.

### E. Lineage Integrity & Fail-Closed Checks
- Lineage reconstruction validates that if deterministic `Scene` or `Shot` records already exist, their `project_id` and `scene_id` match the expected deterministic IDs. Mismatches raise `ViduConflictingLineageError` without silent mutation.
- Project metadata explicitly marks `imported_historical=True` with `$0.00` allocated budget, preventing historical recovery from masquerading as a new paid run.

---

## 3. Test Evidence

Executed full targeted backend test suites via pytest:
- `backend/tests/test_vidu_recovery.py`: 8 passed (100%)
  - `test_unauthorized_provider_job_id_rejected_before_any_io` (0 GET, 0 POST, 0 DB, 0 storage)
  - `test_recovered_job_is_fenced_and_cannot_be_claimed_or_dispatched`
  - `test_failure_paths_leave_zero_ghost_db_or_storage_artifacts` (TASK_NOT_FOUND, non-completed, missing URL)
  - `test_storage_or_download_failure_rolls_back_cleanly_and_cleans_object`
  - `test_durable_audit_truth_and_budget_isolation` (idempotency, $0 spend)
  - `test_conflicting_lineage_fails_closed`
- `backend/tests/test_video_materialization.py`: 3 passed
- `backend/tests/test_wp020_live_r5_vidu2_contract.py`: 22 passed
- `backend/tests/test_production_orchestrator.py`: 22 passed
- `backend/tests/test_wp020a_zero_billing_e2e.py`: 6 passed

**Total Targeted Backend Tests Passing: 61 passed (100%)**
Zero real provider calls, zero POST requests, zero workflow dispatches executed.

---

## 4. Proposed Future Gate: `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`

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
   - If URL expired (e.g. Vidu retention window exceeded) or task not found: stops safely with documented proof, confirming provider ephemeral retention has lapsed without spending credits or retrying.
5. **STOP Condition**: Collect evidence, record output in control docs, and stop for ChatGPT review.
