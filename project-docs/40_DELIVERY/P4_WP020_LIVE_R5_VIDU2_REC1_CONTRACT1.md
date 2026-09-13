# P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 — Runtime & Recovery Contract

## Document Metadata

```text
PROJECT: Orbis Video Studio AI
REPOSITORY: rebootob/Orbis-Video-Studio-AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 (Gate A — Runtime & Recovery Contract)
TYPE: DESIGN / DOCS-ONLY / NO-PROVIDER Specification
STATUS: COMPLETE / READY FOR CHATGPT INDEPENDENT REVIEW
CANONICAL_BASE_MAIN_SHA: 0326def88915b25fbb4e2b7019753c2b3fedc0f7
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-contract1
OWNER_AUTHORIZATION: Direct chat session instruction (Gate A contract; no Issue #63 comment claimed)

INVARIANTS HELD:
  REAL_VIDU_GET_CALLS: 0
  VIDU_GENERATION_POSTS: 0
  REAL_PROVIDER_CALLS: 0
  PAID_CALLS: 0
  NEW_PROVIDER_JOBS: 0
  WORKFLOW_DISPATCHES: 0
  CODE_CHANGES: 0 (Strictly DOCS-ONLY specification)
  REC1_RUN1_STATUS: BLOCKED / NOT AUTHORIZED
  P4_WP020_STATUS: ACTIVE / NOT CLOSED
  CORE_V1_PROGRESS: 19 / 20 WPs (95%)
  CORE_V1_RELEASE: NOT DECLARED
  LIVE_EXECUTION: NONE / NOT AUTHORIZED
```

---

## 1. Executive Summary & Purpose

Following the readiness review in `P4_WP020_LIVE_R5_VIDU2_REC1_READY1.md` (PR #105, merge commit `0326def88915b25fbb4e2b7019753c2b3fedc0f7`) which established that the recovery service has proven code capability but lacks operational runtime readiness, this document establishes the **authoritative engineering and governance contract** for:
1. **Persistent Cloud UAT Environment**: Decoupling persistence from ephemeral CI runners to guarantee data retention across restarts.
2. **Bounded Recovery Harness**: A strictly single-purpose invocation harness reusing `ViduExistingJobRecoveryService` targeting historical job `995880130565918720`.
3. **Atomic One-Shot Approval Fence**: Guaranteeing that live provider GET is issued at most once (`GET ≤ 1`), with fail-closed behavior on crash or ambiguity.
4. **Durable Materialization & Compensation**: Ensuring transactional consistency between PostgreSQL lineage and object storage.
5. **Historical Audit & Billing Fence**: Idempotent tracking without claiming confirmed consumption or USD conversion.
6. **Multi-Gate Roadmap**: A strict sequential gate model where each phase requires explicit Owner authorization and no auto-progression is permitted.

**Scope of this Gate**: Strictly architectural specification and contract design. No code implementation, schema modification, cloud deployment, provider calls, or secret inspection are performed or authorized.

---

## 2. Persistent Cloud UAT Architecture (Decoupled from Production)

### 2.1 Environmental Boundaries
- **UAT vs Production Isolation**: The UAT environment must run in completely isolated database and object storage namespaces from any prospective production environment.
- **Components**:
  - **Relational Database**: Managed PostgreSQL (version 16+ compatible) with automated point-in-time recovery (PITR) or regular snapshot capability.
  - **Object Storage**: Private, S3-compatible object storage (e.g. AWS S3, Cloudflare R2, MinIO on persistent volume) with private read/write access via IAM credentials.
- **Stateless Compute**:
  - Execution runners (GitHub Actions runners, containerized workers, or local development daemons) must be treated as completely ephemeral and replaceable.
  - Teardown, restart, or re-provisioning of compute runners must cause **zero data loss** to database records or stored media assets.

### 2.2 Configuration, Secrets & Host Isolation
- **No Developer Host Coupling**: Operational runtime must not depend on local paths, local environment variables, or developer machine state (`C:\Users\...`).
- **Secrets Management**:
  - Runtime credentials (`POSTGRES_SERVER`, `POSTGRES_PASSWORD`, `OBJECT_STORAGE_ACCESS_KEY`, `OBJECT_STORAGE_SECRET_KEY`, `VIDU_API_KEY`) must be provisioned via secure GitHub Secrets or cloud environment secret stores.
  - Zero secret values may be logged, exported to artifacts, or committed to repository files.

### 2.3 Deployed Runtime Status: UNKNOWN / NOT VERIFIED
- Per repository truth, `docker-compose.yml` defines named volumes (`postgres_data`, `minio_data`) for local multi-container development.
- However, the existence, configuration, and connectivity of any external cloud PostgreSQL instance or external S3-compatible storage bucket remain **UNKNOWN / NOT VERIFIED**.
- **Rule**: Neither Hermes, ChatGPT, nor Antigravity may assume external cloud infrastructure is provisioned without explicit verified read-only connection evidence provided in a future dedicated infrastructure gate.

### 2.4 Governance & Cost Ceiling
- **Prohibited Actions in Gate A**:
  - No account creation, subscription selection, credit card entry, or quota/billing adjustments.
  - No infrastructure deployment (Terraform, Pulumi, CloudFormation, or manual provisioning).
- **Cost Separation**: Infrastructure hosting costs (PostgreSQL, storage egress/ingress) must be evaluated and approved under a separate infrastructure budget, distinct from the historical **USD $1.00 provider UAT budget**.

---

## 3. Recovery Harness Contract

### 3.1 Service Reuse & Target Bounding
- The recovery harness must directly invoke `ViduExistingJobRecoveryService.recover_existing_job()` in `backend/app/services/vidu_recovery.py`.
- **Target Provider Job ID**: Strictly bounded to hardcoded constant `TARGET_HISTORICAL_PROVIDER_JOB_ID = "995880130565918720"`.
- **Pre-Mutation Validation**:
  - The harness must invoke `validate_authorized_job_id(provider_job_id)` before initiating any network I/O, database writes, or storage operations.
  - Any parameter mismatch must raise `ViduUnauthorizedJobError` and immediately abort with exit code `1`.

### 3.2 Provider Call Limits (Transport & Application)
- **Generation POST Calls**: Strictly `0` (Zero). Calling `submit_generation_job` or any provider creation endpoint is completely prohibited.
- **Provider Status GET Calls**: Strictly `≤ 1` across the entire recovery lifecycle for the execution identity.
- **Transport Retry Policy**:
  - In standard HTTP clients, transient errors (e.g. 502, 503, 504, connection reset) might trigger client-level transport retries.
  - **Contract Rule**: For this historical recovery probe, automatic transport retries are capped at `0` (no retry). If the single GET request fails, times out, or returns a network error, the harness must record the error, mark the fence as `DISPATCHED_UNKNOWN`, and **STOP**.
- **No Polling Loops**: Polling loops are prohibited. If provider returns `status != "success"` (e.g., `processing` or `failed`), the harness must fail closed with `ViduJobNotCompletedError` and not enter a wait/retry loop.
- **No Fallback Providers**: If Vidu recovery fails, no fallback adapter (e.g., Mock, Gemini, ElevenLabs) may be invoked.

### 3.3 Mock Mode & Decoupled Verification
- The harness must provide a dry-run / mock mode:
  - Executes full validation of inputs, database models, savepoints, and deterministic ID calculation.
  - Operates without requiring live provider credentials (`VIDU_API_KEY`).
  - Never touches provider network endpoints.
- **No Generic API**: No public REST API route or generic Hermes tool integration may be introduced. The harness must be a tightly bounded, single-purpose CLI runner script.

---

## 4. Approval Fence & One-Shot Execution Contract

### 4.1 Four-Point Authorization Anchor
Before any live network request to Vidu is initiated, the execution harness must verify an explicit, unbroken four-point authorization binding:
1. **Exact Git Commit SHA**: Must match the Owner-authorized commit on canonical `main` or authorized branch.
2. **Task ID**: Must match `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`.
3. **Provider Job ID**: Must strictly match `995880130565918720`.
4. **Runtime Target**: Must specify the exact verified persistent environment (e.g., `UAT-COMPOSE-PERSISTENT` or `UAT-CLOUD-STAGING`).

### 4.2 Atomic Durable Fence Prior to Provider I/O
- To prevent accidental duplicate runs, concurrent invocations, or rerun loops, an **atomic durable fence** must be recorded in the database *before* issuing the network GET request.
- **Canonical Existing Model for Fence**:
  - The repository models `OrchestrationAudit` (`backend/app/models/orchestration_audit.py`) and `UsageLedger` (`backend/app/models/usage_ledger.py`) already support durable state recording without requiring new database migrations or schema alterations.
  - `UsageLedger` enforces a unique partial constraint on `(job_id, operation)` and deterministic UUIDs (`uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://vidu-recovery/ledger/{provider_job_id}")`).
- **Atomic Fencing Protocol**:
  1. Generate deterministic fence record with state `RECOVERY_DISPATCHED`.
  2. Commit fence record to persistent database. If the record already exists, the transaction fails immediately with a uniqueness violation (`DuplicateExecutionError`), halting execution before any provider I/O.
  3. Issue provider GET request (`check_job_status`).
  4. On successful materialization, update fence record to `RECOVERY_COMPLETED`.

### 4.3 Crash Windows & Failure Reconciliation
If the runner process terminates abnormally, the state must be safely reconcilable based on the exact failure window:

| Failure Window | Point of Interruption | DB State | Storage State | Protocol Action on Next Run |
|---|---|---|---|---|
| **Window 1: Pre-GET** | Process dies after fence written, before network call | Fence = `DISPATCHED` | Clean | **STOP**. Requires manual inspection of provider audit logs to confirm GET was not received before fence reset. |
| **Window 2: Mid-GET** | Network timeout / process killed during GET call | Fence = `DISPATCHED` | Clean | **STOP**. Provider status unknown. Must not retry GET automatically. Reconciliation gate required. |
| **Window 3: Post-GET, Pre-Storage** | Result received, process dies before S3 upload | Fence = `DISPATCHED` | Clean | **STOP**. Result payload lost in ephemeral memory. Manual review required. |
| **Window 4: Mid-Storage** | S3 upload partially completed or times out | Fence = `DISPATCHED` | Partial / Orphan S3 object | **STOP**. Automated or manual S3 compensation required to prune orphan key. |
| **Window 5: Post-Storage, Pre-DB Commit** | File in S3, DB commit fails / process crashes | Fence = `DISPATCHED` (savepoint rolled back) | Uploaded S3 object | S3 compensation triggered in `finally` block. If compensation fails, log orphan key in audit. |

**Strict Rule**: In ALL crash windows where a fence was consumed, automatic retry is strictly **FORBIDDEN**. Execution must halt until independent evidence is evaluated.

---

## 5. Durable Materialization & Compensation Contract

### 5.1 Validation of Provider Result
- Prior to creating database records or downloading media:
  - Verify `job_result.provider_job_id == "995880130565918720"`.
  - Verify `job_result.status == "success"`.
  - Validate `job_result.video_url`:
    - Must be a non-empty string.
    - Must use HTTPS scheme (`https://`).
    - Must parse as a valid URL.
    - If URL is expired, invalid, or inaccessible, raise `ViduInvalidMediaUrlError` and abort.

### 5.2 Transactional Integrity & Lineage Reconstruction
- **Lineage Components**:
  - `Project` (deterministic UUID via `uuid5`)
  - `Scene` (scene_number: 1)
  - `Shot` (shot_number: 1, duration: 4.0s, visual_prompt preserved)
  - `GenerationJob` (status: `COMPLETED`, `imported_historical=True`, `execution_disabled=True`)
  - `Asset` (asset_type: `VIDEO`, content_type: `video/mp4`, storage_bucket, storage_key, checksum_sha256)
  - `UsageLedger` (cost_status: `UNKNOWN`, `imported_historical=True`)
- **Transaction Ownership**:
  - All DB entities must be created within a single managed database transaction.
  - Either all records commit together atomically, or all are rolled back.
  - If conflicting lineage already exists with mismatched attributes, fail closed with `ViduConflictingLineageError`.

### 5.3 Storage Compensation & Orphan Handling
- Because object storage operations (S3 PUT) and database transactions (SQL COMMIT) cannot participate in a distributed two-phase commit:
  - The video binary must be downloaded and uploaded to object storage *prior* to final database `db.commit()`.
  - If the database commit raises an exception, the service must execute compensation: delete the uploaded object from S3 using `storage.delete_file(bucket, storage_key)`.
  - If the compensation deletion itself fails (e.g. S3 outage), the service must log a critical alert containing the exact bucket and key for offline garbage collection.

### 5.4 Post-Success Read-Back Verification
- To definitively prove durable retention:
  1. Commit database transaction.
  2. Perform immediate independent read-back query from database to confirm records exist.
  3. Perform read-back head/get request from object storage to verify:
     - File exists in bucket.
     - Byte length matches recorded `Asset.file_size_bytes`.
     - Compute SHA-256 of stored object and verify exact match with `Asset.checksum_sha256`.
- **Role of Workflow Artifacts**:
  - GitHub Actions artifacts (`actions/upload-artifact@v4`) serve as secondary, bounded-retention backups (typically 90 days default).
  - Artifacts do **not** substitute for operational, durable object storage assets.

---

## 6. Historical Audit & Billing Fence Contract

### 6.1 Historical Record Immutability
- All recovered records must be explicitly marked:
  - `GenerationJob.imported_historical = True`
  - `GenerationJob.execution_disabled = True`
  - `UsageLedger.imported_historical = True`
  - `UsageLedger.cost_status = "UNKNOWN"`
- **Worker Isolation**: The render worker (`app.services.render_worker`) and queue dispatcher (`app.services.job_dispatch`) must never claim, execute, submit, or retry jobs with `execution_disabled=True` or `imported_historical=True`.

### 6.2 Truthful Credit & Cost Accounting
- **Provider Credits**:
  - Vidu returned `credits: 30.0` in historical telemetry.
  - Recorded as raw provider metadata: `provider_credits_reported = 30.0`.
  - Actual consumed credits: **UNKNOWN / NOT CONFIRMED**.
  - USD equivalent: **UNKNOWN / NOT CONVERTED** (no arbitrary pricing conversion to $0.00 or $0.30 may be fabricated).
- **Budget Protection**:
  - The historical recovery probe must not record synthetic spend that inflates or duplicates the historical **USD $1.00 UAT budget**.
  - Live spend addition: **$0.00**.

---

## 7. Comprehensive Acceptance Matrix

| Requirement | Existing Source / Model | Proposed Contract / Change | Verification Test | Required Evidence | STOP Condition |
|---|---|---|---|---|---|
| **1. Wrong Provider Job ID** | `backend/app/services/vidu_recovery.py` (`TARGET_HISTORICAL_PROVIDER_JOB_ID`) | Reject any ID other than `995880130565918720` before any I/O | Unit test with randomized ID | `ViduUnauthorizedJobError` raised; 0 network/DB calls | Any non-matching ID provided |
| **2. Duplicate / Concurrent Request** | `backend/app/models/usage_ledger.py` (`uq_usage_ledger_job_operation`) | Unique deterministic ID / DB constraint fails atomic fence | Concurrency simulation test | Second caller receives `IntegrityError` / `DuplicateExecutionError` | Fence record already exists |
| **3. Stale / Missing Authorization** | Control doc ruleset (`AGENTS.md`) | Runner checks 4-point authorization anchor in environment | Preflight test without auth marker | Runner aborts with auth error before DB connection | Auth marker missing or commit SHA mismatch |
| **4. Already Consumed Fence** | `backend/app/models/orchestration_audit.py` | State check verifies fence is not in `DISPATCHED` or `COMPLETED` | Test with pre-existing fence record | Harness stops with `FenceAlreadyConsumedError` | Fence state != `INITIAL` |
| **5. Task Gone / Not Completed** | `ViduExistingJobRecoveryService.recover_existing_job` | Check `job_result.status == "success"`; fail closed on others | Mock provider returning `failed` / `processing` | `ViduJobNotCompletedError` raised; no media written | Provider returns non-success |
| **6. Missing / Unsafe / Expired URL** | `ViduExistingJobRecoveryService._validate_media_url` | Validate HTTPS scheme, hostname, and expiration header | Test with `http://`, malformed, or 404 URL | `ViduInvalidMediaUrlError` raised; DB rolled back | URL missing, insecure, or invalid |
| **7. Media Download / Storage Failure** | `ViduExistingJobRecoveryService._download_and_store_media` | Stream download to temporary buffer; atomic S3 upload | Mock network timeout during stream | Exception caught; DB savepoint rolled back; zero corrupt rows | Download or S3 upload fails |
| **8. Compensation Failure** | `ViduExistingJobRecoveryService` (`try...except` compensation) | Log critical orphan record if S3 deletion fails on DB error | Mock S3 delete error during DB rollback | Critical log generated with bucket/key details | Compensation fails (flag for audit) |
| **9. Process Crash Recovery** | Crash window matrix (Section 4.3) | Any crash after fence consumption stops automatic execution | Crash simulation after step 2 | State remains `DISPATCHED`; subsequent run halts | Crash detected (requires Owner manual review) |
| **10. Historical Fencing** | `backend/app/models/generation_job.py` | `imported_historical=True`, `execution_disabled=True` | Background worker query test | Background worker excludes job from query results | Job eligible for queue claim |
| **11. Retention & Read-Back Proof** | Post-recovery validation suite | Query DB, download S3 object, compute SHA-256, verify match | End-to-end dry run test | SHA-256 matches exactly; byte length matches | Read-back mismatch or file missing |

---

## 8. Multi-Gate Execution Roadmap

Progress toward live recovery and WP020 closure is strictly structured into sequential, independent gates:

```text
[ Gate A: Contract & Architecture ]  <-- CURRENT ACTIVE GATE (P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1)
               │
               ▼  (Requires Owner Approval + Merge of Gate A PR)
[ Gate B: Harness & Preflight Implementation ] (NO-PROVIDER, mock tests, CLI runner)
               │
               ▼  (Requires Owner Approval + Merge of Gate B PR)
[ Gate C: Infrastructure & Persistence Proof ] (Verify persistent DB/S3, read-back proof, NO-PROVIDER)
               │
               ▼  (Requires Owner Explicit Live Authorization)
[ Gate D: Bounded Live Recovery Probe ] (P4-WP020-LIVE-R5-VIDU2-REC1-RUN1: GET ≤ 1, exact job 995880130565918720)
               │
               ▼  (Requires Owner Acceptance of Live Evidence)
[ Gate E: Post-Recovery Control Sync & Closure ] (DOCS-ONLY post-run sync)
               │
               ▼  (Requires Owner Authorization)
[ Gate F: P4-WP020 Final Gate Review & Core V1 Release Assessment ]
```

**Sequential Progression Rules**:
1. No gate may be started automatically upon completion of the previous gate.
2. Each gate requires a distinct feature branch, a dedicated PR, passing exact-head CI, ChatGPT independent review PASS, and explicit Owner merge/execution authorization.
3. If at any point the target task or media URL on Vidu is unavailable or expired, execution must **STOP**. No replacement generation may be initiated automatically.

---

## 9. Open Questions & Owner Decisions Needed

Before proceeding to **Gate B (Harness Implementation)** and **Gate C (Infrastructure Verification)**, the Owner's direction is requested on the following architectural items:

1. **Persistent Cloud Environment Target**:
   - *Option 1*: Dedicated cloud-hosted PostgreSQL and S3-compatible storage (e.g. AWS / Supabase / Neon / Cloudflare R2).
   - *Option 2*: Persistent Linux host / VM running Docker Compose with durable named host volumes (`postgres_data`, `minio_data`).
2. **Execution Runner Target for Live Probe**:
   - *Option A*: GitHub Actions workflow triggered via `workflow_dispatch` with secrets configured in repository settings.
   - *Option B*: Direct execution on a secured, dedicated server/runner.
3. **Storage Retention Policy**:
   - Confirmation of required retention period for recovered video assets and database audit records in the UAT tier.

---

## 10. Invariant Confirmation

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
REC1-RUN1: BLOCKED / NOT AUTHORIZED

HISTORICAL_VIDU2_EXECUTION:
  TARGET_HISTORICAL_PROVIDER_JOB_ID: 995880130565918720
  PROVIDER_CREDITS_REPORTED: 30.0
  ACTUAL_CREDITS_CONSUMED: UNKNOWN / NOT CONFIRMED
  USD_EQUIVALENT: UNKNOWN / NOT CONVERTED
  RETAINED_RECOVERABLE_URL: NOT PROVEN
  DURABLE_VIDEO_ASSET: NOT PROVEN
```
