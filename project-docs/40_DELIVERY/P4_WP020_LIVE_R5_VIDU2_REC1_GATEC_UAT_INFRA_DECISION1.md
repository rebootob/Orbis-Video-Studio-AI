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

- **Existence Truth**: `EXISTING_UAT_TARGET_EXISTENCE = UNKNOWN / NOT VERIFIED`
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
- **Cost Truth**: `UNKNOWN / DEPENDS ON OWNER-PROVIDED EXISTING-INFRASTRUCTURE ALLOCATION, CAPACITY, LICENSING, AND INCREMENTAL COST` (No claim of free, zero-cost, or minimal-cost is made).
- **Required Owner / Admin Inputs**:
  - `POSTGRES_TARGET_IDENTITY`:
    - Hostname or endpoint identity
    - Port
    - Database name
    - Isolation model (e.g. dedicated DB instance vs isolated database/schema)
  - `OBJECT_STORAGE_TARGET_IDENTITY`:
    - Endpoint
    - Region if applicable
    - Bucket / prefix identity
  - `COMPUTE_RUNTIME_TARGET_IDENTITY`:
    - Runtime / platform identity
    - Environment identity
    - Deployment target name / reference
    - Isolation boundary
  - `SECRET_REFERENCE_MECHANISM`:
    - GitHub Environment Secrets OR Cloud secret manager OR equivalent organization-approved secret store
  - `SECRET_REFERENCE_NAMES`:
    - Specific environment variable / secret key names (values MUST NOT be recorded)
  - `OWNER / ADMIN CONFIRMATIONS`:
    - Target ownership confirmation
    - Explicit UAT authorization to use target
    - Expected retention period
    - Acceptable data classification
    - Backup / restore expectations
    - Assessment whether incremental usage has billing / licensing impact
- **Candidate Next Package**: `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-BIND1`
- **Status**: `PROPOSED / NOT AUTHORIZED`
- **Mutations Required**: Configuration/secret binding only (no cloud provisioning).

---

### Path B: Separately Authorize New UAT Infrastructure Provisioning
**Concept**: Authorize dedicated provisioning of new cloud infrastructure (e.g., managed PostgreSQL 16+ + dedicated S3-compatible bucket + isolated compute container/runner).

- **Candidate Next Package**: `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PROVISION1`
- **Status**: `PROPOSED / NOT AUTHORIZED`
- **Mutations Required**: Cloud resource creation, IAM roles, billing commitment, external infrastructure state creation.

#### Path B — Minimum Sizing / Capacity Assumptions (Decision-Preparation Classification)
*(Note: Decision-preparation classifications only; exact sizing requires Owner target selection)*
- `POSTGRES_ENGINE`: `PostgreSQL 16+ compatible`
- `POSTGRES_CPU`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `POSTGRES_MEMORY`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `POSTGRES_STORAGE`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `POSTGRES_CONNECTION_CAPACITY`: `TBD / WORKLOAD-SIZING REQUIRED`
- `OBJECT_STORAGE_CAPACITY`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `OBJECT_STORAGE_RETENTION`: `TBD / UAT RETENTION POLICY REQUIRED`
- `COMPUTE_CPU`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `COMPUTE_MEMORY`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `COMPUTE_REPLICA_COUNT`: `TBD / OWNER TARGET SELECTION REQUIRED`
- `NETWORK_EGRESS_REQUIREMENT`: `TBD / PROVIDER + TEST-SCOPE DEPENDENT`
- `REGION`: `TBD / OWNER TARGET SELECTION REQUIRED` (Examples such as ap-southeast-1 or us-east-1 are illustrative examples only, never selected target truth).

#### Path B — Cost Categories
- **Recurring Cost Categories**:
  - Managed PostgreSQL instance / runtime
  - PostgreSQL persistent storage
  - PostgreSQL backup / PITR retention
  - Object storage capacity
  - Object storage request operations (GET/PUT/LIST)
  - Object storage versioning / retention if enabled
  - Compute / container / runtime
  - Network egress
  - Logging / monitoring if separately billed
  - Secret-management service if separately billed
  - Static IP / load-balancer / network services if required
  - **Classification**: `EXACT_RECURRING_COST = UNKNOWN / REQUIRES OWNER TARGET + PROVIDER QUOTE`
- **One-Time / Setup Cost Categories**:
  - Environment / bootstrap setup
  - IAM / service-account setup
  - Network / security configuration
  - DB initialization / migration preparation
  - Bucket / prefix setup
  - Backup / restore validation preparation
  - Decommission / cleanup activity if separately charged
  - **Classification**: `EXACT_ONE_TIME_COST = UNKNOWN / REQUIRES OWNER TARGET + PROVIDER QUOTE`

#### Path B — Future Acceptance Criteria (Informational / Future Implementation Only)
*(Note: These are FUTURE acceptance criteria for a future provisioning package. They are NOT marked PASS in DECISION1.)*
1. PostgreSQL target exists and is isolated for UAT.
2. PostgreSQL version is compatible with PostgreSQL 16+ requirements.
3. Object storage target exists with dedicated UAT isolation.
4. Compute / runtime target is isolated from production.
5. Secret values are stored outside repository.
6. Runtime references only approved secret names / references.
7. Provider execution remains disabled by default.
8. Backup capability is explicitly identified.
9. Restore capability is explicitly identified.
10. Backup / restore test remains separately authorized.
11. No production data is required or mutated.
12. Resource ownership and billing account are explicitly known.
13. Rollback / decommission procedure is documented.
14. Security / network boundary is documented.
15. Owner accepts expected recurring / one-time cost classification before provisioning.
16. No REC1-RUN1 authorization is implied.

#### Owner Approvals Required Before Path B Mutation
A future `PROVISION1` package MUST NOT execute until Owner explicitly approves:
1. Cloud / provider / platform selection
2. Account / project / subscription target
3. Region
4. PostgreSQL sizing
5. PostgreSQL storage / retention
6. Object storage target / sizing / retention
7. Compute sizing / runtime
8. Network / security boundary
9. IAM / service-account mutation
10. Secret-management mechanism
11. Recurring cost ceiling or accepted cost basis
12. One-time setup cost ceiling or accepted cost basis
13. Rollback / decommission ownership and schedule
14. Explicit execution authorization comment referencing the provisioning package
15. Backup capability design
16. Restore capability design
17. Exact provisioning package identity AND exact authorized base HEAD (Owner approval must be bound to: exact future package name, exact canonical base HEAD, and exact mutation scope)

APPROVAL OF DECISION1 != APPROVAL TO PROVISION

MERGE OF DECISION1 != APPROVAL TO PROVISION

APPROVAL OF A FUTURE PROVISIONING PACKAGE MUST BE BOUND TO AN EXACT PACKAGE AND EXACT BASE HEAD

---

## 5. Owner Decision Matrix

| Dimension | Path A: Bind Existing Infrastructure | Path B: Provision New Infrastructure |
| :--- | :--- | :--- |
| **Known Evidence** | Codebase supports standard Postgres & S3 env vars; local compose has templates. | No active cloud provisioning scripts or Terraform state in repo. |
| **Unknowns** | Whether dedicated UAT instances exist in Owner's accounts (`EXISTING_UAT_TARGET_EXISTENCE = UNKNOWN / NOT VERIFIED`). | Platform provider preference, sizing, region, and target budget. |
| **Required Owner/Admin Inputs** | Hostname, port, DB name, bucket name, secret refs, ownership/retention/billing impact confirmation. | Provider selection, account/region, sizing, IAM boundaries, cost ceiling, provisioning approval. |
| **Mutation Required?** | No cloud resource creation; secrets/config binding only. | Yes: Cloud resource creation, subscription/IAM mutation. |
| **Potential Cost?** | `UNKNOWN / DEPENDS ON OWNER-PROVIDED EXISTING-INFRASTRUCTURE ALLOCATION, CAPACITY, LICENSING, AND INCREMENTAL COST` | `EXACT_RECURRING_COST = UNKNOWN / REQUIRES OWNER TARGET + PROVIDER QUOTE`<br>`EXACT_ONE_TIME_COST = UNKNOWN / REQUIRES OWNER TARGET + PROVIDER QUOTE` |
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
