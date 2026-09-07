# Work Package Roadmap

> **Canonical Document Location:** [`project-docs/40_DELIVERY/WORK_PACKAGES.md`](project-docs/40_DELIVERY/WORK_PACKAGES.md)

---

## 1. Roadmap Overview

Orbis Video Studio AI is delivered through discrete, bounded Work Packages. Every WP requires explicit Owner authorization before implementation. Completion of one WP never auto-authorizes the next.

The product direction is automation-first: Orbis should orchestrate external Creative, Image, Video and Audio AI services behind adapters while owning the production state, approvals, history, cost control, QC, assembly and export workflow.

```mermaid
graph TD
    P0["P0 Foundation & Governance"] --> P1["P1 Core Architecture & Data Engine"]
    P1 --> P2["P2 Generation, Workspace & Production Orchestration"]
    P2 --> P3["P3 Audio, Assembly, QC & Cloud Render"]
    P3 --> P4["P4 Multi-Output, Export & Core V1"]
    P4 -.-> PX["Post-Core V1 / V1.x Integrations"]
```

---

## 2. Completed Work

- **P0-WP001 — Project Governance & Architecture Documentation Foundation**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP002 — Backend Core Framework & Domain Database Setup**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP003 — S3 Object Storage & Asset Management API**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP004 — Document Ingestion & Text Extraction Engine**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP005 — Story & Screenplay Script Generator Service**
  - **Status:** PASS / CLOSED / MERGED

- **P2-WP006 — Reference Library & Character/Location Bibles**
  - **Status:** PASS / CLOSED / MERGED

- **P2-WP007 — Vidu Provider Adapter & Durable Job Dispatch Queue**
  - **Status:** PASS / CLOSED / MERGED
  - **PR:** #15
  - **Reviewed Head:** `5a03d4d7f56ac8ae39a78914276610c0512da78b`
  - **Merge Commit:** `9cb098dea7fc2948b023ad48163c729f566573a7`

- **P2-WP008 — Hybrid Shot Engine, Asset Lock Machine & Base Video Mode Configuration**
  - **Status:** PASS / CLOSED / MERGED
  - **PR:** #19
  - **Reviewed Head:** `a2c3f3d4e80a0b0aedb58fba5a04a436c9e88797`
  - **Merge Commit:** `a360c3b38d1d962f9f3c5f6412e3107e90fae7db`

- **P2-WP009 — Cost Control & Granular Usage Audit Ledger**
  - **Status:** PASS / CLOSED / MERGED
  - **PR:** #23
  - **Reviewed Head:** `250df0bb6df24577e2e1f14c7ada3d0dbbaf75fa`
  - **Merge Commit:** `9f094a5cbe9a4faeb5741231d0a819da0da283c1`
  - **Scope delivered:** provider-neutral usage ledger, configurable pricing service, project budget controls, manual adjustment audit, DB-level idempotency/uniqueness and concurrency-safe accounting behavior.

- **P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #24
  - **PR:** #25
  - **Reviewed Head:** `0f0a16fa95c8110bc8ab7a0c52d45351eaa82182`
  - **Merge Commit:** `639e61fb69b6abee8598074add458035db906ceb`
  - **Final Review:** PASS / READY TO MERGE (Review ID 5124386306)
  - **Scope delivered:** Mode-aware workspace (Story/Short/Loop/Scene), staged workflow with production approval gates, soft-delete / version lineage retention (FULL_HISTORY_RETENTION / NO_SILENT_HISTORY_LOSS), dashboard project management (rename/duplicate/archive/search/sort), actionable queue controls (Generate Selected / Continue incomplete / safe cost confirmation), and provider submission stage fencing.

- **P2-WP011 — Selective / Batch Regeneration & Resume Service + Performance & Scalability Guardrails**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #28
  - **PR:** #29
  - **Reviewed Head:** `b2f349adb6d5704fa1aadfb19e06644b40a37080`
  - **Merge Commit:** `643614b089a295ea96be179e470707609cbe4b53`
  - **Final Review:** PASS / READY TO MERGE (Review ID 5124729394)
  - **Scope Delivered:**
    - Canonical `BatchResumeService` supporting Generate Selected, Continue Incomplete, and Retry Failed.
    - Shot-level deduplication (at most ONE new job per shot, even with multiple historical failed jobs).
    - Repeat-safe resume semantics (no duplicate active work, preservation of completed assets).
    - Transactional `GenerationJob` + `UsageLedger` + `BatchRunItem` atomic persistence with savepoint rollback isolation.
    - Strictly bounded keyset processing via `(created_at, id)` snapshot, eliminating full-project candidate in-memory materialization.
    - Streaming chunk processing (`EXECUTE_CHUNK_SIZE = 50`) and set-based DB queries (zero N+1 queries).
    - Strictly bounded memory retention (`MAX_COMPATIBILITY_RETURNED_JOBS = 100`, `accumulate_jobs=False` on canonical resume).
    - Fail-closed legacy `/jobs/batch` execution boundary ($\le 100$) with atomic rollback on capacity breach.
    - Lightweight `BatchRun` & `BatchRunItem` audit trail with truthful skip reasons and dynamic read reconciliation.
    - Migration `011_batch_resume_runs_and_indexes.py` with targeted indexes.
    - Full frontend integration removing client-side retry loops and guarding stage transitions.

- **P2-WP012 — Production Orchestrator & Staged Approval State Machine**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #31
  - **PR:** #32
  - **Reviewed Head:** `a781926bbf607cad1b992d089920be6f094e41c9`
  - **Merge Commit:** `cdd79aaa80eaefa8be6c4e4894cb40db0b097a60`
  - **Final Review:** PASS / READY TO MERGE (Review ID 5125098674)
  - **Scope Delivered:** Server-side Orchestrator Service, stage transition gates, mode routing (STORY, SHORT, LOOP, SCENE), automation modes (MANUAL, ASSISTED, AUTO), append-only orchestration audit ledger, frontend integration.

- **P2-WP013 — Storyboard Image / Keyframe Pipeline**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #33
  - **PR:** #34
  - **Reviewed Head:** `f9fd46b917390224a5ab58bad0d3be238edbd7b3`
  - **Merge Commit:** `c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd`
  - **Final Review:** PASS / READY TO MERGE
  - **Scope Delivered:** Provider-neutral ImageProvider abstraction, storyboard keyframe generation, continuity/reference integration, batch image generation.

- **P3-WP014 — Core V1 Audio Production Automation**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #35
  - **PR:** #36
  - **Reviewed Head:** `cbbcea8c9a84bd9c08222dabf95d1788b2d3945e`
  - **Merge Commit:** `f50e2568d197b3c4bab5e4303f31af817db6e1bf`
  - **Final Review:** PASS / READY TO MERGE (Review ID 5125802846)
  - **Scope Delivered:** Provider-neutral AudioProvider boundary, 3D audio taxonomy (source, type, generation mode), AudioSpec render, scope lineage, volume/fade/ducking mixing metadata, usage ledger integration.

- **P3-WP015 — Simplified Assembly / Timeline Preview**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #37
  - **PR:** #38
  - **Reviewed Head:** `640212f71182ba3f6a5024a442beb363868eabc1`
  - **Merge Commit:** `35b31c3c41834209fcb9d63ad7ac52e9632d63d2`
  - **Final Review:** PASS / READY TO MERGE (Review ID 5127082342)
  - **Scope Delivered:** Simplified assembly timeline engine, shot ordering, non-destructive timeline overrides, manual placement & lock preservation, transition preview specs, auto-assembly idempotency, frontend timeline workspace.

---

## 3. Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
```

- **Current Status:** POST-WP015 / READY FOR OWNER NEXT-WP AUTHORIZATION
- P3-WP016 remains: `PROPOSED / NOT AUTHORIZED`. Do not implement or silently authorize WP016 without explicit Owner authorization.

---

## 4. Remaining Roadmap — Direction After WP015

The roadmap should prioritize end-to-end production automation rather than building a heavyweight manual NLE.

### Phase 2 — Production Orchestration & Generation

- **P2-WP012 — Production Orchestrator & Staged Approval State Machine**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #31
  - **PR:** #32 (Merged into `main` at `cdd79aaa80eaefa8be6c4e4894cb40db0b097a60`)

- **P2-WP013 — Provider-Neutral Storyboard Image / Keyframe Pipeline**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #33
  - **PR:** #34 (Merged into `main` at `c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd`)

### Future Provider Planning Note — ComfyUI / Cloud GPU

Preserve provider-neutral architecture. ComfyUI + Cloud GPU is a FUTURE provider/execution candidate.

Concept:
```text
Orbis
-> GenerationJob
-> Provider Adapter
-> ComfyUI Provider
-> Cloud GPU Worker
-> Object Storage
-> Orbis Asset / Version / History
```

Status: `PROPOSED / NOT AUTHORIZED / NOT IMPLEMENTED`

Important product locks:
- Vidu remains the only currently implemented registered VideoProvider.
- ComfyUI must not replace the provider abstraction.
- Do not add ComfyUI source code in this docs sync.
- Do not select a GPU cloud vendor yet.
- `LOCAL_AI` remains disallowed.
- Cloud-hosted ComfyUI is compatible with `CLOUD_AI` direction.

### Phase 3 — Audio, Assembly, QC & Cloud Rendering

- **P3-WP014 — Core V1 Audio Production Automation**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #35
  - **PR:** #36 (Merged into `main` at `f50e2568d197b3c4bab5e4303f31af817db6e1bf`)

- **P3-WP015 — Simplified Assembly / Timeline Preview**
  - **Status:** PASS / CLOSED / MERGED
  - **Issue:** #37
  - **PR:** #38 (Merged into `main` at `35b31c3c41834209fcb9d63ad7ac52e9632d63d2`)

- **P3-WP016 — QC / Approval Pipeline**
  - **Status:** PROPOSED / NOT AUTHORIZED
  - Continuity checks, missing-asset checks, final review and explicit approval semantics.

- **P3-WP017 — Cloud Render Workers**
  - **Status:** PROPOSED / NOT AUTHORIZED
  - Final assembly/render after approval, preserving deterministic job control and auditability.

### Phase 4 — Multi-Output, Export & Core V1 Release

- **P4-WP018 — Multi-Output & Platform Export Presets**
  - **Status:** PROPOSED / NOT AUTHORIZED
  - 16:9 / 9:16 / 1:1 and platform-specific output variants from one master project.

- **P4-WP019 — Project Export/Import Archive Package (.orbis)**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P4-WP020 — End-to-End System Integration, UAT & Core V1 Release**
  - **Status:** PROPOSED / NOT AUTHORIZED

### Post-Core V1 / V1.x

- **Full Operational Integration Gateway (Hermes / n8n / external agents)**
  - **Status:** PROPOSED / POST-CORE V1 / V1.x
  - Architecture readiness remains a V1 design requirement; full operational integration must not block Core V1.

---

## 5. Product Locks Governing Future WPs

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
HUMAN_REVIEW_NOT_HUMAN_MICROMANAGEMENT = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION = CORE_V1_REQUIRED
PROVIDER_INDEPENDENCE = REQUIRED
LOCAL_AI = DISALLOWED
```

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready only until separately authorized:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Future-mode readiness must not silently expand an active WP.
