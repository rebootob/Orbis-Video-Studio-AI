# P4-WP020-LIVE-R5-VIDU2-REC1-PREP — Recovery Tooling & Contract Review

## Status

```text
PROJECT: Orbis Video Studio AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-PREP
TYPE: NO-PAID / NO-PROVIDER Recovery Tooling & Contract Review (Corrective Updated)
OWNER_AUTHORIZED: YES (Issue #63 comment 5646093066)
AUTHORIZED_BASE_MAIN_SHA: 8cae4bd72bd447470f214cf852b516b856638b7f
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-prep
CHATGPT_REVIEW_CORRECTED: Review ID 5186603987 (CHANGES REQUIRED addressed)

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

Under Owner authorization in Issue #63 comment `5646093066` and resolving ChatGPT Review ID `5186603987`, this gate `P4-WP020-LIVE-R5-VIDU2-REC1-PREP` finalizes bounded recovery tooling for historical Vidu Provider Job ID `995880130565918720` (Run `34569728383`).

The historical run generated video on the provider side, but ephemeral runner teardown prevented durable asset ingestion. This gate establishes zero-cost, idempotent, bounded GET recovery tooling without running any real provider queries or generating new jobs.

---

## 2. Technical Implementation & Corrective Architecture

### A. Hard Bounding to Exact Historical Provider Job ID
- `ViduExistingJobRecoveryService.validate_authorized_job_id()` strictly asserts `provider_job_id == "995880130565918720"`.
- Rejecting unauthorized IDs occurs before any provider GET, POST, database operation, or object storage access.

### B. Transaction Handling & Storage Compensation
- Transaction handling ensures that if `db.commit()` fails after a new storage upload:
  - The owning DB transaction/savepoint is safely rolled back.
  - Storage compensation executes even if savepoint rollback encounters an issue.
  - Deletes only newly uploaded objects from the current attempt; never deletes pre-existing idempotent objects.
  - Never masks the original root exception.
- Verified by tests: `test_db_commit_failure_after_new_upload_cleans_new_storage_object` and `test_storage_upload_failure_rolls_back_cleanly`.

### C. Idempotent Path & Relationship Validation
- Idempotent recovery validates deterministic entity relationships:
  - Exact `provider_job_id` matches on `GenerationJob`.
  - `GenerationJob.output_asset_id == Asset.id`.
  - `Asset.project_id == deterministic project_id`.
  - `Scene.project_id == deterministic project_id`.
  - `Shot.scene_id == deterministic scene_id`.
  - `GenerationJob.shot_id == deterministic shot_id`.
- If conflicting relationships exist, fails closed (`ViduConflictingLineageError`) without silent mutation.
- Non-conflicting incomplete fencing/audit state (`imported_historical`, `execution_disabled`, `Shot.source_asset_id`, `UsageLedger`) is safely repaired inside the transaction.
- Accurately tracks `get_calls_attempted` based on provider queries performed.
- Provider credits reported reflect only current safe provider response (e.g. `None` when provider omits credits, never hard-coded).

### D. Billing Semantics & Cost Status
- Uses conservative `cost_status = "UNKNOWN"` in `UsageLedger`.
- Differentiates:
  - Recovery GET adds zero new generation spend.
  - Historical Vidu generation economic cost remains `UNKNOWN / NOT CONFIRMED`.
  - Credits reported (30.0) are provider-reported only if returned.
  - USD equivalent remains `UNKNOWN / NOT CONVERTED`.
  - Historical generation is never described as USD 0.

### E. Historical Execution Fencing
- Every reconstructed `GenerationJob` enforces `imported_historical = True` and `execution_disabled = True`.
- Proved via unit test that the job cannot be claimed by workers (`claim_next_job`), dispatched, polled, or counted as an active production job.

---

## 3. Test Evidence

Executed full targeted backend test suites:
- `backend/tests/test_vidu_recovery.py`: 15 passed (100%)
  - `test_unauthorized_provider_job_id_rejected_before_any_io`
  - `test_recovered_job_is_fenced_and_cannot_be_claimed_or_dispatched`
  - `test_failure_paths_leave_zero_ghost_db_or_storage_artifacts` (3 cases: 404, not COMPLETED, missing URL)
  - `test_unsafe_private_url_leaves_zero_lineage_and_storage`
  - `test_storage_upload_failure_rolls_back_cleanly`
  - `test_db_commit_failure_after_new_upload_cleans_new_storage_object`
  - `test_durable_audit_truth_and_budget_isolation`
  - `test_idempotent_path_with_missing_provider_credits_retains_none`
  - `test_idempotent_audit_evidence_repair`
  - `test_conflicting_lineage_scene_project_id_fails_closed`
  - `test_conflicting_lineage_shot_scene_id_fails_closed`
  - `test_conflicting_generation_job_provider_id_fails_closed`
  - `test_conflicting_asset_project_id_fails_closed`
- `backend/tests/test_video_materialization.py`: 3 passed
- `backend/tests/test_wp020_live_r5_vidu2_contract.py`: 22 passed
- `backend/tests/test_production_orchestrator.py`: 22 passed
- `backend/tests/test_wp020a_zero_billing_e2e.py`: 6 passed

**Total Targeted Backend Tests Passing: 68 passed (100%)**
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
   - If URL expired or task not found: stops safely with documented proof, confirming provider ephemeral retention has lapsed without spending credits or retrying.
5. **STOP Condition**: Collect evidence, record output in control docs, and stop for ChatGPT review.
