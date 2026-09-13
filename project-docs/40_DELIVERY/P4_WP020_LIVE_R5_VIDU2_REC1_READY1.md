# P4-WP020-LIVE-R5-VIDU2-REC1-READY1 — Readiness Review for Historical Job Recovery

## Document Metadata

```text
PROJECT: Orbis Video Studio AI
REPOSITORY: rebootob/Orbis-Video-Studio-AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-READY1
TYPE: EVIDENCE-ONLY / READ-ONLY / NO-PROVIDER Readiness Review
STATUS: COMPLETE / BLOCKED FOR LIVE RUN
INSPECTED_MAIN_SHA: ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-ready1
OWNER_AUTHORIZATION: Direct chat session instruction (Readiness review before REC1-RUN1; no Issue #63 comment claimed)

INVARIANTS HELD DURING REVIEW:
  REAL_VIDU_GET_CALLS: 0
  VIDU_GENERATION_POSTS: 0
  REAL_PROVIDER_CALLS: 0
  WORKFLOW_DISPATCHES: 0
  PAID_CALLS: 0
  CODE_CHANGES: 0 (Strictly DOCS-ONLY report)
```

---

## 1. Executive Summary

Under direct Owner authorization in the chat session, this gate evaluates the repository truth, source implementation, and runtime readiness before any potential live execution of `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`.

**Overall Verdict**: **BLOCKED (NOT READY FOR LIVE RUN)**

While the underlying service logic in `backend/app/services/vidu_recovery.py` has proven code capability through 27 unit tests and 80 targeted backend test suite passes, **runtime readiness is not proven**:
1. **Invocation Path & Entry Point**: There is no runtime script, CLI entry point, API router, or GitHub Actions workflow to invoke recovery.
2. **Transaction Ownership in Production**: Because no runtime harness exists, runtime transaction ownership is unassigned.
3. **Approval Gates & Execution Fence**: No live workflow or runner script exists to check fresh Owner authorization or consume a one-shot execution fence before issuing provider GET requests.
4. **Durable Persistence**: Past UAT environments used ephemeral Docker PostgreSQL and ephemeral Docker MinIO containers (`--rm`) which destroyed all data upon runner completion. No persistent database or persistent object storage with post-runner retention is configured or proven for this repository.

---

## 2. Detailed Topic Evaluations

### Topic 1: Invocation Path & Transaction Ownership
- **Source References**:
  - `backend/app/services/vidu_recovery.py` (lines 102–655)
  - `backend/tests/test_vidu_recovery.py` (lines 1–1180)
- **Code Capability (PROVEN)**:
  - `ViduExistingJobRecoveryService.recover_existing_job(db: Session, provider_job_id: str, ..., commit: bool = True)` provides clean transaction semantics:
    - When `commit=True`: executes under a savepoint, performs durable DB commit on success, and triggers DB rollback + storage object deletion on commit failure.
    - When `commit=False`: acts as a caller-owned transaction under a savepoint, releasing savepoint on success, and rolling back savepoint + compensating storage on error without corrupting outer transaction.
- **Runtime Readiness (BLOCKED)**:
  - Repository search reveals zero operational entry points:
    - No CLI runner script in `.github/scripts/` or `backend/scripts/`.
    - No API router endpoint in `backend/app/api/`.
    - No GitHub Actions workflow in `.github/workflows/`.
  - Transaction ownership during actual runtime cannot be determined because no caller exists.
- **Status**: **BLOCKED**

---

### Topic 2: Exact Provider Job Bounding (`995880130565918720`)
- **Source References**:
  - `backend/app/services/vidu_recovery.py` (lines 46, 104–110, 240, 247–251)
  - `backend/tests/test_vidu_recovery.py` (lines 78–122, 915–943)
- **Code Capability (PROVEN)**:
  - Constant `TARGET_HISTORICAL_PROVIDER_JOB_ID = "995880130565918720"` is hard-coded.
  - `validate_authorized_job_id()` strictly raises `ViduUnauthorizedJobError` before any provider request, DB write, or storage write if the ID differs.
  - `recover_existing_job()` verifies provider-returned `job_result.provider_job_id` matches `995880130565918720`, failing closed with `ViduConflictingLineageError` if mismatched.
  - Deterministic UUIDs generated via `uuid.uuid5(uuid.NAMESPACE_URL, ...)` guarantee deterministic idempotency.
- **Runtime Readiness (BLOCKED)**:
  - Code guards are complete, but without an invocation script or workflow, parameters cannot be verified in an operational environment.
- **Status**: **READY (Code Level) / BLOCKED (Runtime Level)**

---

### Topic 3: Guardrails: GET ≤ 1, POST = 0, No Retry/Fallback, Pre-I/O Approval Gate
- **Source References**:
  - `backend/app/services/vidu_recovery.py` (lines 243–265)
  - `.github/workflows/wp020-live-r5-vidu2.yml` (historical reference for probe guardrail structure)
- **Code Capability (PROVEN)**:
  - Calls `await vidu_adapter.check_job_status(provider_job_id)` exactly once.
  - Zero calls to `submit_generation_job()` or any POST endpoint (`posts_attempted = 0`, `get_calls_attempted = 1`).
  - No loop, polling retry, or fallback adapter: immediately raises `ViduJobNotCompletedError` or `ViduRecoveryError` if status is not completed.
- **Runtime Readiness (BLOCKED)**:
  - In previous live probes (e.g. `wp020-live-r5-vidu2.yml`), approval gates and execution fences were enforced via GitHub Actions steps parsing Issue comments (`FRESH_OWNER_AUTHORIZED_VIDU2:...`, `EXECUTION_STARTED:...`).
  - For `REC1-RUN1`, no corresponding workflow exists. There is no pre-I/O fence check or rate guard in an operational deployment.
- **Status**: **READY (Code Level) / BLOCKED (Runtime Level)**

---

### Topic 4: Durable Persistence (Database & Object Storage)
- **Source References**:
  - `backend/app/core/config.py` (lines 22–34, `POSTGRES_*`, `OBJECT_STORAGE_*`)
  - `backend/app/services/storage/factory.py` (lines 15–26)
  - `.github/workflows/wp020-live-r5-pre1.yml` (lines 20–33, 95–109)
  - `project-docs/00_CONTROL/CURRENT_STATE.md` (line 192: ephemeral container limitation)
- **Code Capability (PROVEN)**:
  - Service creates and links `Project`, `Scene`, `Shot`, `GenerationJob`, `Asset`, and `UsageLedger`.
  - Object storage upload uses `storage.upload_file_object()`.
  - Atomic rollback: deletes newly uploaded storage object if DB commit fails.
- **Runtime Readiness (BLOCKED)**:
  - **The Ephemeral Runner Problem**:
    - All past live executions (R1–R4, R5 PRE1) executed in GitHub-hosted Ubuntu runners (`ubuntu-latest`).
    - PostgreSQL was executed as an ephemeral service container (`postgres:16`).
    - MinIO was executed as an ephemeral Docker container (`docker run -d --rm minio/minio`).
    - Once the runner completed, all database rows and uploaded files were permanently destroyed.
    - This is the explicit reason why `CURRENT_STATE.md` and `CHAT_HANDOFF.md` document:
      - `Retained recoverable URL: NOT PROVEN`
      - `Durable VIDEO Asset: NOT PROVEN`
  - In the current repository configuration:
    - There is no persistent external PostgreSQL instance configured via secrets.
    - There is no persistent external S3/MinIO bucket configured via secrets.
    - If `REC1-RUN1` runs in a standard ephemeral GitHub Actions runner, the recovered video asset and DB records will disappear upon runner completion, failing the durability objective.
- **Status**: **BLOCKED**

---

### Topic 5: Asset/Lineage, Historical Audit, Billing UNKNOWN & Sanitized Evidence
- **Source References**:
  - `backend/app/services/vidu_recovery.py` (lines 537–615)
  - `backend/models/generation_job.py`
  - `backend/models/usage_ledger.py`
- **Code Capability (PROVEN)**:
  - `GenerationJob` marked `imported_historical=True`, `execution_disabled=True`. Cannot be claimed or processed by background workers.
  - `UsageLedger` recorded with `cost_status="UNKNOWN"`, `actual_cost=None`, `estimated_cost=None`, `imported_historical=True`.
  - Provider credits reported (30.0) preserved as metadata without claiming confirmed consumption or USD $0.00 conversion.
  - Fails closed on conflicting durable records (`ViduConflictingLineageError`).
- **Runtime Readiness (BLOCKED)**:
  - No evidence capture/export script exists to extract `ViduRecoveryResult`, sanitize secrets/tokens/signed URLs, and publish evidence as an immutable artifact or Issue comment.
- **Status**: **READY (Code Level) / BLOCKED (Runtime Level)**

---

## 3. Identified Gaps & Missing Runtime Components

To achieve runtime readiness for `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`, the following items must be designed, implemented, and reviewed under separate authorized gates:

1. **Dedicated Recovery CLI Runner Script**:
   - Create a bounded script (e.g. `.github/scripts/wp020_live_r5_vidu2_rec1_runner.py`) that initializes DB session, configures storage, calls `ViduExistingJobRecoveryService.recover_existing_job(commit=True)`, and outputs sanitized JSON evidence.
2. **Dedicated GitHub Actions Workflow**:
   - Create a workflow (e.g. `.github/workflows/wp020-live-r5-vidu2-rec1.yml`) with:
     - `workflow_dispatch` trigger with `mode: dry-run` (default) and `mode: live`.
     - Strict pre-dispatch check for explicit Owner authorization marker and unconsumed one-shot execution fence.
     - Consumption of the execution fence prior to provider network call.
     - Post-run sanitized evidence artifact upload.
3. **Architectural Resolution for Persistence**:
   - The Owner / Control Plane must decide how persistence is guaranteed:
     - **Option A (External Backing Services)**: Provide credentials for an external persistent PostgreSQL and S3-compatible storage bucket.
     - **Option B (Artifact-Backed Durability)**: If running in GitHub Actions with ephemeral containers, export the recovered video file and database snapshot as cryptographically verified workflow artifacts (`actions/upload-artifact@v4`) and/or release assets, accompanied by SHA-256 checksums in Issue comments.
4. **Evidence Sanitization Contract**:
   - Ensure the runner never leaks `VIDU_API_KEY`, signed download URLs, or internal paths in workflow logs or Issue comments.

---

## 4. Invariant Confirmation

```text
REAL_VIDU_GET_CALLS: 0
VIDU_GENERATION_POSTS: 0
REAL_PROVIDER_CALLS: 0
PAID_CALLS: 0
NEW_PROVIDER_JOBS: 0
WORKFLOW_DISPATCHES: 0

P4-WP020: ACTIVE / NOT CLOSED
COMPLETED_CORE_V1_WPS: 19 / 20 (95%)
CORE_V1_RELEASE: NOT DECLARED
PROVIDER_LIVE_EXECUTION: NONE / NOT AUTHORIZED
REC1-RUN1: PROPOSED ONLY / BLOCKED / NOT AUTHORIZED

HISTORICAL_VIDU2_EXECUTION:
  EXECUTION_ID: LIVE-20260910-VIDU2-R5
  TARGET_HISTORICAL_PROVIDER_JOB_ID: 995880130565918720
  PROVIDER_CREDITS_REPORTED: 30.0
  ACTUAL_CREDITS_CONSUMED: UNKNOWN / NOT CONFIRMED
  USD_EQUIVALENT: UNKNOWN / NOT CONVERTED
  RETAINED_RECOVERABLE_URL: NOT PROVEN
  DURABLE_VIDEO_ASSET: NOT PROVEN
```
