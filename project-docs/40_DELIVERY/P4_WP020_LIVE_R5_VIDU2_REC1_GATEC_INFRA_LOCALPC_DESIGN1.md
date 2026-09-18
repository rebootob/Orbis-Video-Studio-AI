# P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-LOCALPC-DESIGN1

## Package Metadata
- **Package Identity:** `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-LOCALPC-DESIGN1`
- **Project:** Orbis Video Studio AI
- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Base:** `6a8c0d2b55c74163a16faa15a30fb693a6d19e24`
- **Mode:** `DESIGN / PREFLIGHT / DOCS-ONLY / NO-MUTATION`
- **Owner Direction:** `LOCAL_PC_ONLY_FOR_APPLICATION_INFRASTRUCTURE`
- **Owner Authorization Comment:** `5729415989` (Issue #63)
- **Execution Plane:** Antigravity (bounded execution via Hermes orchestrator)

---

## 1. Executive Summary & Status Semantics
The Project Owner has established the definitive infrastructure decision for Orbis Video Studio AI:
- **Compute & Application Infrastructure:** All core application infrastructure (PostgreSQL database, S3-compatible object storage, backend API, render worker, frontend) shall run on the **Owner's local computer** (Windows PC with Docker Desktop / Docker Compose).
- **AI Provider Architecture:** Cloud AI architecture is strictly preserved (`CLOUD_AI_REQUIRED / LOCAL_AI_DISALLOWED`). External AI providers (Vidu, OpenAI, Gemini, ElevenLabs) remain cloud/API-based where existing repository architecture requires them.
- **Package Scope:** Strictly **DESIGN / PREFLIGHT / DOCS-ONLY / NO-MUTATION**. Zero containers created, zero containers started, zero databases created, zero migrations run, zero buckets created, zero network connectivity tests executed, zero secret plaintexts read or printed, zero AI provider calls.

### Status Semantics & Fence Invariants
```text
FINAL_RESULT = LOCALPC_DESIGN_COMPLETE
```
*Clarification of Status Meaning:*
- `FINAL_RESULT = LOCALPC_DESIGN_COMPLETE` means **DESIGN DOCUMENT COMPLETE ONLY**.
- It **MUST NOT** be interpreted as:
  - `RUNTIME READY`
  - `INFRASTRUCTURE VERIFIED`
  - `BIND1 READY`
  - `PROVISIONING COMPLETE`

*Standing Governance Fences:*
- `BIND1_ELIGIBILITY = NOT YET PROVEN`
- `BIND1_STATUS = NOT AUTHORIZED`
- `PROVISION1_STATUS = NOT AUTHORIZED`
- `REC1_RUN1_STATUS = BLOCKED / NOT AUTHORIZED / UNCONSUMED`
- `WP020_STATUS = ACTIVE / NOT CLOSED`
- `CORE_V1_PROGRESS = 19 / 20 = 95%`
- `CORE_V1_RELEASE_DECLARED = FALSE`

---

## 2. Repository Evidence & Architecture Analysis

### A. Host & Runtime
1. **Container Runtime:**
   - Canonical `docker-compose.yml` exists at repository root defining services: `db`, `minio`, `backend`, `render-worker`.
   - Network defined: bridge network `orbis_network`.
   - Host platform: Owner Windows PC running Docker Desktop (WSL2 backend).
2. **Backend Runtime (`backend/`):**
   - Base image: `python:3.12-slim` (`backend/Dockerfile`).
   - System packages: `libpq-dev`, `gcc`, `ffmpeg`, `fonts-noto-core`, `curl`.
   - Framework & Server: FastAPI, Uvicorn running on port `8000`.
   - Startup contract: `sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"`.
   - Healthcheck: HTTP GET `http://127.0.0.1:8000/api/v1/health` (or `/health`).
3. **Frontend Runtime (`frontend/`):**
   - Node.js runtime, Vite dev server (`frontend/vite.config.ts`), React 19 (`frontend/package.json`).
   - Default port: `5173`.
   - Reverse proxy configuration: `/api` proxies to `http://localhost:8000`.
   - CORS configuration: Backend explicitly supports `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`.
4. **Render Worker Runtime (`backend/app/services/render_worker.py`):**
   - Process entrypoint: `python -m app.services.render_worker`.
   - Component: `CloudRenderWorker` polling database for eligible `RenderJob` records.
   - Validation contract: `validate_runtime()` verifies:
     - `OBJECT_STORAGE_BUCKET` is configured.
     - `FFmpegRenderExecutor.validate_runtime()` executes `ffmpeg -version` (must be executable on PATH).
   - Poll interval: `ORBIS_RENDER_WORKER_POLL_SECONDS` (default 1.0s, bounds 0.1s - 30.0s).

### B. PostgreSQL Database Contract Truth & Configuration Gap
1. **Engine Version:** PostgreSQL 16 (`postgres:16-alpine` in `docker-compose.yml`).
2. **Repository Truth:**
   - `docker-compose.yml`:
     - `POSTGRES_SERVER = db`
     - `POSTGRES_DB = orbis_db`
     - `POSTGRES_PORT = 5432`
   - `backend/app/core/config.py`:
     - default `POSTGRES_SERVER = localhost`
     - default `POSTGRES_DB = orbis_db`
     - default `POSTGRES_PORT = 5432`
   - `backend/app/services/recovery_auth.py`:
     - `AUTHORIZED_RUNTIME_TARGET_PROFILES["UAT-COMPOSE-PERSISTENT"]` specifies:
       ```python
       "trusted_db_identities": [
           "postgresql+psycopg://localhost:5432/orbis_studio",
           "postgresql+psycopg://127.0.0.1:5432/orbis_studio",
           "postgresql+psycopg://postgres:5432/orbis_studio",
           "postgresql://localhost:5432/orbis_studio",
           "postgresql://127.0.0.1:5432/orbis_studio",
           "postgresql://postgres:5432/orbis_studio",
       ]
       ```
3. **Configuration Gap Explicit Finding:**
   ```text
   POSTGRES_LOCALPC_CONFIGURATION_STATUS = CONFIGURATION GAP / NOT YET VERIFIED
   ```
   - **Exact Mismatch:**
     - Compose runtime service host: `db`
     - Compose & default config DB name: `orbis_db`
     - Recovery profile accepted host: `localhost` | `127.0.0.1` | `postgres`
     - Recovery profile DB name: `orbis_studio`
   - **Status & Policy:**
     - Current repository configuration **DOES NOT YET deterministically match** the Gate-C recovery profile.
     - Current compose **MUST NOT** be stated as already fully Gate-C compatible.
     - Application, configuration, and code files are **NOT modified** in this docs-only package.
     - Any alignment of host aliases, compose DB identity, recovery profile, or application config belongs to a separately authorized future implementation/configuration package.
     - Standing invariant preserved: `BIND1_ELIGIBILITY = NOT YET PROVEN`.
4. **Migration Mechanism:** Alembic (`backend/alembic.ini`, `backend/migrations/env.py`). Migrations are run automatically on container startup or via `alembic upgrade head`.
5. **Connection String Contract:**
   - Built by `backend/app/core/config.py`: `PostgresDsn.build(scheme="postgresql+psycopg", username=..., password=..., host=..., port=..., path=...)`.
   - Can be explicitly overridden via `SQLALCHEMY_DATABASE_URI_OVERRIDE`.
6. **Database Extensions:** Zero specialized extensions required (no `pgvector`, `uuid-ossp`, or `citext` in migrations). Standard relational schema.
7. **Persistence Volume:** Named volume `postgres_data` mapped to `/var/lib/postgresql/data`.

### C. Object Storage (S3-Compatible MinIO) Truth
1. **Repository Truth & Contract Support:**
   - `backend/app/core/config.py`: Default `OBJECT_STORAGE_BUCKET = orbis-assets`.
   - `docker-compose.yml`: `OBJECT_STORAGE_BUCKET = orbis-assets`.
   - `backend/app/services/recovery_auth.py`: Accepts both `orbis-assets` and `orbis-media-assets`:
     ```python
     "trusted_storage_identities": [
         "s3://http://localhost:9000/orbis-media-assets",
         "s3://http://localhost:9000/orbis-assets",
         "s3://http://127.0.0.1:9000/orbis-media-assets",
         "s3://http://127.0.0.1:9000/orbis-assets",
         "s3://http://minio:9000/orbis-media-assets",
         "s3://http://minio:9000/orbis-assets",
     ]
     ```
   - `docker-compose.yml` MinIO volume: `minio_data:/data`.
2. **Required Wording Distinction:**
   - `REPOSITORY DEFAULT BUCKET = orbis-assets`
   - `RECOVERY PROFILE ACCEPTED ALTERNATIVE = orbis-media-assets`
   - `MINIO PERSISTENT VOLUME ROOT = /data`
   - *Architectural Note:* Bucket name represents a logical S3 namespace inside MinIO, not proof of a physical filesystem subdirectory layout such as `/data/orbis-media-assets`.
3. **Evidence-Bounded MinIO Capability Statement:**
   - `backend/app/services/storage/s3.py`: `S3CompatibleObjectStorageProvider` explicitly supports AWS S3, MinIO, Cloudflare R2, and Backblaze B2 using S3v4 signing and path-style addressing (`Config(signature_version="s3v4", s3={"addressing_style": "path"})`).
   - `docker-compose.yml` specifies `minio/minio:RELEASE.2024-03-03T17-50-39Z` command `server /data --console-address ":9001"`.
   - *Verifiable Statement:* **MinIO compatibility is supported by repository adapter and configuration contracts. Runtime connectivity, persistent-volume behavior, and durable-target verification were NOT EXECUTED / NOT PROVEN in this DESIGN/PREFLIGHT package.**
4. **Prefix Topology:**
   - Project assets: `projects/{project_id}/...`
   - Generated video/audio: `renders/{job_id}/...`
   - Temporary uploads: `temp/...`
5. **Ports:** `9000` (S3 API), `9001` (Web Console).
6. **Persistence Volume:** Named volume `minio_data` mapped to `/data`.

---

## 3. Local-PC Component Topology

```text
+-------------------------------------------------------------------------------+
|                             Owner Windows PC                                  |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                            Local Browser                              |   |
|   +-----------------------------------------------------------------------+   |
|           | (5173)                   | (8000)                  | (9001)       |
|           v                          v                         v              |
|   +------------------+      +------------------+      +-------------------+   |
|   |  Frontend (Vite) |      | Backend (FastAPI)|      |   MinIO Console   |   |
|   |  localhost:5173  |----->|  localhost:8000  |      |   localhost:9001  |   |
|   +------------------+      +------------------+      +-------------------+   |
|                                      |                                        |
|   ======================== Docker Network (orbis_network) =================   |
|                                      |                                        |
|              +-----------------------+-----------------------+                |
|              |                                               |                |
|              v                                               v                |
|   +----------------------+                       +------------------------+   |
|   |   PostgreSQL 16      |                       |   MinIO S3 Storage     |   |
|   |   Container:         |                       |   Container:           |   |
|   |   orbis_postgres_db  |                       |   orbis_minio          |   |
|   |   Port: 5432 (local) |                       |   Port: 9000 (local)   |   |
|   +----------------------+                       +------------------------+   |
|              |                                               |                |
|              v                                               v                |
|       [postgres_data]                                   [minio_data]          |
|     (Durable Local DB)                              (Durable Local Media)     |
|              ^                                               ^                |
|              |                                               |                |
|              +-----------------------+-----------------------+                |
|                                      |                                        |
|                             +------------------+                              |
|                             |  Render Worker   |                              |
|                             |  (Python/FFmpeg) |                              |
|                             +------------------+                              |
|                                                                               |
+-------------------------------------------------------------------------------+
```

---

## 4. Configuration Contracts & Secret Classification Matrix

*Zero-Plaintext Policy:* The repository consumes environment substitutions via `.env`. Plaintext secrets are never hard-coded as authoritative defaults, inspected, or printed.

| Config Key | A. Repository Default / Example Value | B. Secret Reference Name | C. Proposed Local-UAT Configuration | Contract Source |
|---|---|---|---|---|
| `POSTGRES_SERVER` | `db` (compose) / `localhost` (`config.py`) | N/A (non-secret) | `db` (in container network) / `127.0.0.1` (host-facing) | `docker-compose.yml`, `config.py` |
| `POSTGRES_PORT` | `5432` | N/A (non-secret) | `5432` | `docker-compose.yml`, `config.py` |
| `POSTGRES_DB` | `orbis_db` (repository default) | N/A (non-secret) | `orbis_studio` (target Gate C profile) | `docker-compose.yml`, `recovery_auth.py` |
| `POSTGRES_USER` | `orbis_user` | N/A (non-secret) | `orbis_user` | `docker-compose.yml` |
| `POSTGRES_PASSWORD` | `change_me_in_env_file` (`.env.example`) | `POSTGRES_PASSWORD` | *(Local UAT secret reference)* | `.env.example` |
| `OBJECT_STORAGE_ENDPOINT`| `http://minio:9000` (compose) / `http://localhost:9000` | N/A (non-secret) | `http://minio:9000` (in container) / `http://127.0.0.1:9000` (host) | `docker-compose.yml`, `config.py` |
| `OBJECT_STORAGE_BUCKET` | `orbis-assets` (repository default) | N/A (non-secret) | `orbis-assets` or `orbis-media-assets` | `config.py`, `docker-compose.yml`, `recovery_auth.py` |
| `OBJECT_STORAGE_REGION` | `us-east-1` | N/A (non-secret) | `us-east-1` | `config.py` |
| `OBJECT_STORAGE_ACCESS_KEY`| `minio_access_key` (`.env.example`) | `OBJECT_STORAGE_ACCESS_KEY` | *(Local UAT secret reference)* | `.env.example`, `docker-compose.yml` |
| `OBJECT_STORAGE_SECRET_KEY`| `change_me_minio_secret_key` (`.env.example`) | `OBJECT_STORAGE_SECRET_KEY` | *(Local UAT secret reference)* | `.env.example`, `docker-compose.yml` |
| `OBJECT_STORAGE_SECURE` | `False` | N/A (non-secret) | `False` (local HTTP) | `config.py` |
| `MAX_UPLOAD_SIZE_BYTES` | `104857600` (100MB) | N/A (non-secret) | `104857600` | `config.py` |
| `ORBIS_RENDER_WORKER_POLL_SECONDS` | `1.0` | N/A (non-secret) | `1.0` | `docker-compose.yml` |
| `ENVIRONMENT` | `development` | N/A (non-secret) | `uat` / `development` | `config.py` |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:5173", ...]` | N/A (non-secret) | Includes `http://localhost:5173`, `http://127.0.0.1:5173` | `config.py` |

---

## 5. Port and Network Exposure Matrix & Security Hardening

### Exposure Status
```text
CURRENT_COMPOSE_BINDING = NOT EXPLICITLY LOCALHOST-ONLY
```
- In canonical `docker-compose.yml`, published port mappings use standard forms:
  - `5432:5432` (PostgreSQL)
  - `9000:9000` (MinIO API)
  - `9001:9001` (MinIO Console)
  - `8000:8000` (Backend API)
- Without an explicit IP prefix, Docker binds to `0.0.0.0` on host interfaces. This is **not repository proof of explicit localhost-only binding**.

### Proposed Security Hardening
```text
PROPOSED SECURITY HARDENING = bind required host-facing ports to 127.0.0.1 in a future authorized configuration package.
```
- Examples shown as design proposals only (NOT applied in this package):
  - `127.0.0.1:5432:5432`
  - `127.0.0.1:9000:9000`
  - `127.0.0.1:9001:9001`
  - `127.0.0.1:8000:8000`
- **Network Invariant:** `NETWORK_MUTATIONS = 0`. Canonical `docker-compose.yml` is **NOT modified** in this documentation package.

| Service | Container / Process | Repository Port Mapping | Proposed Hardened Binding | Scope & Access Requirement |
|---|---|---|---|---|
| **PostgreSQL** | `orbis_postgres_db` | `5432:5432` | `127.0.0.1:5432:5432` | Localhost only. Internal bridge network access for backend & worker. |
| **MinIO API** | `orbis_minio` | `9000:9000` | `127.0.0.1:9000:9000` | Localhost only. S3 operations from backend & worker. |
| **MinIO Console** | `orbis_minio` | `9001:9001` | `127.0.0.1:9001:9001` | Localhost only. Owner web browser management. |
| **Backend API** | `orbis_backend` | `8000:8000` | `127.0.0.1:8000:8000` | Localhost only. Web browser API calls, OpenAPI docs. |
| **Frontend UI** | Vite dev server | N/A (native process) | `127.0.0.1:5173` | Localhost only. Owner web browser user interface. |
| **Render Worker**| `orbis_render_worker`| None | None | Outbound connection to `db:5432` and `minio:9000` via Docker bridge. |

---

## 6. Storage and Volume Matrix

| Storage Category | Data Classification | Target Path / Volume | Durability & Lifecycle |
|---|---|---|---|
| **PostgreSQL Database** | **DURABLE** | Docker volume `postgres_data` (`/var/lib/postgresql/data`) | High. Must persist across container recreation. Backed up regularly. |
| **Object Storage Media** | **DURABLE** | Docker volume `minio_data` (`/data`) | High. Contains master uploaded assets and source audio/video clips in logical S3 bucket (`orbis-assets` / `orbis-media-assets`). |
| **Authoritative Register**| **DURABLE** | Local file `/var/run/orbis/external_execution_register.json` | High. Execution fence and recovery registration state. |
| **Rendered Exports** | **REGENERABLE** | MinIO logical prefix `renders/{job_id}/` | Medium. Can be reproduced from timeline assembly and source assets. |
| **Frontend Build** | **REGENERABLE** | `frontend/dist/` | Low. Regenerated via `npm run build`. |
| **Secrets & Keys** | **SECRET** | `.env` / `backend/.env` (gitignored) | High security. Machine-local only; never committed to git. |
| **Worker Scratch Space** | **TEMPORARY** | `/tmp` / intermediate FFmpeg working files | Ephemeral. Cleared after render completion. |
| **Service Logs** | **TEMPORARY** | Docker container stdout/stderr | Ephemeral or rotated via Docker logging driver. |

---

## 7. Secret-Reference Matrix

*Zero-Plaintext Invariant:* Only environment variable reference names and delivery scopes are documented. Plaintext secrets are never stored, inspected, or printed.

| Secret Reference Name | Scope / Target | Delivery Mechanism | Classification |
|---|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL Container & Backend DB URI | Local `.env` file | Sensitive Credential |
| `MINIO_ROOT_PASSWORD` | MinIO root administrator | Local `.env` file | Sensitive Credential |
| `OBJECT_STORAGE_SECRET_KEY` | Backend S3 Boto3 client | Local `.env` file | Sensitive Credential |
| `SECRET_KEY` | FastAPI JWT session encoding | Local `.env` file | Cryptographic Secret |
| `FIRST_SUPERUSER_PASSWORD` | Initial admin account creation | Local `.env` file | Sensitive Credential |
| `VIDU_API_KEY` | Cloud Vidu provider adapter (preserved) | Local `.env` file | External API Credential |
| `OPENAI_API_KEY` | Cloud OpenAI provider adapter (preserved) | Local `.env` file | External API Credential |
| `GEMINI_API_KEY` | Cloud Gemini provider adapter (preserved) | Local `.env` file | External API Credential |
| `ELEVENLABS_API_KEY` | Cloud ElevenLabs provider adapter (preserved) | Local `.env` file | External API Credential |

---

## 8. Backup and Restore Design (Local Durable Strategy)

### Backup Components & Proposed Procedures
1. **PostgreSQL Database Backup:**
   - Proposed Mechanism: `docker exec orbis_postgres_db pg_dump -U orbis_user -Fc orbis_studio > backup_orbis_studio_$(date +%Y%m%d_%H%M%S).dump`
   - Destination Class: Dedicated local backup directory on secondary physical disk or dedicated backup volume.
   - Frequency Proposal: Prior to any schema migration or major recovery operation; daily during active work.
   - Retention Proposal: 7 daily backups, 4 weekly snapshots.
2. **Object Storage Backup:**
   - Proposed Mechanism: MinIO client mirror (`mc mirror local/<bucket> /backups/storage/<bucket>/`) or volume filesystem snapshot.
   - Frequency Proposal: Synchronized with database dumps.
   - Retention Proposal: Matched to database snapshot retention.
3. **Configuration & Recovery Registry Backup:**
   - Proposed Mechanism: Encrypted archive of `.env` configuration and `external_execution_register.json`.
   - Frequency Proposal: On any configuration change.

### Proposed Restore Ordering
- **Step 0 (Config):** Verify and restore environment configuration and signed registry metadata.
- **Step 1 (Infrastructure):** Start PostgreSQL and MinIO containers.
- **Step 2 (Database):** Recreate target database and restore from `pg_dump` archive (`pg_restore`).
- **Step 3 (Storage):** Mirror media assets into MinIO bucket.
- **Step 4 (Application):** Start backend API and render worker; verify `/api/v1/health` and database connectivity.

*Invariant:* Zero backup or restore execution in this design package.

---

## 9. Hardware & Resource Assessment

| Resource | Repository-Proven Requirement | Engineering Recommendation (Owner PC) | Basis |
|---|---|---|---|
| **CPU** | x86_64 / arm64 architecture capable of running Docker Linux containers and FFmpeg. | **4 physical cores / 8 vCPUs** minimum. | FFmpeg 1080p multi-track video encoding and subtitle burn-in require multi-threaded CPU capacity. |
| **RAM (PostgreSQL)** | Standard PostgreSQL 16 container footprint. | **1 GB - 2 GB** allocated. | Sufficient for UAT catalog and transaction buffers. |
| **RAM (MinIO)** | Go binary footprint (~100 MB baseline). | **512 MB - 1 GB** allocated. | Accommodates buffered multipart uploads. |
| **RAM (Backend API)** | Python 3.12 + FastAPI + Uvicorn (~150 MB baseline).| **1 GB** allocated. | Accommodates async request spikes and ORM sessions. |
| **RAM (Render Worker)**| Python + FFmpeg subprocesses. | **2 GB - 4 GB** allocated. | Video frame manipulation and audio mixing buffers. |
| **RAM (Frontend Dev)** | Node.js Vite process. | **512 MB - 1 GB**. | Local development server. |
| **Total Host RAM** | Docker Desktop baseline. | **8 GB floor, 16 GB preferred**. | Ensures smooth parallel operation of all containers without swapping. |
| **Disk Space Floor** | Docker images (~5 GB) + DB (~1 GB) + MinIO base (~2 GB). | **20 GB free space floor**. | Minimum space for images, containers, and test datasets. |
| **Preferred Disk Space** | Video library growth (100MB+ per full project timeline). | **50 GB - 100 GB** available. | Long-term asset retention and multiple project versions. |
| **Docker WSL2 Settings** | Docker Desktop default or `.wslconfig`. | `processors=4`, `memory=8GB`, `swap=2GB`. | Recommended `.wslconfig` limits to prevent Docker consuming full host RAM. |

---

## 10. Remaining Unknowns
1. **Host Docker Installation State:** Current presence and version of Docker Desktop and Docker Compose on the Owner's Windows PC.
2. **Local Storage Mount Paths:** Exact Windows drive letter (e.g. `C:` vs `D:`) or secondary physical drive designated for long-term durable backup storage.
3. **Host Available Free Space:** Current free disk capacity on the target host volume.

---

## 11. Proposed Next Package Only
- **Package Identity:** `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-LOCALPC-PROVISION-PREP1`
- **Scope:** Read-only inspection of host Docker Desktop availability, version compatibility, and free disk space check on Owner PC. Zero mutations, zero provisioning.

---

## 12. Explicit Zero-Action Evidence

```text
APPLICATION_BINDING_ACTIONS = 0
PROVISIONING_ACTIONS = 0
DOCKER_INSTALLATIONS = 0
CONTAINER_CREATIONS = 0
CONTAINER_STARTS = 0
CLOUD_RESOURCE_CREATIONS = 0
CLOUD_RESOURCE_MUTATIONS = 0
IAM_MUTATIONS = 0
NETWORK_MUTATIONS = 0
CONNECTIVITY_TESTS = 0
SECRET_VALUE_READS = 0
SECRET_VALUE_PRINTS = 0
SECRET_MUTATIONS = 0
DATABASE_CREATIONS = 0
DATABASE_WRITES = 0
DATABASE_MIGRATIONS_EXECUTED = 0
OBJECT_BUCKET_CREATIONS = 0
OBJECT_WRITES = 0
BACKUP_EXECUTIONS = 0
RESTORE_EXECUTIONS = 0
REAL_VIDU_GET_CALLS = 0
VIDU_GENERATION_POSTS = 0
OPENAI_PROVIDER_CALLS = 0
GEMINI_PROVIDER_CALLS = 0
ELEVENLABS_PROVIDER_CALLS = 0
REAL_AI_PROVIDER_CALLS = 0
PAID_PROVIDER_CALLS = 0
REC1_RUN1_DISPATCHES = 0
DEPLOYMENTS = 0
RELEASE_ACTIONS = 0
```

---
*End of Design Document `P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_LOCALPC_DESIGN1.md`.*
