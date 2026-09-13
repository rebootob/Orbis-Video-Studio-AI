# P4-WP020-LIVE-R5-VIDU2-REC1-READY1 — Readiness Review for Historical Job Recovery

## Document Metadata

```text
PROJECT: Orbis Video Studio AI
REPOSITORY: rebootob/Orbis-Video-Studio-AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-READY1
TYPE: EVIDENCE-ONLY / READ-ONLY / NO-PROVIDER Readiness Review (Corrective Updated)
STATUS: COMPLETE / BLOCKED FOR LIVE RUN
INSPECTED_MAIN_SHA: ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-ready1
REVIEW_CORRECTIVE: Addressing ChatGPT Review 5189474118 (CHANGES REQUIRED)
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

Under direct Owner authorization in the chat session and following ChatGPT Review `5189474118`, this gate evaluates repository truth, code capability, and operational runtime readiness before any potential execution of `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`.

**Overall Verdict**: **BLOCKED (NOT READY FOR LIVE RUN)**

While the recovery service in `backend/app/services/vidu_recovery.py` demonstrates verified code capability (proven via 27 unit tests in `backend/tests/test_vidu_recovery.py` and 80 targeted backend test suite passes), **operational runtime readiness is not proven**:
1. **Invocation Entry Point**: No CLI runner script, API route endpoint, or GitHub Actions workflow exists to invoke `ViduExistingJobRecoveryService.recover_existing_job`.
2. **Transaction Ownership at Runtime**: In the absence of an operational runner harness, runtime transaction ownership is unassigned.
3. **Approval Gates & Execution Fence**: No runtime execution harness exists to verify fresh Owner authorization markers or consume a one-shot execution fence prior to provider I/O.
4. **Persistence & Retention**:
   - The repository defines local container persistence via named volumes in `docker-compose.yml` (`postgres_data`, `minio_data`).
   - However, deployed operational runtime infrastructure and backing storage retention are **UNKNOWN / NOT VERIFIED** from repository inspection alone.
   - Historical live probe workflows (e.g. `wp020-live-r5-vidu2.yml`) ran in ephemeral GitHub Actions runners without persistent database or object storage attachment.
5. **Historical Media Non-Retention Root Cause**:
   - For historical run `LIVE-20260910-VIDU2-R5` (`34569728383`), non-retention of media was caused by:
     - Sanitized telemetry stripping the raw provider video URL;
     - The video binary was never downloaded or stored by the probe runner;
     - No durable `Asset` or database lineage was materialized.
   - Ephemeral container teardown is a separate prospective durability risk for future recovery workflows.

---

## 2. Detailed Scoped Inspections & Evaluated Topics

### Topic 1: Invocation Path & Transaction Ownership
- **Inspected Sources**:
  - `backend/app/services/vidu_recovery.py` (commit `ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c`, lines 102–655)
  - `backend/tests/test_vidu_recovery.py` (lines 1–1180)
- **Scoped Search Command & Sanitized Results**:
  ```bash
  # Search 1: Service references across backend/
  search_files(path="backend", pattern="ViduExistingJobRecoveryService")
  # Result: Matches found ONLY in backend/app/services/vidu_recovery.py and backend/tests/test_vidu_recovery.py

  # Search 2: Function invocation across .github/ and backend/
  search_files(path=".github", pattern="recover_existing_job")
  # Result: 0 matches

  # Search 3: API endpoints for recovery
  search_files(path="backend/app/api", pattern="recover_existing_job")
  # Result: 0 matches

  # Search 4: Workflow files for recovery
  search_files(path=".github/workflows", pattern="*recovery*")
  # Result: 0 files found

  # Search 5: Runner scripts in .github/scripts/
  # Result: 17 scripts exist (r2, r3, r4, r5_pre1, r5_vidu1, r5_vidu2); ZERO recovery runner scripts exist
  ```
- **Code Capability (PROVEN)**:
  - `ViduExistingJobRecoveryService.recover_existing_job` supports:
    - `commit=True`: executes under a savepoint, executes durable DB commit on success, triggers DB rollback + storage compensation on commit failure.
    - `commit=False`: acts as a caller-owned transaction under a savepoint, releasing savepoint on success, and rolling back savepoint + compensating storage on error without corrupting outer transaction.
- **Runtime Readiness (BLOCKED)**:
  - No caller harness, CLI entrypoint, API route, or workflow exists in the repository to invoke this service.
  - Runtime transaction ownership is unassigned.
- **Status**: **BLOCKED**

---

### Topic 2: Exact Provider Job Bounding (`995880130565918720`)
- **Inspected Sources**:
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
- **Inspected Sources**:
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

### Topic 4: Persistence Architecture & Backing Storage
- **Inspected Sources**:
  - `docker-compose.yml` (lines 12–13, 30–31, 113–115)
  - `backend/app/core/config.py` (lines 22–34)
  - `backend/app/services/storage/factory.py` (lines 15–26)
  - `.github/workflows/wp020-live-r5-pre1.yml` (ephemeral container reference)
  - `project-docs/40_DELIVERY/P4_WP020_LIVE_R5_FINAL_GAP1.md` (historical gap review)
- **Repository Capability (PROVEN)**:
  - `docker-compose.yml` defines local container persistence:
    - Service `db` mounts named volume `postgres_data:/var/lib/postgresql/data`
    - Service `minio` mounts named volume `minio_data:/data`
    - Volume definitions: `volumes: postgres_data: minio_data:`
  - `S3CompatibleObjectStorageProvider` integrates with standard S3/MinIO APIs.
- **Runtime Readiness & Durability (BLOCKED / UNKNOWN)**:
  - **Distinction between Repository Capability and Deployed Runtime**:
    - Repository source proves that Docker Compose is capable of local volume persistence.
    - However, the repository source cannot establish whether an operational cloud database, external managed S3/MinIO bucket, or deployed server environment is active. Current deployed runtime infrastructure is **UNKNOWN / NOT VERIFIED**.
    - No secret-value inspection was requested or performed.
  - **Historical Actions UAT Distinction**:
    - In historical CI and UAT workflows (`wp020-live-r5-pre1.yml`), runners used ephemeral service containers (`postgres:16`) and ephemeral Docker containers (`docker run -d --rm minio/minio`), which discarded state when the runner terminated.
    - If `REC1-RUN1` were executed under an ephemeral runner configuration without persistent external backing storage or verified persistence attachment, recovery records would not be retained.
- **Status**: **BLOCKED (Runtime Persistence Not Verified)**

---

### Topic 5: Asset/Lineage, Historical Audit, Billing UNKNOWN & Evidence
- **Inspected Sources**:
  - `backend/app/services/vidu_recovery.py` (lines 537–615)
  - `backend/app/models/generation_job.py`
  - `backend/app/models/usage_ledger.py`
  - `backend/app/models/asset.py`
- **Code Capability (PROVEN)**:
  - `GenerationJob` marked `imported_historical=True`, `execution_disabled=True`. Cannot be claimed or processed by background workers.
  - `UsageLedger` recorded with `cost_status="UNKNOWN"`, `actual_cost=None`, `estimated_cost=None`, `imported_historical=True`.
  - Provider credits reported (30.0) preserved as metadata without claiming confirmed consumption or USD $0.00 conversion.
  - Fails closed on conflicting durable records (`ViduConflictingLineageError`).
- **Runtime Readiness (BLOCKED)**:
  - No evidence extraction/export script exists to capture `ViduRecoveryResult`, sanitize secrets/tokens/signed URLs, and publish evidence as an immutable artifact or Issue comment.
- **Status**: **READY (Code Level) / BLOCKED (Runtime Level)**

---

## 3. Analysis of Historical VIDU2 Non-Retention

The non-retention of video media in historical run `LIVE-20260910-VIDU2-R5` (`Run 34569728383`) must be accurately attributed per accepted `P4-WP020-LIVE-R5-FINAL-GAP1` truth:
1. **Primary Causes of VIDU2 Non-Retention**:
   - The probe runner (`.github/scripts/wp020_live_r5_vidu2.py`) executed a single live generation POST and polled for completion (`success`, `video_url_present: true`).
   - To prevent credential and private URL leakage, the probe sanitized output evidence, stripping the raw temporary download URL.
   - The probe runner was designed solely to prove provider API generation capability; it did not implement video download, file storage, or asset creation.
   - Consequently, no video binary was downloaded or retained, and no durable `Asset` or `GenerationJob` was materialized in a database.
2. **Separation from Runner Teardown**:
   - While runner container teardown affected state persistence in earlier multi-step UAT runs (such as R4 database state), for VIDU2 RUN1 the video was never downloaded in the first place.
   - Container teardown represents a separate prospective durability risk for future recovery workflows if executed in ephemeral environments.

---

## 4. Identified Gaps & Prerequisites Before REC1-RUN1

To achieve runtime readiness for `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`, the following items must be designed, implemented, and reviewed under separate authorized gates:

1. **Dedicated Recovery CLI Runner Script**:
   - Create a bounded script (e.g. `.github/scripts/wp020_live_r5_vidu2_rec1_runner.py`) that initializes DB session, configures storage, calls `ViduExistingJobRecoveryService.recover_existing_job(commit=True)`, and outputs sanitized JSON evidence.
2. **Dedicated GitHub Actions Workflow**:
   - Create a workflow (e.g. `.github/workflows/wp020-live-r5-vidu2-rec1.yml`) with:
     - `workflow_dispatch` trigger with `mode: dry-run` (default) and `mode: live`.
     - Strict pre-dispatch check for explicit Owner authorization marker and unconsumed one-shot execution fence.
     - Consumption of the execution fence prior to provider network call.
     - Post-run sanitized evidence artifact upload.
3. **Runtime Persistence Clarification**:
   - Owner / Control Plane must specify and verify the operational execution target:
     - **Path A (Local Compose Runtime)**: Execute recovery within an environment backed by `docker-compose.yml` named volumes (`postgres_data`, `minio_data`).
     - **Path B (Managed / External Services)**: Execute recovery against verified persistent external PostgreSQL and S3/MinIO instances.
     - **Path C (Workflow Artifact Backup with Bounded Retention)**: If executed in GitHub Actions, workflow artifacts (`actions/upload-artifact@v4`) provide bounded-retention backups (typically 90 days default). They serve as diagnostic/backup evidence and do NOT automatically constitute an operational durable Orbis Asset tier without a separately approved retention, security, and restoration design.
   - Note: Release assets are excluded from this scope as Core V1 release remains NOT DECLARED and unauthorized.
4. **Evidence Sanitization Contract**:
   - Ensure the runner never leaks `VIDU_API_KEY`, signed download URLs, or internal paths in workflow logs or Issue comments.

---

## 5. Scope of Checks Performed vs Not Performed

```text
CHECKS PERFORMED (Read-Only / Repository Truth):
  - Fresh-fetch canonical main SHA: ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c
  - Scoped code inspection: backend/app/services/vidu_recovery.py
  - Scoped model inspection: backend/app/models/generation_job.py, usage_ledger.py, asset.py
  - Scoped tests inspection: backend/tests/test_vidu_recovery.py (27 unit tests)
  - Scoped script search: .github/scripts/ (confirmed 0 recovery runners)
  - Scoped workflow search: .github/workflows/ (confirmed 0 recovery workflows)
  - Compose configuration inspection: docker-compose.yml (confirmed named volumes)
  - Delivery history inspection: project-docs/40_DELIVERY/

CHECKS NOT PERFORMED / UNAVAILABLE:
  - External server or cloud runtime inspection (not accessible from repository truth)
  - GitHub Actions secret value inspection (prohibited; secret values are protected)
  - Database write or storage write probes (strictly prohibited by gate rules)
  - Provider GET or POST calls (strictly prohibited; REAL VIDU GET = 0)
  - Workflow dispatch or job triggering (strictly prohibited)
```

---

## 6. Invariant Confirmation

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
