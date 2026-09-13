# P4-WP020-LIVE-R5-VIDU2-REC1-PREP — Recovery Tooling & Contract Review

## Status

```text
PROJECT: Orbis Video Studio AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-PREP
TYPE: NO-PAID / NO-PROVIDER Recovery Tooling & Contract Review
STATUS: PASS / MERGED / COMPLETE
MERGED_PR: #103 (https://github.com/rebootob/Orbis-Video-Studio-AI/pull/103)
MERGE_COMMIT: 7ff516f317f84278f6143f15cc58b91fd3fa34d5
REVIEWED_HEAD: 3d3c639d9138ad629bc05ac47ac2df449b984b66
OWNER_AUTHORIZED: YES (Issue #63 comment 5646093066)
ACCEPTED_CHATGPT_REVIEW: 5188678683 — PASS / READY FOR EXPLICIT OWNER MERGE DECISION
AUTHORIZED_BASE_MAIN_SHA: 8cae4bd72bd447470f214cf852b516b856638b7f
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-prep

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

Under Owner authorization in Issue #63 comment `5646093066` and addressing ChatGPT Review ID `5186668549`, this gate `P4-WP020-LIVE-R5-VIDU2-REC1-PREP` completes bounded recovery tooling for historical Vidu Provider Job ID `995880130565918720` (Run `34569728383`).

The historical generation was successful on the provider side, but ephemeral runner teardown prevented durable ingestion. This gate implements zero-cost, idempotent, bounded recovery tooling with strict invariants and zero real provider calls.

---

## 2. Technical Implementation & Corrective Architecture

### A. Real Durable-Commit Safety & Transaction Ownership
- Result payload is constructed immutably prior to commit and returned strictly outside the compensating `try...except` block.
- Removed artificial extension points (`_post_commit_hook`).
- Explicit transaction lifecycle:
  - **`commit=True`**: commits durable DB transaction upon success; compensation deletes newly uploaded object only if DB commit fails.
  - **`commit=False`**: caller-owned transaction behavior executing inside a nested savepoint. On failure, rolls back to savepoint and deletes newly uploaded storage object without corrupting caller's outer transaction.
- Separately proved by tests:
  - **Test A** (`test_db_commit_failure_after_new_upload_cleans_new_storage_object`): DB commit failure before durability -> DB recovery lineage = 0, newly uploaded object deleted.
  - **Test B** (`test_commit_true_succeeds_then_result_delivery_fails_preserves_durability`): `commit=True` succeeds, downstream delivery/consumption fails -> durable DB lineage retained, storage object retained, Asset does not dangle.
  - **Test C** (`test_commit_false_failure_leaves_caller_transaction_safe_and_zero_lineage`): `commit=False` failure -> caller transaction remains active/safe, 0 partial DB lineage, 0 uncompensated storage objects.

### B. Fail Closed on Conflicting Audit Evidence
- Strictly validates existing durable state before declaring idempotent success:
  - `GenerationJob`: `provider_name == "vidu"`, `provider_job_id == "995880130565918720"`, `job_type == "VIDEO"`, `status == "COMPLETED"`, `output_asset_id == Asset.id`, `imported_historical == True`, `execution_disabled == True`.
  - `Asset`: correct deterministic `project_id`, `asset_type == "VIDEO"`.
  - `Scene` and `Shot`: deterministic lineage bindings (`Scene.project_id`, `Shot.scene_id`, `Shot.source_asset_id`).
  - `UsageLedger`: `project_id`, `shot_id`, `job_id`, `provider == "vidu"`, `operation == "historical_recovery_get"`, `provider_event_id`, `idempotency_key`, `cost_status == "UNKNOWN"`, `imported_historical == True`, `actual_cost is None`, `estimated_cost is None`.
  - `GenerationJob.result`: `provider_job_id`, `recovery_method == "GET_ONLY_EXISTING_JOB"`, `new_generation_posts == 0`, `provider_status == "COMPLETED"`, `actual_credits_consumed == "UNKNOWN / NOT CONFIRMED"`, `usd_equivalent == "UNKNOWN / NOT CONVERTED"`, `imported_historical == True`, `execution_disabled == True`.
- **Fail-closed rule**: any conflicting evidence raises `ViduConflictingLineageError` immediately. Does not erase, overwrite, or normalize conflicting cost evidence. Failure leaves original evidence completely unchanged.
- **Repair rule**: fills only genuinely missing fields (e.g. `Shot.source_asset_id is None`, missing `UsageLedger`, missing `result` dictionary keys) while preserving compatible additional evidence.
- Tested:
  - `test_conflicting_actual_cost_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_estimated_cost_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_cost_status_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_imported_historical_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_generation_job_result_fails_closed_and_leaves_evidence_unchanged`

### C. Provider Credits Reporting Truth
- If an earlier recovery stored `provider_credits_reported = 30.0` and a subsequent idempotent GET omits credits, the retained `30.0` evidence is preserved (`test_first_get_credits_30_followed_by_get_credits_none_preserves_durable_credits`).
- If credits were never reported, credits remain `None` (`test_no_credit_history_remains_none_when_credits_were_never_reported`).
- Differentiates:
  - Recovery GET adds zero new generation spend.
  - Historical Vidu generation economic cost remains `UNKNOWN / NOT CONFIRMED` (never described as USD 0).
  - USD equivalent remains `UNKNOWN / NOT CONVERTED`.

### D. Historical Execution Fencing
- Reconstructed `GenerationJob` sets `imported_historical = True` and `execution_disabled = True`.
- Proved via unit test that the job cannot be claimed by workers (`claim_next_job`), dispatched, polled, or counted as an active production job.

---

## 3. Test Evidence

Executed full targeted backend test suites:
- `backend/tests/test_vidu_recovery.py`: 27 passed (100%)
  - `test_unauthorized_provider_job_id_rejected_before_any_io`
  - `test_recovered_job_is_fenced_and_cannot_be_claimed_or_dispatched`
  - `test_failure_paths_leave_zero_ghost_db_or_storage_artifacts` (3 cases)
  - `test_unsafe_private_url_leaves_zero_lineage_and_storage`
  - `test_storage_upload_failure_rolls_back_cleanly`
  - `test_db_commit_failure_after_new_upload_cleans_new_storage_object` (Test A)
  - `test_commit_true_succeeds_then_result_delivery_fails_preserves_durability` (Test B)
  - `test_commit_false_failure_leaves_caller_transaction_safe_and_zero_lineage` (Test C)
  - `test_durable_audit_truth_and_budget_isolation`
  - `test_idempotent_path_with_missing_provider_credits_retains_none`
  - `test_idempotent_audit_evidence_repair`
  - `test_conflicting_lineage_scene_project_id_fails_closed`
  - `test_conflicting_lineage_shot_scene_id_fails_closed`
  - `test_conflicting_generation_job_provider_id_fails_closed`
  - `test_conflicting_asset_project_id_fails_closed`
  - `test_returned_provider_job_id_mismatch_fails_closed`
  - `test_first_get_credits_30_followed_by_get_credits_none_preserves_durable_credits`
  - `test_no_credit_history_remains_none_when_credits_were_never_reported`
  - `test_conflicting_usage_ledger_bindings_fail_closed`
  - `test_conflicting_asset_type_fails_closed`
  - `test_conflicting_actual_cost_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_estimated_cost_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_cost_status_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_imported_historical_fails_closed_and_leaves_evidence_unchanged`
  - `test_conflicting_generation_job_result_fails_closed_and_leaves_evidence_unchanged`
- `backend/tests/test_video_materialization.py`: 3 passed
- `backend/tests/test_wp020_live_r5_vidu2_contract.py`: 22 passed
- `backend/tests/test_production_orchestrator.py`: 22 passed
- `backend/tests/test_wp020a_zero_billing_e2e.py`: 6 passed

**Total Targeted Backend Tests Passing: 80 passed (100%)**
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
