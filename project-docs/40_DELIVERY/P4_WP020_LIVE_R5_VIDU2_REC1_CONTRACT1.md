# P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 — Runtime & Recovery Contract

## Document Metadata

```text
PROJECT: Orbis Video Studio AI
REPOSITORY: rebootob/Orbis-Video-Studio-AI
GATE: P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 (Gate A — Runtime & Recovery Contract)
TYPE: DESIGN / DOCS-ONLY / NO-PROVIDER Specification
STATUS: COMPLETE / READY FOR CHATGPT INDEPENDENT RE-REVIEW
CANONICAL_BASE_MAIN_SHA: 0326def88915b25fbb4e2b7019753c2b3fedc0f7
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-rec1-contract1
OWNER_AUTHORIZATION: Direct chat session instruction (Gate A contract; no Issue #63 comment claimed)
REVIEWS_ADDRESSED:
  - Review 5190708464 (CHANGES REQUIRED) — All 5 initial findings resolved
  - Review 5190804562 (CHANGES REQUIRED) — All 4 remaining blockers resolved

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
1. **Persistent Cloud UAT Environment**: Decoupling persistence from ephemeral compute to guarantee data retention across worker restarts and runner teardowns, including isolated backup/restore and fence preservation proofs.
2. **Bounded Recovery Harness**: A strictly single-purpose invocation harness reusing `ViduExistingJobRecoveryService` targeting historical job `995880130565918720`.
3. **Atomic One-Shot Approval Fence**: A strict, consistent state machine backed by a dedicated standalone schema (`provider_execution_fences`) without foreign key dependencies on speculative recovery lineage, guaranteeing provider `GET <= 1`.
4. **Authoritative Transaction Outcome & Safe Storage Compensation**: Preventing premature or unverified media deletion during ambiguous commits, defining explicit service transaction boundaries, and logging failure/orphan records in an autonomous audit table (`recovery_failure_audits`).
5. **Trusted Cryptographic Authorization Verification**: Binding exact commit, task, job, runtime, and message anchor via HMAC-SHA256 / Ed25519 signatures and GitHub environment protections without raw secret persistence.
6. **Historical Audit & Billing Fence**: Idempotent tracking without claiming confirmed consumption or USD conversion, excluding historical recovery from live production ledgers, render workers, and `ProductionOrchestrator`.
7. **Comprehensive Acceptance Matrix**: 15 distinct failure/edge scenarios mapped to existing source models, proposed contracts, verification tests, required evidence, and STOP conditions.
8. **Multi-Gate Roadmap**: A strict sequential gate model restoring all required downstream acceptance work (audio, subtitles, QC, human approval, render variants, `.orbis` portability, cost reconciliation) prior to WP020 closure or Core V1 release.

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
To definitively prove data durability, compute statelessness, and fence preservation before any live probe is attempted:
1. **Worker Replacement / Container Restart Test**:
   - Write a deterministic preflight probe record to PostgreSQL and upload a synthetic probe object to object storage.
   - Forcefully terminate or recreate the runner container/process (simulating an ephemeral worker replacement).
   - Spawn a fresh, independent runner instance with clean local filesystem.
   - Execute a read-back query for the database record and an S3 GET request for the probe object.
   - Verify byte-for-byte SHA-256 checksum and metadata match.
2. **Isolated Backup & Restore Proof (Database & Storage)**:
   - Create a PostgreSQL database snapshot / PITR backup and an object storage snapshot.
   - Restore the snapshot into an isolated scratch database instance and isolated storage location.
   - Execute an automated verification suite against the restored database and storage:
     - Confirm all existing table rows, relationships, and constraints are preserved bit-for-bit.
     - Confirm object storage keys exist, file size matches, and streaming SHA-256 checksum matches recorded database `Asset.checksum_sha256`.
     - **Fence Preservation & Anti-Rollback Proof**: Verify that consumed fence records (`provider_execution_fences`) cannot be reverted, rolled back, or deleted in a manner that would reset `network_get_attempts` or permit another provider GET call. If an older backup is restored, fence reconciliation rules must detect that the provider job was already consumed and immediately fail closed.
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
  - `ProviderJobResult` lives in `backend/app/providers/base.py` (not `backend/app/services/providers/base.py`).
  - Its status is defined as `Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]` (it uses literal strings, not an enum or `PENDING` string).
  - `ViduExistingJobRecoveryService.recover_existing_job` consumes `job_result: ProviderJobResult`.
  - The service verifies `job_result.status == "COMPLETED"`.
  - Raw provider responses (e.g. Vidu JSON payload `{"state": "success"}`) are mapped by `ViduProviderAdapter` into normalized `job_result.status = "COMPLETED"`.
  - **Exception Mapping in `backend/app/services/vidu_recovery.py`**:
    - If `job_result.status == "FAILED"`:
      - If `provider_error_code in ("TASK_NOT_FOUND", "NOT_FOUND")` or `status_code == 404`: raises `ViduJobNotFoundError`.
      - Otherwise: raises `ViduRecoveryError(f"Provider task failed: {error}")`.
    - If `job_result.status != "COMPLETED"` (e.g. `"PROCESSING"`, `"QUEUED"`): raises `ViduJobNotCompletedError`.
    - If `not job_result.video_url`: raises `ViduMissingOutputUrlError`.
    - If lineage conflicts: raises `ViduConflictingLineageError`.

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
  - If the single GET request fails, times out, or returns a network error, the harness must record the error, transition the fence to `CONSUMED_CRASHED` or `CONSUMED_TERMINAL_FAILURE`, and **STOP**.
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

### 4.1 Trusted Cryptographic Authorization Verification
Before any live network request to Vidu is initiated, the execution harness must verify an authentic, unbroken, and cryptographically verifiable authorization binding:
1. **Trusted Authority & Signer**:
   - The sole authorized human authority is the Project Owner (`@rebootob`).
   - Third-party callers, automated agents, or unsigned environment variables cannot grant authorization.
2. **Verification Mechanism (No New Paid Auth Infrastructure)**:
   - **Layer 1: GitHub Environment Protection**: The execution workflow runs inside a dedicated GitHub Actions environment (`uat-vidu-recovery`) configured with required human approval restricted exclusively to `@rebootob`.
   - **Layer 2: Cryptographic Signature Verification**: The harness verifies an HMAC-SHA256 signature (or Ed25519 signature) against the repository secret `OWNER_AUTH_SIGNING_KEY`.
3. **Structured Authorization Payload**:
   ```json
   {
     "authorized_commit_sha": "0ad13a25d1a4cacd472805f11c820b50801f156b",
     "task_id": "P4-WP020-LIVE-R5-VIDU2-REC1-RUN1",
     "provider_job_id": "995880130565918720",
     "runtime_target": "UAT-COMPOSE-PERSISTENT",
     "issued_at": "2026-09-13T14:00:00Z",
     "expires_at": "2026-09-13T16:00:00Z",
     "nonce": "d290f1ee-6c54-4b01-90e6-d701748f0851"
   }
   ```
4. **Verification Procedure**:
   - **Signature Authenticity**: Recompute HMAC-SHA256 over canonicalized JSON payload; compare with provided signature using constant-time comparison.
   - **Freshness**: Verify `issued_at <= current_utc_time <= expires_at` (validity window strictly <= 2 hours).
   - **Exact SHA Binding**: Verify `authorized_commit_sha == git rev-parse HEAD`.
   - **Exact Job & Task Binding**: Verify `provider_job_id == "995880130565918720"` and `task_id == "P4-WP020-LIVE-R5-VIDU2-REC1-RUN1"`.
   - **Replay Protection**: Verify `nonce` does not exist in `provider_execution_fences.auth_nonce`.
5. **Safe Persistence**:
   - The raw secret and raw token are **never persisted**.
   - Only `auth_digest` (SHA-256 hash of payload), `auth_issued_at`, and `auth_nonce` are persisted on the fence record.
6. **Failure & Revocation**:
   - Any verification failure (signature invalid, expired, nonce reused, SHA mismatch) causes the harness to **STOP** immediately with exit code `1` before connecting to database or network.

### 4.2 Standalone Pre-GET Durable Fence Schema (`provider_execution_fences`)
- **Resolution of Architectural Dependency**:
  - Existing models `OrchestrationAudit` and `UsageLedger` enforce a non-null foreign key `project_id` pointing to `projects`. `UsageLedger.job_id`, when present, points to `generation_jobs`.
  - In a pre-GET state, no recovery `Project` or `GenerationJob` exists or is proven. Creating speculative recovery rows before issuing the provider GET would violate Section 5.2 and create "ghost recovery lineage" if the GET fails, task is not found, or media URL is missing.
  - Furthermore, `UsageLedger`'s partial unique index cannot fence `job_id = NULL`, and the deterministic ledger UUID (`orbis://vidu-recovery/ledger/...`) belongs to post-success historical billing evidence, not dispatch fencing.
- **Proposed Standalone Schema (Gate B Migration Revision `011`)**:
  - Gate B will introduce dedicated standalone table: `provider_execution_fences`:
    ```sql
    CREATE TABLE provider_execution_fences (
        fence_id UUID PRIMARY KEY,
        provider_name VARCHAR(64) NOT NULL DEFAULT 'vidu',
        provider_job_id VARCHAR(128) NOT NULL,
        execution_id VARCHAR(128) NOT NULL,
        task_id VARCHAR(128) NOT NULL,
        authorized_commit_sha VARCHAR(64) NOT NULL,
        runtime_target VARCHAR(64) NOT NULL,
        auth_digest VARCHAR(64) NOT NULL,
        auth_nonce VARCHAR(64) NOT NULL,
        auth_issued_at TIMESTAMPTZ NOT NULL,
        status VARCHAR(32) NOT NULL,
        network_get_attempts INTEGER NOT NULL DEFAULT 0,
        storage_intent_bucket VARCHAR(64) NULL,
        storage_intent_key VARCHAR(512) NULL,
        storage_intent_sha256 VARCHAR(64) NULL,
        storage_intent_bytes BIGINT NULL,
        storage_is_new_object BOOLEAN NULL,
        target_asset_id UUID NULL,
        target_job_id UUID NULL,
        target_project_id UUID NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_provider_job_fence UNIQUE (provider_name, provider_job_id),
        CONSTRAINT uq_auth_nonce UNIQUE (auth_nonce),
        CONSTRAINT chk_network_get_attempts CHECK (network_get_attempts <= 1)
    );
    ```
- **Consistent State Machine**:
  - `INITIAL_UNCLAIMED`: Unallocated initial state.
  - `CLAIMED_PENDING_GET`: Fence claimed and committed with `network_get_attempts = 0`. Default action on interruption: **STOP**. Any reset requires explicit Owner authorization.
  - `GET_IN_FLIGHT`: Atomic transition committing `status = 'GET_IN_FLIGHT'` and `network_get_attempts = 1` **prior** to outbound HTTP GET. Crash/timeout after this transition means fence is **CONSUMED**; no further GET permitted.
  - `MATERIALIZED_UNVERIFIED`: Lineage committed in PostgreSQL and S3 object uploaded, but post-commit read-back verification has not completed.
  - `CONSUMED_SUCCESS`: Reached **only** after independent DB lineage query + S3 byte length + streaming SHA-256 checksum match have been verified.
  - `CONSUMED_TERMINAL_FAILURE`: Terminal error (provider 404, failed, URL missing/unsafe, integrity check failure, or unrecoverable crash).
  - `CONSUMED_CRASHED`: Process crashed during or after `GET_IN_FLIGHT`.
- **Zero Foreign Keys**: No FK dependencies on `projects` or `generation_jobs`.
- **Transaction Boundary**: The fence record is inserted and committed in its OWN independent transaction prior to any outbound network GET. If this commit fails or detects a unique violation, execution halts immediately with 0 provider calls.

### 4.3 Crash Windows & Failure Reconciliation Protocol
If the runner process terminates abnormally, state must be safely reconcilable based on the exact failure window:

| Failure Window | Point of Interruption | Fence State | Storage State | DB Lineage | Reconciliation Protocol on Next Run |
|---|---|---|---|---|---|
| **Window 1: Pre-GET** | Process dies after fence committed, before network call | `CLAIMED_PENDING_GET` (attempts = 0) | Clean | None | **STOP by default**. Provider call count is 0. Any reset or reconciliation requires separate explicit Owner authorization, never an automatic retry. |
| **Window 2: Mid-GET** | Network timeout / process killed during GET call | `GET_IN_FLIGHT` (attempts = 1) | Clean | None | **STOP**. Provider call count is consumed. Never issue another GET. Mark fence `CONSUMED_CRASHED`. |
| **Window 3: Post-GET, Pre-Storage** | Result received, process dies before S3 upload | `GET_IN_FLIGHT` (attempts = 1) | Clean (temp file wiped) | None | **STOP**. Result payload lost in ephemeral memory. Mark `CONSUMED_CRASHED`. Owner decision required. |
| **Window 4: Mid-Storage PUT** | S3 upload partially completed or times out | `GET_IN_FLIGHT` (`storage_intent_key` recorded) | Partial / Orphan S3 object | None | Inspect S3 for `storage_intent_key`. Execute compensation `delete_object`. Mark `CONSUMED_TERMINAL_FAILURE`. |
| **Window 5: Post-Storage, Pre-DB Commit** | File in S3, process dies before `db.commit()` | `GET_IN_FLIGHT` (`storage_intent_key` recorded) | Uploaded S3 object | Rolled back (none) | Authoritative primary DB outcome check. If rollback confirmed, compensate S3. If ambiguous, STOP and retain object! |
| **Window 6: Post-DB Commit, Pre-Read-Back** | Lineage committed, process dies before read-back | `MATERIALIZED_UNVERIFIED` | Uploaded S3 object | Committed `Asset` | Independent query detects committed `Asset` and `GenerationJob`. Proceed to read-back verification. Do NOT re-GET! |
| **Window 7: Read-Back Verification Failure** | DB committed, but S3 read-back checksum fails | `MATERIALIZED_UNVERIFIED` | Uploaded S3 object | Committed `Asset` | Status set to `CONSUMED_TERMINAL_FAILURE` or remains `MATERIALIZED_UNVERIFIED` for diagnosis. DB and storage retained for analysis. |

**Strict Rule**: In ALL crash windows where `GET_IN_FLIGHT` was entered (Windows 2-7), automatic re-issuance of GET is strictly **PROHIBITED**.

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
  - Failure audit logging executes in a separate, autonomous committed transaction in `recovery_failure_audits` so that audit evidence survives lineage rollback.

### 5.3 Authoritative Transaction Outcome, Safe Storage Compensation & Future Service Refactor
Because object storage operations (S3 PUT) and relational database transactions (SQL COMMIT) cannot participate in a two-phase commit:
1. **Durable Storage Intent Recording**:
   - Before initiating S3 upload, the service records complete storage intent on the fence record and commits it:
     `storage_intent_bucket`, `storage_intent_key`, `storage_intent_sha256`, `storage_intent_bytes`, `storage_is_new_object = True`, and target lineage UUIDs (`target_asset_id`, `target_job_id`, `target_project_id`).
2. **Media Upload**:
   - Video is downloaded to local temp file, verified, and uploaded to S3 via `storage.upload_file_object()`.
3. **Necessary Service Refactor (Gate B Bounded Change)**:
   - In the existing codebase, `recover_existing_job(commit=True)` (`backend/app/services/vidu_recovery.py` lines 621-645) catches exceptions and immediately attempts `storage.delete_object` inside its internal `except` block *before* the caller can inspect or reconcile.
   - **Required Gate B Change**: Introduce a bounded modification to `ViduExistingJobRecoveryService` allowing the caller/runner to manage compensation (`auto_compensate_storage: bool = False`) or encapsulating the transaction boundary so compensation only executes when rollback is affirmatively confirmed on the primary DB connection.
4. **Authoritative Primary DB Transaction Outcome Resolution**:
   - An absent `Asset` query alone does NOT prove rollback (it could be caused by an in-flight unacknowledged server commit, replica lag, or transient network drop).
   - If `db.commit()` raises an exception:
     - The service must query the **authoritative primary database connection**.
     - It must check exact `(storage_bucket, storage_key)` AND validate complete deterministic lineage (`Project`, `Scene`, `Shot`, `GenerationJob`, `Asset`).
     - **Rule of Uncertainty**: If the primary DB transaction outcome is unavailable, uncertain, or unproven: **STOP and retain the S3 object; DO NOT delete**.
     - Only if the primary DB connection affirmatively confirms that the transaction rolled back and no `Asset` references the key, may compensation `storage.delete_object` proceed.
5. **Dedicated Failure & Orphan Audit Table (`recovery_failure_audits`)**:
   - Gate B will introduce `recovery_failure_audits`:
     ```sql
     CREATE TABLE recovery_failure_audits (
         audit_id UUID PRIMARY KEY,
         fence_id UUID REFERENCES provider_execution_fences(fence_id),
         provider_job_id VARCHAR(128) NOT NULL,
         failure_stage VARCHAR(64) NOT NULL,
         error_class VARCHAR(128) NOT NULL,
         error_message TEXT NOT NULL,
         orphan_storage_bucket VARCHAR(64) NULL,
         orphan_storage_key VARCHAR(512) NULL,
         db_transaction_state VARCHAR(64) NOT NULL,
         compensation_status VARCHAR(64) NOT NULL,
         created_at TIMESTAMPTZ NOT NULL
     );
     ```
   - Written and committed in an autonomous database transaction (`commit=True` on separate engine connection).

### 5.4 Post-Success Read-Back Verification & Completion Semantics
To definitively prove durable retention:
1. Commit database transaction. Fence state transitions to `MATERIALIZED_UNVERIFIED`.
2. Perform immediate independent read-back query from primary database to confirm records exist and match expected deterministic UUIDs.
3. Perform read-back head/get request from object storage to verify:
   - File exists in bucket.
   - Byte length matches recorded `Asset.file_size_bytes`.
   - Compute streaming SHA-256 of stored object and verify exact match with `Asset.checksum_sha256`.
4. Only upon 100% verification of both database lineage and storage read-back does the fence transition to `CONSUMED_SUCCESS`.
5. **Role of Workflow Artifacts**:
   - GitHub Actions artifacts (`actions/upload-artifact@v4`) serve as secondary, diagnostic backups with bounded retention (default 90 days).
   - Artifacts do **not** substitute for operational, durable object storage assets.

---

## 6. Historical Audit & Billing Fence Contract

### 6.1 Historical Record Immutability & Production/Worker Queue Isolation
- All recovered records must be explicitly marked:
  - `GenerationJob.imported_historical = True`
  - `GenerationJob.execution_disabled = True`
  - `UsageLedger.imported_historical = True`
  - `UsageLedger.cost_status = "UNKNOWN"`
  - `UsageLedger.actual_cost = None`
  - `UsageLedger.estimated_cost = None`
- **Worker, Queue & Production Orchestrator Exclusions** (verified against repository source):
  - `backend/app/services/job_dispatch.py`: Filters `Job.execution_disabled.isnot(True)` (line 318) and excludes `job.imported_historical or job.execution_disabled` (line 517).
  - `backend/app/services/generation_worker.py`: Filters `GenerationJob.execution_disabled.isnot(True)` (line 22).
  - `backend/app/services/render_worker.py`: Explicitly ignores jobs with `getattr(job, "imported_historical", False) or getattr(job, "execution_disabled", False)` (line 63).
  - `backend/app/services/render_job.py`: Filters `RenderJob.execution_disabled.isnot(True)` (lines 243, 942).
  - `backend/app/services/subtitle_control.py`: Filters `RenderJob.execution_disabled.isnot(True)` (line 59).
  - `backend/app/services/production_orchestrator.py`: Dispatches only non-historical, active production jobs. Excludes imported historical jobs from generation pipelines.
  - `backend/app/services/archive/import_service.py`: Preserves bit-for-bit historical records tagged with `imported_historical=True` and `execution_disabled=True` (lines 7, 1406, 1443).

### 6.2 Truthful Credit & Cost Accounting
- **Provider Credits Provenance vs Future GET Credits**:
  - In historical Run 1 (`34569728383`), Vidu reported `credits: 30.0` in sanitized workflow comments telemetry.
  - **Proposed Audit Behavior in Gate B**: In the existing service, `prior_credits` is only preserved if `existing_job.result` already contains it. On first recovery, `existing_job.result` is empty. Gate B must implement the proposed behavior: if future GET returns `provider_credits`, record it; if future GET omits credits, seed the historical `30.0` as `provider_credits_reported`.
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
| **2** | **Missing / Tampered / Stale Owner Auth** | HMAC-SHA256 / Ed25519 validator; GitHub env protection | Require cryptographically verifiable payload binding commit, task, job, runtime, and message anchor within 2h window | Preflight test with missing/stale/tampered auth payload | Harness exits with code 1; 0 DB/network calls | Auth payload missing, expired, or invalid |
| **3** | **Already Consumed / Active Fence** | `provider_execution_fences` (Gate B proposed schema) | Unique constraint `(provider_name, provider_job_id)` rejects duplicate claim | Concurrency test attempting 2 claims | Second caller receives `IntegrityError`; 0 GET calls | Fence record already exists |
| **4** | **Fence DB Insertion Failure** | `provider_execution_fences` / DB transaction | Fence commit fails (e.g. DB connection error); halt before GET | Simulated DB error on fence insert | Preflight raises DB exception; 0 GET calls issued | Fence cannot be durably committed |
| **5** | **Provider Task Gone / Not Found** | `backend/app/providers/base.py` (`ProviderJobResult`), `vidu_recovery.py` | Handle provider 404 / `TASK_NOT_FOUND`; mark fence `CONSUMED_TERMINAL_FAILURE` | Mock provider returning 404 / `status = "FAILED"` | `ViduJobNotFoundError` raised; fence marked failed; 0 media written | Provider indicates task does not exist |
| **6** | **Provider Task Incomplete / In Progress** | `backend/app/providers/base.py`, `vidu_recovery.py` | Consume normalized `job_result.status`; fail closed if not `"COMPLETED"` | Mock provider returning `"PROCESSING"` / `"QUEUED"` | `ViduJobNotCompletedError` raised; 0 polling retries | Task not in completed state |
| **7** | **Missing / Unsafe / SSRF Media URL** | `VideoMaterializationService._validate_public_https_url` | Enforce HTTPS, DNS resolution, private/loopback IP block, redirect guard | Test with private IP (`10.0.0.1`), loopback, or non-HTTPS URL | `ViduRecoveryError` raised; DB savepoint rolled back; 0 download | URL invalid, private, insecure, or missing |
| **8** | **Video Download Failure / Network Error** | `VideoMaterializationService._download_video_to_file` | Stream download with size limit and SHA-256; catch network drops | Mock network disconnect mid-stream | Exception caught; temp file purged; DB rolled back; fence `CONSUMED_TERMINAL_FAILURE` | Download fails or integrity check fails |
| **9** | **S3 Storage Upload Failure** | `backend/app/services/storage/base.py` (`upload_file_object`) | Record `storage_intent_key`; if S3 PUT fails, rollback DB and purge temp file | Mock S3 PUT failure (500 / access denied) | Exception caught; DB rolled back; 0 orphan DB records | Storage upload fails |
| **10** | **Ambiguous DB Commit Exception** | Service transaction boundary (`db.commit()`) | Authoritative primary DB query before compensating S3; if outcome uncertain, STOP and retain S3 object | Simulated DB commit exception with confirmed DB write | Primary DB query detects `Asset`; S3 object NOT deleted; marked for audit | Commit outcome ambiguous; halt for reconciliation |
| **11** | **Storage Compensation Failure** | `ViduExistingJobRecoveryService`, `recovery_failure_audits` | If compensation `delete_object` fails, log critical orphan record to audit table | Mock S3 delete failure during DB rollback | Critical audit log recorded with bucket/key details; original error preserved | Compensation deletion fails (flagged for audit) |
| **12** | **Hard Process Crash Recovery** | Crash window protocol (Section 4.3) | Any crash in Windows 2-7 consumes fence; automatic re-GET is forbidden | Crash simulation after GET issued | Fence in `GET_IN_FLIGHT` or `CONSUMED_CRASHED`; subsequent run refuses GET | Process terminates unexpectedly |
| **13** | **Worker Replacement & Restore Persistence Proof** | Cloud PostgreSQL + S3 test suite | Teardown runner container; restore DB/S3 from snapshot; verify read-back & fence preservation | Container recreation & snapshot restoration test | Byte-for-byte SHA-256 and metadata match; fence cannot be rolled back | Data loss or fence reset upon restore/restart |
| **14** | **Historical Production & Queue Fencing** | `backend/app/services/job_dispatch.py`, `render_worker.py`, `production_orchestrator.py` | Verify background workers and orchestrators ignore `execution_disabled=True` jobs | Queue dispatch & production orchestrator test | Job omitted from worker query results; 0 execution | Recovered job claimed by worker/orchestrator |
| **15** | **Post-Commit S3 Read-Back Failure** | Post-recovery read-back verification | Read back S3 object, compute SHA-256; transition to SUCCESS only upon match | Mock S3 read-back corruption or 404 | Status remains `MATERIALIZED_UNVERIFIED` / marked terminal; DB preserved; STOP | Read-back checksum mismatch |

---

## 8. Multi-Gate Execution Roadmap (Restoring Required Downstream Work)

Progress toward live recovery, downstream validation, and WP020 closure is strictly structured into sequential, independent gates. Successful recovery in Gate D is a recovery probe only—it does **not** constitute WP020 closure or Core V1 release readiness.

```text
[ Gate A: Contract & Architecture ]  <-- CURRENT ACTIVE GATE (P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1)
               │
               ▼  (Requires Owner Approval + Merge of Gate A PR)
[ Gate B: Harness & Standalone Schema Implementation ]
     - Migration revision 011: `provider_execution_fences` & `recovery_failure_audits`
     - Bounded CLI runner script (reusing ViduExistingJobRecoveryService with auto_compensate_storage option)
     - Mocked unit & failure matrix tests (NO-PROVIDER, zero network calls)
               │
               ▼  (Requires Owner Approval + Merge of Gate B PR)
[ Gate C: Infrastructure & Persistence Verification ]
     - Verify persistent PostgreSQL and S3 connectivity
     - Worker replacement / container restart read-back proof
     - Isolated snapshot backup & restore verification
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
