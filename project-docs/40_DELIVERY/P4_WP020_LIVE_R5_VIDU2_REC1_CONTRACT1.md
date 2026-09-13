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
REVIEW_ADDRESSED: Review 5190708464 (CHANGES REQUIRED) — All 5 findings resolved

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
1. **Persistent Cloud UAT Environment**: Decoupling persistence from ephemeral CI runners to guarantee data retention across worker restarts and runner teardowns.
2. **Bounded Recovery Harness**: A strictly single-purpose invocation harness reusing `ViduExistingJobRecoveryService` targeting historical job `995880130565918720`.
3. **Atomic One-Shot Approval Fence**: Guaranteeing that live provider GET is issued at most once (`GET <= 1`), backed by a dedicated standalone schema (`provider_execution_fences`) without foreign key dependencies on speculative recovery lineage.
4. **Durable Materialization & Compensation**: Ensuring transactional consistency between PostgreSQL lineage and object storage, defining unambiguous transaction ownership, crash reconciliation without re-GET, and safe compensation.
5. **Historical Audit & Billing Fence**: Idempotent tracking without claiming confirmed consumption or USD conversion, excluding historical recovery from live production ledgers and render queues.
6. **Comprehensive Acceptance Matrix**: 15 distinct failure/edge scenarios mapped to existing source models, proposed contracts, verification tests, required evidence, and STOP conditions.
7. **Multi-Gate Roadmap**: A strict sequential gate model restoring all required downstream acceptance work (audio, subtitles, QC, human approval, render variants, `.orbis` portability, cost reconciliation) prior to WP020 closure or Core V1 release.

**Scope of this Gate**: Strictly architectural specification and contract design. No code implementation, schema modification, cloud deployment, provider calls, or secret inspection are performed or authorized.

---

## 2. Persistent Cloud UAT Architecture (Decoupled from Production)

### 2.1 Environmental Boundaries & Stateless Compute
- **UAT vs Production Isolation**: The UAT environment must run in completely isolated database and object storage namespaces from any prospective production environment.
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
- **Rule**: Neither Hermes, ChatGPT, nor Antigravity may assume external cloud infrastructure is provisioned without explicit verified read-only connection evidence provided in a future dedicated infrastructure gate (Gate C).

### 2.4 Persistence, Backup/Restore & Worker-Replacement Retention Proofs
To definitively prove data durability and compute statelessness before any live probe is attempted:
1. **Worker Replacement / Container Restart Test**:
   - Write a deterministic preflight probe record to PostgreSQL and upload a synthetic probe object to object storage.
   - Forcefully terminate or recreate the runner container/process (simulating an ephemeral worker replacement).
   - Spawn a fresh, independent runner instance with clean local filesystem.
   - Execute a read-back query for the database record and an S3 GET request for the probe object.
   - Verify byte-for-byte SHA-256 checksum and metadata match.
2. **Backup & PITR Restore Proof**:
   - Verify automated snapshot or PITR point creation on the managed PostgreSQL instance.
   - Confirm object versioning or retention policy on the S3-compatible bucket.
3. **Infrastructure Cost Governance**:
   - Infrastructure hosting costs (PostgreSQL, storage egress/ingress) must be evaluated and approved under a separate infrastructure budget, distinct from the historical **USD $1.00 provider UAT budget**.
   - No account creation, subscription selection, credit card entry, or quota/billing adjustments are permitted in Gate A.

---

## 3. Recovery Harness Contract

### 3.1 Service Reuse & Target Bounding
- The recovery harness must directly invoke `ViduExistingJobRecoveryService.recover_existing_job()` in `backend/app/services/vidu_recovery.py`.
- **Target Provider Job ID**: Strictly bounded to hardcoded constant `TARGET_HISTORICAL_PROVIDER_JOB_ID = "995880130565918720"`.
- **Pre-Mutation Validation**:
  - The harness must invoke the classmethod `ViduExistingJobRecoveryService.validate_authorized_job_id(provider_job_id)` before initiating any network I/O, database writes, or storage operations.
  - Any parameter mismatch must raise `ViduUnauthorizedJobError` and immediately abort with exit code `1`.

### 3.2 Provider Status Consumption & Method Alignment
- **Normalized Status Consumption**:
  - `ViduExistingJobRecoveryService.recover_existing_job` consumes a normalized `ProviderJobResult` (from `backend/app/services/providers/base.py`).
  - The service checks for normalized status `job_result.status == "COMPLETED"` (or `JobStatus.COMPLETED`).
  - Raw provider responses (e.g. Vidu JSON payload `{"state": "success"}`) must be mapped by the provider adapter into normalized `JobStatus.COMPLETED`.
  - If the provider indicates failure, the adapter maps to `JobStatus.FAILED`, and the recovery service raises `ViduJobNotCompletedError` (or `ViduJobNotFoundError` for missing tasks).
- **Existing Service Exception Hierarchy** (`backend/app/services/vidu_recovery.py`):
  - Base: `ViduRecoveryError`
  - Subclasses:
    - `ViduUnauthorizedJobError`: Raised when job ID does not match authorized constant.
    - `ViduJobNotFoundError`: Raised when provider indicates task does not exist.
    - `ViduJobNotCompletedError`: Raised when provider status is not completed/success.
    - `ViduMissingOutputUrlError`: Raised when provider completed payload lacks video URL.
    - `ViduConflictingLineageError`: Raised when pre-existing database lineage has conflicting metadata.
  - *Note on Proposed Symbols*: `ViduInvalidMediaUrlError` is not an existing exception; URL validation failures in the current codebase raise `ViduRecoveryError(f"URL validation failed: {exc}")`.

### 3.3 Media Validation & Download Pipeline Alignment
- URL safety validation and streaming download do not reside on `ViduExistingJobRecoveryService` directly. They are delegated to `VideoMaterializationService` (`backend/app/services/video_materialization.py`):
  - `VideoMaterializationService._validate_public_https_url(url)`:
    - Resolves hostname to IP addresses via DNS.
    - Validates resolved IPs against private, loopback, link-local, multicast, and reserved ranges using Python `ipaddress` module.
    - Prevents Server-Side Request Forgery (SSRF) and DNS rebinding attacks.
    - Enforces HTTPS scheme (`https://`).
    - Prohibits redirects to non-public destinations.
  - `VideoMaterializationService._download_video_to_file(url, target_file_path)`:
    - Streams media over HTTPS into a local temporary file (`tempfile.NamedTemporaryFile`).
    - Calculates streaming SHA-256 checksum and exact file size in bytes.
    - Enforces maximum file size ceiling (`MAX_VIDEO_DOWNLOAD_BYTES`).
- Storage compensation:
  - Invokes `storage.delete_object(bucket, key)` on the configured `StorageProvider` (`backend/app/services/storage/base.py`, `mock.py`, `s3.py`).

### 3.4 Provider Call Limits (Transport & Application)
- **Generation POST Calls**: Strictly `0` (Zero). Calling `submit_generation_job` or any provider creation endpoint is completely prohibited.
- **Provider Status GET Calls**: Strictly `<= 1` across the entire recovery lifecycle for the execution identity, including all transport retries.
- **Zero Transport Retries**:
  - Automatic transport retries are capped at `0` (no retry).
  - If the single GET request fails, times out, or returns a network error, the harness must record the error, mark the fence as `CONSUMED_TERMINAL_FAILURE` or `CONSUMED_CRASHED`, and **STOP**.
- **No Polling Loops**: Polling loops are prohibited. If provider returns non-completed status, the harness halts immediately.
- **No Fallback Providers**: No fallback adapter (e.g., Mock, Gemini, ElevenLabs) may be invoked.

### 3.5 Mock Mode & Decoupled Verification
- The harness must provide a dry-run / mock mode:
  - Executes full validation of inputs, database models, savepoints, and deterministic ID calculation.
  - Operates without requiring live provider credentials (`VIDU_API_KEY`).
  - Never touches provider network endpoints.
- **No Generic API**: No public REST API route or generic Hermes tool integration may be introduced. The harness must be a tightly bounded, single-purpose CLI runner script.

---

## 4. Approval Fence & One-Shot Execution Contract

### 4.1 Four-Point Authorization Anchor & Freshness
Before any live network request to Vidu is initiated, the execution harness must verify an explicit, unbroken four-point authorization binding:
1. **Exact Git Commit SHA**: Must match the Owner-authorized commit on canonical `main` or authorized branch.
2. **Task ID**: Must match `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`.
3. **Provider Job ID**: Must strictly match `995880130565918720`.
4. **Runtime Target**: Must specify the exact verified persistent environment (e.g., `UAT-COMPOSE-PERSISTENT` or `UAT-CLOUD-STAGING`).
5. **Authorization Freshness & Authenticity**:
   - Authorization cannot be established merely by an unverified boolean environment variable (e.g. `OWNER_APPROVED=true`).
   - The authorization payload must be a structured token or signature containing:
     - `owner_auth_source`: Exact Telegram DM message ID or GitHub Issue #63 comment anchor.
     - `auth_timestamp`: ISO 8601 UTC timestamp within an authorized validity window (e.g. <= 2 hours).
     - `auth_scope`: Strictly `GET_ONLY_EXISTING_JOB_995880130565918720`.
   - Any missing, tampered, or expired authorization payload halts execution before connecting to the database or network.

### 4.2 Standalone Pre-GET Durable Fence Schema (`provider_execution_fences`)
- **Resolution of Architectural Dependency**:
  - Existing models `OrchestrationAudit` and `UsageLedger` enforce a non-null foreign key `project_id` pointing to the `projects` table. `UsageLedger.job_id`, when present, enforces a foreign key pointing to `generation_jobs`.
  - In a pre-GET state, no recovery `Project` or `GenerationJob` exists or is proven. Creating speculative recovery rows before issuing the provider GET would violate Section 5.2 and create "ghost recovery lineage" if the GET fails, task is not found, or media URL is missing.
  - Furthermore, `UsageLedger`'s partial unique index cannot fence `job_id = NULL`, and the deterministic ledger UUID (`orbis://vidu-recovery/ledger/...`) belongs to post-success historical billing evidence, not dispatch fencing.
- **Proposed Standalone Schema (Gate B Migration Revision `011`)**:
  - To provide an implementable, robust, and clean durable fence, Gate B will introduce a dedicated standalone table: `provider_execution_fences`.
  - **Schema Specification**:
    ```sql
    CREATE TABLE provider_execution_fences (
        fence_id UUID PRIMARY KEY,
        provider_name VARCHAR(64) NOT NULL DEFAULT 'vidu',
        provider_job_id VARCHAR(128) NOT NULL,
        execution_id VARCHAR(128) NOT NULL,
        task_id VARCHAR(128) NOT NULL,
        authorized_commit_sha VARCHAR(64) NOT NULL,
        runtime_target VARCHAR(64) NOT NULL,
        auth_signature TEXT NOT NULL,
        status VARCHAR(32) NOT NULL,
        network_get_attempts INTEGER NOT NULL DEFAULT 0,
        storage_intent_key VARCHAR(512) NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_provider_job_fence UNIQUE (provider_name, provider_job_id),
        CONSTRAINT chk_network_get_attempts CHECK (network_get_attempts <= 1)
    );
    ```
  - **State Lifecycle**:
    - `CLAIMED_PENDING_GET`: Fence claimed and committed prior to issuing HTTP GET.
    - `GET_IN_FLIGHT`: Network GET has been initiated.
    - `CONSUMED_SUCCESS`: Materialization, DB commit, and S3 read-back verified.
    - `CONSUMED_TERMINAL_FAILURE`: Provider returned 404, failed, or URL missing; no retry permitted.
    - `CONSUMED_CRASHED`: Process crashed or timed out during execution; manual reconciliation required.
  - **Zero Foreign Keys**: The fence table has zero foreign key dependencies on `projects`, `scenes`, `shots`, or `generation_jobs`.
  - **Transaction Boundary**: The fence record is inserted and committed in its OWN independent transaction prior to any outbound network GET. If this commit fails or detects a unique violation, execution halts immediately with 0 provider calls.
  - **Retention & Deletion Protection**: The fence table is an immutable audit log. Rows cannot be cascade-deleted. On failure, ONLY the fence record remains in the database; zero ghost recovery lineage is created.

### 4.3 Crash Windows & Failure Reconciliation Protocol
If the runner process terminates abnormally, state must be safely reconcilable based on the exact failure window:

| Failure Window | Point of Interruption | Fence State | Storage State | DB Lineage | Reconciliation Protocol on Next Run |
|---|---|---|---|---|---|
| **Window 1: Pre-GET** | Process dies after fence committed, before network call | `CLAIMED_PENDING_GET` (attempts = 0) | Clean | None | Provider audit confirmed 0 GET calls. Reset allowed ONLY with explicit Owner approval. |
| **Window 2: Mid-GET** | Network timeout / process killed during GET call | `GET_IN_FLIGHT` (attempts = 1) | Clean | None | **STOP**. Provider call count is consumed. Never issue another GET. Mark fence `CONSUMED_CRASHED`. |
| **Window 3: Post-GET, Pre-Storage** | Result received, process dies before S3 upload | `GET_IN_FLIGHT` | Clean (temp file wiped) | None | **STOP**. Result payload lost in ephemeral memory. Mark `CONSUMED_CRASHED`. Owner decision required. |
| **Window 4: Mid-Storage PUT** | S3 upload partially completed or times out | `GET_IN_FLIGHT` (`storage_intent_key` recorded) | Partial / Orphan S3 object | None | Inspect S3 for `storage_intent_key`. Execute compensation `delete_object`. Mark `CONSUMED_TERMINAL_FAILURE`. |
| **Window 5: Post-Storage, Pre-DB Commit** | File in S3, process dies before `db.commit()` | `GET_IN_FLIGHT` (`storage_intent_key` recorded) | Uploaded S3 object | Rolled back (none) | Independent DB query confirms no `Asset` references key. Execute compensation `delete_object`. Mark `CONSUMED_TERMINAL_FAILURE`. |
| **Window 6: Post-DB Commit, Pre-Fence Update** | Lineage committed, process dies before fence update | `GET_IN_FLIGHT` | Uploaded S3 object | Committed `Asset` | Independent query detects committed `Asset` and `GenerationJob`. Update fence to `CONSUMED_SUCCESS`. Do NOT delete storage! |
| **Window 7: Read-Back Verification Failure** | DB committed, fence updated, but S3 read-back fails | `CONSUMED_SUCCESS` | Uploaded S3 object | Committed `Asset` | Mark status `MATERIALIZED_UNVERIFIED_READBACK`. Lineage preserved for inspection. STOP for diagnosis. |

**Strict Rule**: In ALL crash windows where a GET was issued (Windows 2-7), automatic re-issuance of GET is strictly **PROHIBITED**.

---

## 5. Durable Materialization & Compensation Contract

### 5.1 Validation of Provider Result
- Prior to creating database records or downloading media:
  - Verify `job_result.provider_job_id == "995880130565918720"`.
  - Verify normalized `job_result.status == "COMPLETED"`.
  - Validate `job_result.video_url`:
    - Must be a non-empty string.
    - Must use HTTPS scheme (`https://`).
    - Must pass SSRF and DNS checks in `VideoMaterializationService._validate_public_https_url(url)`.
    - If URL is expired, invalid, private, or inaccessible, raise `ViduRecoveryError` and abort.

### 5.2 Transaction Ownership & Lineage Reconstruction
- **Transaction Ownership**:
  - The recovery service must own its dedicated database session (`Session(bind=engine)`), passing `commit=True` explicitly.
  - The Pre-GET Fence is committed in its own independent transaction.
  - Speculative lineage reconstruction is performed inside a managed savepoint (`db.begin_nested()`).
- **Lineage Components**:
  - `Project` (deterministic UUID via `uuid5(NAMESPACE_URL, f"orbis://vidu-recovery/project/{provider_job_id}")`, `budget_limit=None`)
  - `Scene` (scene_number: 1)
  - `Shot` (shot_number: 1, duration: 4.0s, visual_prompt preserved)
  - `GenerationJob` (status: `COMPLETED`, `imported_historical=True`, `execution_disabled=True`)
  - `Asset` (asset_type: `VIDEO`, content_type: `video/mp4`, storage_bucket, storage_key, checksum_sha256)
  - `UsageLedger` (cost_status: `UNKNOWN`, `imported_historical=True`, `actual_cost=None`, `estimated_cost=None`)
- **Atomic Rollback & Failure Audit**:
  - All DB entities must commit together atomically, or roll back cleanly.
  - If conflicting lineage already exists with mismatched attributes, fail closed with `ViduConflictingLineageError`.
  - Failure audit logging executes in a separate, autonomous committed transaction so that audit evidence survives lineage rollback.

### 5.3 Storage Compensation & Ambiguous Commit Handling
Because object storage operations (S3 PUT) and relational database transactions (SQL COMMIT) cannot participate in a two-phase commit:
1. **Durable Storage Intent**:
   - Before initiating S3 upload, the service records `storage_intent_key` on the fence record and commits it.
2. **Media Upload**:
   - Video is downloaded to local temp file, verified, and uploaded to S3 via `storage.upload_file_object()`.
3. **Caught Pre-Commit Failures**:
   - If an exception occurs before `db.commit()`, the savepoint rolls back DB changes.
   - The service executes compensation: `storage.delete_object(bucket, storage_key)` ONLY for newly created objects that are not referenced by any existing committed `Asset`.
4. **Ambiguous `db.commit()` Exception Handling**:
   - If `db.commit()` raises an exception (e.g. database connection timeout or network glitch during acknowledgment), the transaction outcome is AMBIGUOUS (the commit may have succeeded on the PostgreSQL server).
   - **Protocol**: The service must NOT immediately delete the S3 object!
   - Instead, open a fresh database connection and execute an independent query: `SELECT id FROM assets WHERE storage_key = :storage_key`.
   - If the `Asset` record exists, the commit actually succeeded! Mark as materialized, do NOT compensate/delete, and proceed to read-back verification.
   - If the `Asset` record does not exist, the commit failed and rolled back. Proceed with compensation `storage.delete_object(bucket, storage_key)`.
5. **Compensation Failure**:
   - If `storage.delete_object` fails (e.g. S3 connectivity issue), log a critical alert containing bucket and key to the failure audit table for offline garbage collection. Never mask the underlying database failure.

### 5.4 Post-Success Read-Back Verification
To definitively prove durable retention:
1. Commit database transaction.
2. Perform immediate independent read-back query from database to confirm records exist and match expected UUIDs.
3. Perform read-back head/get request from object storage to verify:
   - File exists in bucket.
   - Byte length matches recorded `Asset.file_size_bytes`.
   - Compute streaming SHA-256 of stored object and verify exact match with `Asset.checksum_sha256`.
4. Distinguish between:
   - `MATERIALIZED`: DB rows committed and S3 object uploaded.
   - `READ_BACK_VERIFIED`: Byte-for-byte read-back, checksum verification, and DB integrity confirmed.
5. **Role of Workflow Artifacts**:
   - GitHub Actions artifacts (`actions/upload-artifact@v4`) serve as secondary, diagnostic backups with bounded retention (default 90 days).
   - Artifacts do **not** substitute for operational, durable object storage assets.

---

## 6. Historical Audit & Billing Fence Contract

### 6.1 Historical Record Immutability & Worker Queue Isolation
- All recovered records must be explicitly marked:
  - `GenerationJob.imported_historical = True`
  - `GenerationJob.execution_disabled = True`
  - `UsageLedger.imported_historical = True`
  - `UsageLedger.cost_status = "UNKNOWN"`
  - `UsageLedger.actual_cost = None`
  - `UsageLedger.estimated_cost = None`
- **Worker & Queue Exclusions** (verified against repository source):
  - `backend/app/services/job_dispatch.py`: Filters `Job.execution_disabled.isnot(True)` (line 318) and excludes `job.imported_historical or job.execution_disabled` (line 517).
  - `backend/app/services/generation_worker.py`: Filters `GenerationJob.execution_disabled.isnot(True)` (line 22).
  - `backend/app/services/render_worker.py`: Explicitly ignores jobs with `getattr(job, "imported_historical", False) or getattr(job, "execution_disabled", False)` (line 63).
  - `backend/app/services/render_job.py`: Filters `RenderJob.execution_disabled.isnot(True)` (lines 243, 942).
  - `backend/app/services/subtitle_control.py`: Filters `RenderJob.execution_disabled.isnot(True)` (line 59).
  - `backend/app/services/archive/import_service.py`: Preserves bit-for-bit historical records tagged with `imported_historical=True` and `execution_disabled=True` (lines 7, 1406, 1443).

### 6.2 Truthful Credit & Cost Accounting
- **Provider Credits Accounting**:
  - In historical Run 1 (`34569728383`), Vidu reported `credits: 30.0` in sanitized telemetry.
  - Future GET response payload: May return `provider_credits` or may omit it.
    - If the future GET response returns `provider_credits`, record that value as `provider_credits_reported`.
    - If the future GET omits credits, retain the historical `30.0` as `provider_credits_reported`.
  - Actual consumed credits: **UNKNOWN / NOT CONFIRMED**.
  - USD equivalent: **UNKNOWN / NOT CONVERTED** (no arbitrary conversion to $0.00, $0.30, or synthetic pricing may be fabricated).
- **Budget Protection & Live Spend Definition**:
  - **Live Spend Addition $0.00**: Defined strictly as exclusion from live production usage ledger totals and zero new provider generation transactions (`new_generation_posts = 0`).
  - This does **not** constitute an empirical proof that Vidu's cloud billing account charges $0.00 for the HTTP GET request. That provider-side billing cost is `UNKNOWN / NOT CONVERTED`.
  - The historical recovery probe must not record synthetic spend that inflates or duplicates the historical **USD $1.00 UAT budget**.
- **Immutable Result Accounting Fields**:
  - `recovery_method = "GET_ONLY_EXISTING_JOB"`
  - `new_generation_posts = 0`
  - `provider_status = job_result.status or "COMPLETED"`
  - `actual_credits_consumed = "UNKNOWN / NOT CONFIRMED"`
  - `usd_equivalent = "UNKNOWN / NOT CONVERTED"`
  - `imported_historical = True`
  - `execution_disabled = True`

---

## 7. Comprehensive Acceptance Matrix (15 Scenarios)

The following matrix defines the exact verification scenarios, existing/proposed source models, verification tests, required evidence, and STOP conditions:

| # | Requirement Scenario | Existing / Proposed Model | Proposed Contract / Change | Verification Test | Required Evidence | STOP Condition |
|---|---|---|---|---|---|---|
| **1** | **Wrong Provider Job ID** | `backend/app/services/vidu_recovery.py` (`TARGET_HISTORICAL_PROVIDER_JOB_ID`) | Reject any ID other than `995880130565918720` before any I/O | Unit test calling `validate_authorized_job_id("111")` | `ViduUnauthorizedJobError` raised; 0 network/DB calls | Any non-matching job ID provided |
| **2** | **Missing / Tampered / Stale Owner Auth** | Control doc ruleset (`AGENTS.md`) & auth token validator | Require structured auth payload binding commit, task, job, runtime, and message anchor within 2h window | Preflight test with missing/stale/tampered auth payload | Harness exits with code 1; 0 DB/network calls | Auth payload missing, expired, or invalid |
| **3** | **Already Consumed / Active Fence** | `provider_execution_fences` (Gate B proposed schema) | Unique constraint `(provider_name, provider_job_id)` rejects duplicate claim | Concurrency test attempting 2 claims | Second caller receives `IntegrityError`; 0 GET calls | Fence record already exists |
| **4** | **Fence DB Insertion Failure** | `provider_execution_fences` / DB transaction | Fence commit fails (e.g. DB connection error); halt before GET | Simulated DB error on fence insert | Preflight raises DB exception; 0 GET calls issued | Fence cannot be durably committed |
| **5** | **Provider Task Gone / Not Found** | `ViduExistingJobRecoveryService.recover_existing_job` | Handle provider 404 / task not found; mark fence `CONSUMED_TERMINAL_FAILURE` | Mock provider returning 404 / `JobStatus.FAILED` | `ViduJobNotFoundError` raised; fence marked failed; 0 media written | Provider indicates task does not exist |
| **6** | **Provider Task Incomplete / In Progress** | `ViduExistingJobRecoveryService.recover_existing_job` | Consume normalized `job_result.status`; fail closed if not `COMPLETED` | Mock provider returning `processing` / `JobStatus.PENDING` | `ViduJobNotCompletedError` raised; 0 polling retries | Task not in completed state |
| **7** | **Missing / Unsafe / SSRF Media URL** | `VideoMaterializationService._validate_public_https_url` | Enforce HTTPS, DNS resolution, private/loopback IP block, redirect guard | Test with private IP (`10.0.0.1`), loopback, or non-HTTPS URL | `ViduRecoveryError` raised; DB savepoint rolled back; 0 download | URL invalid, private, insecure, or missing |
| **8** | **Video Download Failure / Network Error** | `VideoMaterializationService._download_video_to_file` | Stream download with size limit and SHA-256; catch network drops | Mock network disconnect mid-stream | Exception caught; temp file purged; DB rolled back; fence `CONSUMED_TERMINAL_FAILURE` | Download fails or integrity check fails |
| **9** | **S3 Storage Upload Failure** | `backend/app/services/storage/base.py` (`upload_file_object`) | Record `storage_intent_key`; if S3 PUT fails, rollback DB and purge temp file | Mock S3 PUT failure (500 / access denied) | Exception caught; DB rolled back; 0 orphan DB records | Storage upload fails |
| **10** | **Ambiguous DB Commit Exception** | Service transaction boundary (`db.commit()`) | If commit raises exception, independently query `Asset(storage_key)` before compensating S3 | Simulated DB commit exception with confirmed DB write | Independent query detects `Asset`; S3 object NOT deleted; marked for audit | Commit outcome ambiguous; halt for reconciliation |
| **11** | **Storage Compensation Failure** | `ViduExistingJobRecoveryService` (`storage.delete_object`) | If compensation `delete_object` fails, log critical orphan record to audit table | Mock S3 delete failure during DB rollback | Critical audit log recorded with bucket/key details; original error preserved | Compensation deletion fails (flagged for audit) |
| **12** | **Hard Process Crash Recovery** | Crash window protocol (Section 4.3) | Any crash in Windows 2-7 consumes fence; automatic re-GET is forbidden | Crash simulation after GET issued | Fence in `GET_IN_FLIGHT` or `CONSUMED_CRASHED`; subsequent run refuses GET | Process terminates unexpectedly |
| **13** | **Worker Replacement Persistence Proof** | Cloud PostgreSQL + S3 test suite | Teardown runner container, spawn fresh instance, verify read-back | Container recreation preflight test | Byte-for-byte SHA-256 and metadata match on fresh runner | Data loss upon runner restart |
| **14** | **Historical Worker Queue Fencing** | `backend/app/services/job_dispatch.py`, `render_worker.py` | Verify background workers ignore `execution_disabled=True` jobs | Queue dispatch test with recovered job | Job omitted from worker query results; 0 execution | Recovered job claimed by worker |
| **15** | **Post-Commit S3 Read-Back Failure** | Post-recovery read-back verification | Read back S3 object, compute SHA-256; distinguish `MATERIALIZED` from `READ_BACK_VERIFIED` | Mock S3 read-back corruption or 404 | Status set to `MATERIALIZED_UNVERIFIED_READBACK`; DB preserved; STOP for diagnosis | Read-back checksum mismatch |

---

## 8. Multi-Gate Execution Roadmap (Restoring Required Downstream Work)

Progress toward live recovery, downstream validation, and WP020 closure is strictly structured into sequential, independent gates. Successful recovery in Gate D is a recovery probe only—it does **not** constitute WP020 closure or Core V1 release readiness.

```text
[ Gate A: Contract & Architecture ]  <-- CURRENT ACTIVE GATE (P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1)
               │
               ▼  (Requires Owner Approval + Merge of Gate A PR)
[ Gate B: Harness & Standalone Schema Implementation ]
     - Migration revision 011: `provider_execution_fences`
     - Bounded CLI runner script (reusing ViduExistingJobRecoveryService)
     - Mocked unit & failure matrix tests (NO-PROVIDER, zero network calls)
               │
               ▼  (Requires Owner Approval + Merge of Gate B PR)
[ Gate C: Infrastructure & Persistence Verification ]
     - Verify persistent PostgreSQL and S3 connectivity
     - Worker replacement / container restart read-back proof
     - Zero provider calls (NO-PROVIDER)
               │
               ▼  (Requires Owner Explicit Live Execution Authorization)
[ Gate D: Bounded Live Recovery Probe ]
     - Task ID: P4-WP020-LIVE-R5-VIDU2-REC1-RUN1
     - Live GET <= 1 to exact job 995880130565918720
     - Materialize video asset, read-back proof, durable audit
               │
               ▼  (Requires Owner Acceptance of Live Evidence)
[ Gate E: REC1-RUN1 Post-Run Control Sync & Diagnostic Closure ]
     - DOCS-ONLY post-run synchronization of repository state
               │
               ▼  (Requires Owner Authorization)
[ Gate F: Downstream Assembly, Subtitles, Audio Integration & QC Gate ]
     - Task ID: P4-WP020-LIVE-R5-DOWNSTREAM1
     - Core V1 audio integration (AUDIO1 / live UAT)
     - Subtitle generation and export verification
     - QC evaluation and human final approval gate verification
     - Multi-output render pipeline variants
     - `.orbis` portable archive export/import with historical fencing
               │
               ▼  (Requires Owner Authorization)
[ Gate G: Cost & Ledger Final Reconciliation ]
     - Task ID: P4-WP020-LIVE-R5-COST-RECON1
     - Comprehensive accounting of all live UAT runs (R1 through R5)
     - Reconciliation against historical USD $1.00 budget ceiling
     - Confirmation of zero ongoing or runaway spend
               │
               ▼  (Requires Owner Authorization)
[ Gate H: WP020 Final Gate Review & Core V1 Release Candidate Review ]
     - Comprehensive verification against all 15 Core V1 release closure criteria
     - Full CI suite pass across all services
     - Formal ChatGPT Independent Final Review (PASS / READY FOR OWNER RELEASE DECISION)
     - Formal Owner release declaration and version tag
```

**Sequential Progression Rules**:
1. No gate may be started automatically upon completion of the previous gate.
2. Each gate requires a distinct feature branch, a dedicated PR, passing exact-head CI, ChatGPT independent review PASS, and explicit Owner merge/execution authorization.
3. If at any point the target task or media URL on Vidu is unavailable or expired, execution must **STOP**. No replacement generation may be initiated automatically.

---

## 9. Open Questions & Owner Decisions Needed

Before proceeding to **Gate B (Harness Implementation)** and **Gate C (Infrastructure Verification)**, the Owner's direction is requested on the following architectural items:

1. **Persistent Cloud Environment Target**:
   - *Option 1*: Dedicated cloud-hosted PostgreSQL and S3-compatible storage (e.g. AWS RDS/S3, Neon/Supabase/Cloudflare R2).
   - *Option 2*: Persistent Linux host / VM running Docker Compose with durable named host volumes (`postgres_data`, `minio_data`).
2. **Execution Runner Target for Live Probe**:
   - *Option A*: GitHub Actions workflow triggered via `workflow_dispatch` with secrets configured in repository settings.
   - *Option B*: Direct execution on a secured, dedicated server/runner.
3. **Handling of Expired Historical Video URL**:
   - If provider responds that the task was completed but the video download URL has expired and returns HTTP 403/404, confirm that the harness must mark the fence `CONSUMED_TERMINAL_FAILURE` and **STOP**, without any automatic generation retry (POST = 0).

---

## 10. Invariant Confirmation & No-Provider Execution Proof

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
