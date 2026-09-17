# P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1 — Gate C UAT Infrastructure Decision Record

## Executive Summary

```text
PACKAGE: P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1
MODE: DOCS-ONLY + READ-ONLY DECISION PREPARATION
OWNER_AUTHORIZATION: APPROVED IN CHAT 2026-09-17 (Issue #63 comment 5716927467)
AUTHORIZED_BASE_MAIN: cb20631556bafdeaf17373fca3fd7ef8d9234c80
PREDECESSOR_PACKAGE: P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-VERIFY1-CLOSE (PR #112 / cb20631556bafdeaf17373fca3fd7ef8d9234c80)
DECISION1_RESULT: OWNER_INFRA_PATH_DECISION_REQUIRED
ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1
ACTIVE_EXECUTION_PACKAGE: NONE
NEXT_CONTROL_DECISION: OWNER UAT INFRASTRUCTURE PATH DECISION
```

---

## 1. Purpose & Governance Boundaries

This document prepares the canonical Owner Decision Package for Gate C UAT Infrastructure under Phase 4 Work Package 20 (`P4-WP020`).

### Governance Boundaries
- **No Autonomous Path Selection**: This package presents two bounded architectural paths (Path A and Path B) without deciding or pre-selecting either path on behalf of the Owner.
- **Zero Provisioning**: Absolutely no cloud resources, databases, storage buckets, or VMs are created, modified, or started.
- **Zero Backup / Restore**: No backups or restorations are executed.
- **Zero Execution / Provider Calls**: No real provider calls (Vidu, OpenAI, Gemini, ElevenLabs), no dispatches of `REC1-RUN1`, and no deployment mutations.
- **Preserved Status**: `WP020 = ACTIVE / NOT CLOSED`, `CORE_V1 = 19/20 = 95%`, `RELEASE = NOT DECLARED`.

---

## 2. Starting Truth & Current Baseline State

Based on Gate C verification in PR #111 / PR #112:
- **GATE_C_VERIFY_RESULT**: `BLOCKED_INFRA_CONFIGURATION_INCOMPLETE`
- **EXTERNAL_UAT_POSTGRES_EXISTENCE**: `UNKNOWN / NOT VERIFIED`
- **CURRENT_RUNTIME_UAT_POSTGRES_CONFIGURATION**: `ABSENT / UNCONFIGURED`
- **EXTERNAL_UAT_STORAGE_EXISTENCE**: `UNKNOWN / NOT VERIFIED`
- **CURRENT_RUNTIME_UAT_STORAGE_CONFIGURATION**: `ABSENT / UNCONFIGURED`
- **DEDICATED_UAT_COMPUTE_EXISTENCE**: `UNKNOWN / NOT VERIFIED`
- **UAT_ISOLATION**: `UNKNOWN / NOT VERIFIED`
- **BACKUP_CAPABILITY**: `UNKNOWN / NOT VERIFIED`
- **RESTORE_CAPABILITY**: `UNKNOWN / NOT VERIFIED`
- **REC1_RUN1_STATUS**: `BLOCKED / NOT AUTHORIZED / UNCONSUMED`

*Note: UNKNOWN remains UNKNOWN and is NOT converted to "NOT PROVISIONED" without direct evidence.*

---

## 3. Read-Only Environment & Credential Key Discovery

In accordance with safety rules, only environment variable names and secret reference keys were inspected:
- Database variables referenced in codebase: `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `SQLALCHEMY_DATABASE_URI`.
- Object Storage variables referenced: `OBJECT_STORAGE_ENDPOINT`, `OBJECT_STORAGE_REGION`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY`, `OBJECT_STORAGE_SECRET_KEY`, `OBJECT_STORAGE_SECURE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
- Credential Values: Not inspected, not logged, not committed.
- Credential Status: `UNVERIFIED` (values are absent from repository tracking and local git-bash runtime).

---

## 4. Path Analysis

### Path A: Use / Bind Existing UAT Infrastructure
**Concept**: Point the application runtime to an existing, already-provisioned external PostgreSQL instance and S3-compatible object storage bucket managed by the Owner / Organization.

- **Minimum Requirements**:
  1. **PostgreSQL**:
     - PostgreSQL 16+ compatible.
     - Persistent external storage with dedicated UAT schema/database isolation.
     - Connection identity (host/port/dbname) provided by Owner/Admin.
     - Credential references injected via GitHub Secrets / secure environment.
     - Backup capability identifiable.
     - No production-data mutation required.
  2. **Object Storage**:
     - S3-compatible or contract-compatible persistent storage.
     - Dedicated UAT bucket or prefix isolation (e.g. `orbis-uat-assets`).
     - Endpoint and region identity known.
     - Object durability and versioning/retention capability identifiable.
  3. **Compute**:
     - Stateless runtime / runner compatible with external DB/storage.
     - Isolated from production network.
     - External provider execution disabled by default.
- **Candidate Next Package**: `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-BIND1`
- **Status**: `PROPOSED / NOT AUTHORIZED`
- **Mutations Required**: Configuration/secret binding only (no cloud provisioning).

---

### Path B: Separately Authorize New UAT Infrastructure Provisioning
**Concept**: Authorize dedicated provisioning of new cloud infrastructure (e.g., AWS RDS / Supabase / Neon PostgreSQL + AWS S3 / Cloudflare R2 bucket + dedicated compute container).

- **Provisioning Specification Requirements**:
  1. **PostgreSQL Resource**: Dedicated managed PostgreSQL 16 instance.
  2. **Object Storage Resource**: Dedicated S3-compatible bucket with CORS and TLS encryption.
  3. **Compute / Runtime**: Isolated container/runner environment.
  4. **Region / Location**: Standard low-latency region (e.g., ap-southeast-1 or us-east-1).
  5. **Isolation**: Dedicated VPC/network rules or distinct project tenancy separating UAT from Dev/Prod.
  6. **Secrets Management**: KMS / Cloud secret store or GitHub repository environments.
  7. **Backup / Restore**: Point-in-time recovery (PITR) or automated snapshot lifecycle.
  8. **Cost Estimates**: `UNKNOWN / REQUIRES PROVIDER/PLATFORM QUOTE OR OWNER TARGET SELECTION`.
  9. **Decommission / Rollback**: Ability to destroy or pause resources when testing concludes.
- **Candidate Next Package**: `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PROVISION1`
- **Status**: `PROPOSED / NOT AUTHORIZED`
- **Mutations Required**: Cloud resource creation, IAM roles, billing commitment, external infrastructure state creation.

---

## 5. Owner Decision Matrix

| Dimension | Path A: Bind Existing Infrastructure | Path B: Provision New Infrastructure |
| :--- | :--- | :--- |
| **Known Evidence** | Codebase supports standard Postgres & S3 env vars; local compose has templates. | No active cloud provisioning scripts or Terraform state in repo. |
| **Unknowns** | Whether dedicated UAT instances exist in Owner's accounts. | Platform provider preference, sizing, region, and target budget. |
| **Required Owner/Admin Inputs** | Hostname, port, DB name, bucket name, credential refs. | Choice of cloud provider, budget approval, provisioning execution approval. |
| **Mutation Required?** | No cloud resource creation; secrets/config binding only. | Yes: Cloud resource creation, subscription/IAM mutation. |
| **Potential Cost?** | Minimal/zero additional cost (if using existing resources). | `UNKNOWN / REQUIRES PROVIDER/PLATFORM QUOTE OR OWNER SELECTION`. |
| **Proposed Next Package** | `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-BIND1` | `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PROVISION1` |
| **Authorization State** | `PROPOSED / NOT AUTHORIZED` | `PROPOSED / NOT AUTHORIZED` |

---

## 6. Canonical Result for this Package

```text
DECISION1_RESULT = OWNER_INFRA_PATH_DECISION_REQUIRED
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1
ACTIVE_EXECUTION_PACKAGE = NONE
PACKAGE_STATUS = IN REVIEW / NOT MERGED
NEXT_CONTROL_DECISION = OWNER UAT INFRASTRUCTURE PATH DECISION
```

Neither Path A nor Path B is pre-selected or authorized. Owner review and path decision is mandatory before any binding or provisioning package can be designed or executed.

---

## 7. Zero-Action Invariants Verification

- REAL_VIDU_GET_CALLS: 0
- VIDU_GENERATION_POSTS: 0
- OPENAI_PROVIDER_CALLS: 0
- GEMINI_PROVIDER_CALLS: 0
- ELEVENLABS_PROVIDER_CALLS: 0
- REAL_PROVIDER_CALLS: 0
- PAID_PROVIDER_CALLS: 0
- NEW_PROVIDER_JOBS: 0
- REC1_RUN1_DISPATCHES: 0
- PROVISIONING_ACTIONS: 0
- CLOUD_RESOURCE_CREATIONS: 0
- CLOUD_RESOURCE_MUTATIONS: 0
- BACKUP_EXECUTIONS: 0
- RESTORE_EXECUTIONS: 0
- DEPLOYMENTS: 0
- RELEASE_ACTIONS: 0
- HISTORICAL_JOB_995880130565918720_QUERIED: FALSE
- HISTORICAL_RUN_34569728383_RERUN: FALSE
