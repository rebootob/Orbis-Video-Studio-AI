# P4-WP020-LIVE-R5-VIDU2-REC1-GATED-AUTH-DESIGN1

> **Mode:** DOCS-ONLY / DESIGN / NO EXECUTION
>
> **Canonical source baseline:** `main@ae1f7ba7649afda2773a15d6587e81e61a94887e`
>
> **Owner authorization:** EXPLICIT OWNER APPROVAL IN CHAT (Claude control session, 2026-10-05; not Issue #63)
>
> **Status:** IN PROGRESS / DOCS-ONLY / WAITING FOR REVIEW

---

## A. Purpose & Scope

This package defines prerequisites and proposed design decisions for Gate D, `P4-WP020-LIVE-R5-VIDU2-REC1-RUN1`. It does **not** execute REC1-RUN1, create authorization artifacts, create or install keys, configure deployment files, configure the external execution register, connect to PostgreSQL/S3/Vidu, deploy, release, or close WP020.

All design decisions in Section C remain **PROPOSED** until accepted by the Owner through merge authorization. Completion or merge of this design package does not authorize packages 2–4 and does not authorize any provider request.

---

## B. Source Facts from `main@ae1f7ba7649afda2773a15d6587e81e61a94887e`

### B.1 Canonical Payload and Signature

| Fact | Source |
|---|---|
| `CanonicalAuthPayload` has 9 required fields: `authorized_commit_sha`, `task_id`, `provider_job_id`, `runtime_target`, `owner_evidence_anchor`, `issued_at`, `expires_at`, `auth_nonce`, `restore_epoch`. | `backend/app/services/recovery_auth.py:662-671` |
| Canonical JSON explicitly emits all 9 fields; JSON keys are sorted; separators are `(",", ":")`; output is UTF-8 bytes. | `backend/app/services/recovery_auth.py:673-686` |
| Datetimes are normalized through `astimezone(timezone.utc).isoformat()`. | `backend/app/services/recovery_auth.py:678-679` |
| Payload maximum validity window is `7200` seconds. | `backend/app/services/recovery_auth.py:30,1197-1211` |
| `ed25519_verify()` implements RFC 8032 verification; public key is 32 bytes and signature is 64 bytes (`R || S`). | `backend/app/services/ed25519_pure.py:1-9,93-105` |
| CLI parses `--signature` with `bytes.fromhex()` and production `OWNER_AUTH_PUBLIC_KEY` with `bytes.fromhex()`. | `backend/app/cli/vidu_recovery_harness.py:615,647,657-666` |
| A deployment signing public key file is UTF-8 hex decoded and must be exactly 32 bytes. | `backend/app/services/recovery_auth.py:181-186` |
| Nonce replay is rejected against `provider_execution_fences`; `auth_nonce` is unique in migration revision 022. | `backend/app/services/recovery_auth.py:1378-1388`; `backend/migrations/versions/022_provider_execution_fences_and_audits.py:45` |
| Payload commit SHA is compared with independently resolved executing artifact SHA. Resolution order is `EXECUTING_COMMIT_SHA`, `git rev-parse HEAD`, then `settings.GIT_COMMIT_SHA`. | `backend/app/cli/vidu_recovery_harness.py:668-685`; `backend/app/services/recovery_auth.py:1213-1217` |

### B.2 Authorization Phases and Pre-GET Controls

Phase 1 is in-memory signature/scope verification (`backend/app/services/recovery_auth.py:1170-1244`). Phase 2 is `verify_phase_2_and_claim_fence()` (`backend/app/services/recovery_auth.py:1247-1522`) and, before the first provider GET, verifies:

1. `VIDU_GENERATION_ENABLED` is false and `VIDU_RECOVERY_GET_ENABLED` is true (`:1272-1285`).
2. `owner_evidence_anchor` matches `^(telegram|issue|pr|evidence|rec1|r5|run1)[\w\-\.\/:]+$` (`:1287-1291`).
3. A signed authoritative deployment record exists (`:1293-1297`).
4. Payload runtime target equals actual and deployment-attested target, and exists in `AUTHORIZED_RUNTIME_TARGET_PROFILES` (`:1299-1318`).
5. Actual DB and storage identities are independently resolved and match the selected profile (`:1320-1330`).
6. Physical topology probes return canonical DB/storage identities attested by `db_topology.expected_identities` and `storage_topology.expected_identities` (`:1332-1360`).
7. Revocation evidence is present; nonce/anchor are not revoked (`:1362-1376`).
8. Nonce replay and same-job fences are absent (`:1378-1402`).
9. Out-of-band consumed evidence does not list the provider job (`:1404-1415`).
10. The deterministic historical `GenerationJob` does not already exist without a fence (`:1417-1425`).
11. The signed restore epoch equals the independently sourced runtime epoch (`:1427-1432`).
12. The external execution register confirms the job/nonce have not already been dispatched or consumed (`:1434-1442`).
13. Storage contains no in-flight/consumed/asset marker proving prior dispatch or recovery (`:1444-1490`).
14. Only after all checks pass, the service inserts and commits a fence with `status="CLAIMED_PENDING_GET"`, `network_get_attempts=0` (`:1492-1522`).

### B.3 Authorized Runtime Identities

`AUTHORIZED_RUNTIME_TARGET_PROFILES` (`backend/app/services/recovery_auth.py:33-92`) includes:

```text
UAT-COMPOSE-PERSISTENT.trusted_db_identities:
- sqlite://:memory:
- sqlite:///
- sqlite://
- postgresql+psycopg://localhost:5432/orbis_studio
- postgresql+psycopg://127.0.0.1:5432/orbis_studio
- postgresql+psycopg://postgres:5432/orbis_studio
- postgresql://localhost:5432/orbis_studio
- postgresql://127.0.0.1:5432/orbis_studio
- postgresql://postgres:5432/orbis_studio

UAT-COMPOSE-PERSISTENT.trusted_storage_identities:
- mock://local/orbis-media-assets
- mock://local/orbis-assets
- mock://local/test-bucket
- s3://http://localhost:9000/orbis-media-assets
- s3://http://localhost:9000/orbis-assets
- s3://http://127.0.0.1:9000/orbis-media-assets
- s3://http://127.0.0.1:9000/orbis-assets
- s3://http://minio:9000/orbis-media-assets
- s3://http://minio:9000/orbis-assets
- s3://localhost:9000/orbis-media-assets
- s3://localhost:9000/orbis-assets
- s3://127.0.0.1:9000/orbis-media-assets
- s3://127.0.0.1:9000/orbis-assets
- s3://minio:9000/orbis-media-assets
- s3://minio:9000/orbis-assets
```

The local compose application container uses PostgreSQL `postgres:5432/orbis_studio` and MinIO `http://minio:9000/orbis-assets` (`docker-compose.yml:54-62`), both represented in the profile. Gate C evidence records the same application-internal MinIO and database identities (`P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_LOCALPC_BIND1.md:47,50,61`).

**Recorded discrepancy:** PR #122 states that local PostgreSQL is host-bound at `127.0.0.1:5434:5432`, and `docker-compose.yml:10-11` confirms that host mapping. `git grep 5434 -- '*.py'` at this baseline returns no match, while the recovery profile only lists PostgreSQL port `5432` (`recovery_auth.py:39-44`). Therefore host execution via `127.0.0.1:5434` is not an allowed identity even though in-container `postgres:5432` is.

### B.4 Signed Deployment Record

The deployment record is JSON at the first existing fixed path (`backend/app/services/recovery_auth.py:95-100,355-369`):

- `/etc/orbis/deployment.json`
- `/var/run/orbis/deployment.json`
- `/opt/orbis/deployment.json`

Its deployment public key is loaded from fixed paths including `/etc/orbis/deployment-signing.pub`, `/var/run/orbis/deployment-signing.pub`, or `/opt/orbis/deployment-signing.pub`; caller-controlled key environment values are explicitly not trusted (`recovery_auth.py:115-130`). The JSON must be UTF-8, include an `attestation` object with `attested=true`, a hex `signature`, `runtime_target`, non-empty `db_topology.expected_identities`, and non-empty `storage_topology.expected_identities`; the signature covers the canonical JSON without `signature` (`recovery_auth.py:304-352`).

On POSIX, file and directory hierarchy security is fail-closed: root UID/GID 0 ownership, no symlinks, no group/world-writable file or hierarchy components, and regular files only (`recovery_auth.py:123-188,193-294`).

### B.5 Authoritative External Execution Register

The register (`recovery_auth.py:693-1148`) is durable authority outside DB/S3 restore sets. For `UAT-COMPOSE-PERSISTENT`, its path must exactly match one of (`:65-72,766-800`):

- `/var/run/orbis/external_execution_register.json`
- `/opt/orbis/register/authoritative_register.json`

Its path comes from `EXTERNAL_EXECUTION_REGISTER_PATH`. Both `EXTERNAL_EXECUTION_REGISTER_TOPOLOGY_ATTESTED=true` and `EXTERNAL_EXECUTION_REGISTER_ATTESTED=true` are mandatory (`:701-709,746-762`). Profile policy requires a distinct mount and directory fsync; this cannot be downgraded by environment (`:712-739,851-879`). Register JSON has `dispatched_jobs`, `dispatched_nonces`, `consumed_jobs`, and `consumed_nonces` (`:881-885`).

Before GET, the harness calls `claim_pre_get_dispatch()` (`backend/app/cli/vidu_recovery_harness.py:227-237`). Failures after the fence is claimed transition it to `CONSUMED_TERMINAL_FAILURE` (`:243,397,455,511`) and are intentionally fail-closed.

### B.6 Complete Auth-Path Environment Contract

| Environment name | Purpose | Accepted form | Authority to set/attest | Source |
|---|---|---|---|---|
| `OWNER_AUTH_PUBLIC_KEY` | Owner authorization verifier | 64 hex chars decoding to 32 bytes | Owner/deployment operator installs public value | harness `:657-666` |
| `CURRENT_RESTORE_EPOCH` | Current signed runtime baseline identity | non-empty string matching payload | Owner attests for the run | auth `:1152-1167` |
| `RESTORE_EPOCH_ATTESTED` | Freshness assertion for epoch | literal `true` | Owner | auth `:1157-1165` |
| `EXECUTING_COMMIT_SHA` | Executing artifact commit | full commit SHA; otherwise independent fallback | deployment operator | harness `:668-685` |
| `VIDU_RECOVERY_GET_ENABLED` | Permits bounded existing-job GET | `true` or `1` | Owner-gated runtime operator | auth `:1281-1285` |
| `VIDU_GENERATION_ENABLED` | Must disable generation | false/unset; never true/1 | deployment operator | auth `:1272-1279` |
| `OWNER_AUTH_REVOCATIONS` | Revoked nonces/anchors | comma-separated values; may be empty only with attestation | Owner | auth `:1362-1376` |
| `OWNER_AUTH_REVOCATIONS_ATTESTED` | Attests an empty revocation registry | literal `true` | Owner | auth `:1366-1371` |
| `OUT_OF_BAND_CONSUMED_EVIDENCE` | Previously consumed job IDs | comma-separated IDs | Owner/deployment operator | auth `:1404-1415` |
| `OUT_OF_BAND_CONSUMED_ATTESTED` | Attests non-empty consumed evidence | literal `true` | Owner/deployment operator | auth `:1407-1409` |
| `EXTERNAL_EXECUTION_REGISTER_PATH` | Durable external register path | exact profile-allowed path | deployment operator | auth `:701-709` |
| `EXTERNAL_EXECUTION_REGISTER_TOPOLOGY_ATTESTED` | Attests separate topology | literal `true` | infrastructure operator after proof | auth `:746-762` |
| `EXTERNAL_EXECUTION_REGISTER_ATTESTED` | Attests register freshness | literal `true` | infrastructure operator after proof | auth `:746-762` |
| `DIRECTORY_FSYNC_SUPPORTED` | Positive capability proof | true/1/yes; cannot downgrade required policy | infrastructure operator | auth `:712-739` |
| `TRUSTED_EXTERNAL_REGISTER_PATH` | Optional exact trusted path corroboration | exact profile path | deployment operator | auth `:773,791-800` |
| `TRUSTED_EXTERNAL_REGISTER_DIR` | Optional trusted directory; not sufficient alone for live path mismatch | trusted directory | deployment operator | auth `:774,786-821` |
| `EXTERNAL_REGISTER_REQUIRE_DISTINCT_MOUNT` | Can strengthen but not weaken distinct-mount policy | true/1/yes; false/0/no rejected when profile requires it | infrastructure operator | auth `:851-860` |
| `DEPLOYED_RUNTIME_TARGET` | Caller consistency assertion only | if set, must equal deployment-owned target | deployment operator | auth `:401-406` |
| `STORAGE_RESTORE_ROOT` | Canonical local storage restore root discovery | absolute/canonical path | infrastructure operator | auth `:411-441` |
| `LOCAL_STORAGE_DIR` | Fallback local storage root | absolute/canonical path | infrastructure operator | auth `:423-426` |
| `STORAGE_BUCKET_DIR` | Storage restore root discovery | absolute/canonical path | infrastructure operator | auth `:427-429` |
| `OBJECT_STORAGE_BUCKET_DIR` | Storage restore root discovery fallback | absolute/canonical path | infrastructure operator | auth `:427-429` |

No attestation flag may be set to true by an execution agent without the corresponding Owner/infrastructure proof described below.

---

## C. Proposed Design Decisions (Owner Decision Required at Merge)

### D-A. Runtime — PROPOSED

Run the future Gate D harness inside the Linux `orbis_backend` container as root, using `postgres:5432/orbis_studio` and `minio:9000/orbis-assets`, because those identities match `UAT-COMPOSE-PERSISTENT`. Do not support direct Windows-host execution: host DB identity `127.0.0.1:5434` is absent from the profile and mandatory directory-fsync policy fails closed on non-POSIX platforms unless positively provided (`recovery_auth.py:726-739`).

Set `EXECUTING_COMMIT_SHA` explicitly to the frozen canonical `main` SHA at run time because git metadata inside the container is **NOT PROVEN** to exist. Package 3 must prove this without provider calls.

### D-B. Keys — PROPOSED

The Owner creates two separate Ed25519 keypairs outside every agent/runtime machine and stores both private keys exclusively in the Owner's password manager. Private keys must never enter this repo, environment variables, agent host, deployment image, logs, or reports. Only public keys are non-secret:

```text
OWNER AUTHORIZATION PUBLIC KEY (32-byte hex):
c33a616bad36e8a21a3af019f52d37d88db72d68b1d547600a11d38fdfeac48a
SHA-256 (decoded public-key bytes):
3e6e428d77599bd48482a12cf1014895d31a4c2e5139a744c1b028d5e315f1ac

DEPLOYMENT SIGNING PUBLIC KEY (32-byte hex):
c9ea3c6e155a7939ca1fcd54d836e0f239bdc1e71d1014c7ffa9ed0d77812b96
SHA-256 (decoded public-key bytes):
bc619de5ed3bb1e2d7ac8f43f5d816c4fe07117fdc9afe544e54ac42354e473a
```

Rotation policy: if a private key is lost or suspected exposed, STOP Gate D, revoke the affected key, create a replacement pair on the Owner's secure device, replace only the trusted public-key deployment, recreate and re-sign every artifact bound to the old key, and repeat package 3 preflight. Lost authorization key means issue a fresh payload/nonce; lost deployment key means re-sign the deployment record. Never reuse an uncertain key.

### D-C. Container File Placement — PROPOSED OPTIONS

| Option | Security fit | Risks / decision |
|---|---|---|
| Dedicated named volume(s) mounted at fixed profile paths | Can be initialized root-owned in Linux; can isolate register from DB/S3 volumes | Must prove actual `st_dev` differs from DB/storage and survive container replacement. Candidate preferred. |
| Baked image files | Can enforce root ownership/mode for immutable deployment record/public key | Inappropriate for mutable external register; key rotation requires image rebuild. Use only for immutable public artifacts if package 3 proves it. |
| WSL2 native Linux filesystem bind mount | May preserve Linux UID/GID/mode and permit separate mount design | Requires explicit mount/device proof. Candidate alternative. |
| Windows-host bind mount via Docker Desktop | **NOT PROVEN** | Often presents permissions broader/different than the POSIX checks require; must not be selected unless package 3 proves root UID/GID, safe mode, no symlink, distinct mount, and directory fsync without weakening code. |

No option may reduce or bypass repository security checks.

### D-D. Restore Epoch — PROPOSED

Proposed format:

```text
RESTORE-EPOCH-<YYYYMMDD>-<first 12 lowercase hexadecimal characters of SHA-256 of the canonical DB backup file recorded by BACKUP-RESTORE1>
```

`P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_LOCALPC_BACKUP_RESTORE1.md` does not document the DB backup SHA-256: **NOT DOCUMENTED**. Package 3 must either recover the already-recorded backup hash from trusted external evidence without altering/restoring data, or propose a new Owner-attested epoch source for explicit decision. It must not invent the value.

Only the Owner sets `CURRENT_RESTORE_EPOCH` and `RESTORE_EPOCH_ATTESTED=true` in the future run process environment after verifying the baseline. Neither value is committed.

### D-E. Attestation Ownership — PROPOSED

| Flag | Who may attest | Required proof before setting true |
|---|---|---|
| `RESTORE_EPOCH_ATTESTED` | Owner | Epoch derived from the accepted canonical backup baseline and matches signed payload. |
| `OWNER_AUTH_REVOCATIONS_ATTESTED` | Owner | Current revocation source checked; an empty list is intentional and fresh. |
| `OUT_OF_BAND_CONSUMED_ATTESTED` | Owner | Issue/run/storage history checked for prior job consumption. |
| `EXTERNAL_EXECUTION_REGISTER_TOPOLOGY_ATTESTED` | Infrastructure operator, accepted by Owner | Exact allowlisted path, trusted ownership/modes, no symlink, separate restore set and distinct mount proven. |
| `EXTERNAL_EXECUTION_REGISTER_ATTESTED` | Infrastructure operator, accepted by Owner | Register read successfully; dispatched/consumed state reconciled and current. |
| `DIRECTORY_FSYNC_SUPPORTED` | Infrastructure operator, accepted by Owner | Positive POSIX directory fsync proof on the selected register filesystem. |

Execution agents may report proofs but must not self-attest these flags.

### D-F. Commit Binding — PROPOSED

The authorization payload binds to canonical `main` at run time. Any main merge changes the SHA and requires a newly generated payload and Owner signature. Gate D runs only after packages 2 and 3 merge and canonical main is explicitly frozen for this run. The Gate D evidence PR is created **after** the run; it must not change main before execution.

### D-G. One-Shot State and Accepted Risks — PROPOSED

| Point/failure | Fence/register state | Consequence |
|---|---|---|
| Before Phase 2 claim | no fence; register unclaimed | No provider action. Fresh corrected payload may be retried. |
| Phase 2 committed | `CLAIMED_PENDING_GET`, `network_get_attempts=0` | Same-job fence already blocks another claim. |
| External dispatch claim succeeds | register job+nonce marked dispatched; pre-GET marker written | One-shot is consumed for safety before GET. |
| Process dies after DB commit but before external claim | DB fence remains `CLAIMED_PENDING_GET` | Same-job check blocks rerun; no automated reset path is documented. |
| External claim/marker/pre-GET transition fails | `CONSUMED_TERMINAL_FAILURE` | Job is permanently fail-closed. |
| Network fails or URL is expired after claim | terminal failure and durable audit | No retry and no generation POST. |
| Successful GET/materialization | consumed/success lineage and audit | Gate E still requires separate authorization. |

No reset/unlock workflow is present in the inspected source or contract: **NOT PROVEN / NO DOCUMENTED RESET PATH**. This preserves Owner-accepted D1–D4: status GET <=1, media download <=1, no retry/POST, fence consumed even for expired URL, pre-run canonical backup only, and GET cost unknown pending Gate G.

### D-H. Gate D Payload Specification — PROPOSED

```text
task_id = P4-WP020-LIVE-R5-VIDU2-REC1-RUN1
provider_job_id = 995880130565918720
runtime_target = UAT-COMPOSE-PERSISTENT
owner_evidence_anchor = issue:63:comment:<Owner authorization comment id>
validity = recommended <= 30 minutes; hard maximum 7200 seconds
nonce = UUID4
restore_epoch = D-D value accepted by Owner
issued_at / expires_at = timezone-aware ISO-8601 using +00:00, matching code canonicalization
```

The anchor must identify an actual Owner authorization comment on Issue #63 and match the Phase 2 regex.

### D-I. Next Packages — PROPOSED / NOT AUTHORIZED

| Package | Start condition | Pass criteria |
|---|---|---|
| Package 2 — Signing and non-consuming preflight tooling | Separate Owner authorization after this design PR is independently reviewed and merged | A bounded tool generates payload/deployment-record bytes using the same canonicalization; supports Phase 1–2 validation without claiming a fence or calling a provider; source/tests are independently reviewed. This necessarily requires separately authorized source/test changes. |
| Package 3 — Machine prerequisites | Package 2 merged; separate Owner authorization | Deployment record/public keys/register/env/mounts installed outside repo; root ownership/modes, no symlink, trusted paths, distinct mount, fsync, runtime identities, frozen commit, restore epoch and all attestations proven read-only; provider calls=0; fence claims=0. |
| Package 4 — Gate D REC1-RUN1 | Packages 2–3 pass and merge; exact main frozen; fresh signed payload; fresh explicit Owner live authorization | One bounded execution only; Vidu status GET <=1; media download <=1; generation POST=0; durable fence/audit/read-back evidence; then STOP awaiting independent review. |

---

## D. Open Questions / Proof Deferred to Packages 2–3

1. Does the final `orbis_backend` image contain git metadata? **NOT PROVEN**.
2. Can a dedicated named volume or WSL2 native path satisfy root ownership, safe modes, exact trusted path, distinct mount, and directory fsync simultaneously? **NOT PROVEN**.
3. Do Docker Desktop Windows bind mounts satisfy the POSIX security checks? **NOT PROVEN; considered unsafe until demonstrated**.
4. What trusted evidence supplies the canonical DB backup SHA-256 needed by proposed restore epoch format? **NOT DOCUMENTED in BACKUP-RESTORE1**.
5. Can Phase 1–2 be evaluated without DB fence claim and without provider access? Current CLI has no verify-only mode; package 2 must add separately reviewed tooling.
6. Does actual runtime identity canonicalization yield exactly `postgresql://postgres:5432/orbis_studio` / `s3://http://minio:9000/orbis-assets`? Documentation aligns, but runtime result is **NOT PROVEN** by this docs-only package.
7. Does a separate register mount remain durable across container replacement and independent of DB/S3 backup/restore? **NOT PROVEN**.
8. What operational recovery policy applies if the process dies after `CLAIMED_PENDING_GET` and before GET? Source blocks rerun and contains no documented reset path; Owner decision remains required.

---

## E. Zero-Action Invariants

```text
PACKAGE_MODE = DOCS-ONLY / DESIGN / NO EXECUTION
PROVIDER_CALLS = 0
VIDU_STATUS_GETS = 0
MEDIA_DOWNLOADS = 0
GENERATION_POSTS = 0
PAID_CALLS = 0
REC1_RUN1_DISPATCHES = 0
DATABASE_CONNECTIONS = 0
DATABASE_WRITES = 0
S3_CONNECTIONS = 0
S3_WRITES = 0
DOCKER_ACTIONS = 0
DEPLOYMENTS = 0
RELEASE_ACTIONS = 0
KEYPAIRS_CREATED = 0
PRIVATE_KEY_MATERIAL_IN_REPO = 0
DEPLOYMENT_RECORDS_CREATED = 0
EXTERNAL_REGISTERS_CREATED = 0
FENCES_CLAIMED = 0
ATTESTATION_FLAGS_SET = 0

REC1_RUN1_STATUS = BLOCKED / NOT AUTHORIZED / UNCONSUMED
WP020_STATUS = ACTIVE / NOT CLOSED
CORE_V1_PROGRESS = 19 / 20 = 95%
CORE_V1_RELEASE_DECLARED = FALSE
NEXT_GATE = OWNER DECISION REQUIRED / REC1-RUN1 NOT AUTHORIZED
```

---

## F. Package Completion Contract

This package is complete only when this design and the seven control/roadmap documents are reviewed in one PR. Merge authorization, if later granted, approves this design record only. It does not authorize package 2, package 3, package 4, REC1-RUN1, any provider request, deployment, release, or WP020 closure.
