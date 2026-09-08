# P4-WP020-PRE1 Evidence — Core V1 Release Readiness / Gap Review

> **Status:** EVIDENCE-ONLY REVIEW COMPLETE / CORE V1 NOT RELEASE-READY  
> **Reviewed canonical main:** `e46dcf4c6d935fdc2bd278c64c6c2bcaa0915e8f`  
> **Scope:** repository evidence only; no application-code changes; no paid provider calls; no release mutation

---

## 1. PRE1 Purpose and Boundaries

This document records the P4-WP020-PRE1 evidence-only review required by `P4_WP020_PROPOSAL.md`.

PRE1 answers four questions:

1. Which Core V1 capabilities already have implementation and test evidence?
2. Which required capabilities are only partial, mock-backed, operationally incomplete or absent?
3. Which findings are genuine release blockers versus later UAT evidence needs?
4. What bounded corrective/test work should be proposed next?

PRE1 does **not** authorize or perform corrective implementation.

```text
APPLICATION_CODE_CHANGES = NONE
TEST_CODE_CHANGES = NONE
PAID_PROVIDER_CALLS = NONE
RELEASE_TAG = NONE
CORE_V1_PASS = NOT DECLARED
```

---

## 2. Executive Verdict

The Core V1 control-plane architecture and most production workflow behavior are substantially implemented and covered by unit/integration/product tests. The repository contains real multi-project state, mode-aware orchestration, approvals, locks/history safety, durable video generation jobs, cost controls, assembly, QC, render/export models and `.orbis` portability.

However, PRE1 identifies **four confirmed S1 Core V1 release blockers** that prevent a truthful Core V1 PASS today:

1. **Subtitle generation/export is absent** despite being an explicit Core V1 requirement where applicable.
2. **ImageProvider production generation is mock-only**; runtime keyframe generation defaults to deterministic mock SVG output.
3. **AudioProvider production generation is mock-only**; runtime generated VO/BGM/SFX/Ambience defaults to deterministic mock WAV output.
4. **Cloud Master Render is not operationally runnable in the current container/deployment path**: the production renderer requires FFmpeg, the backend Docker image does not install FFmpeg, and the render-worker module has no runnable worker loop/entrypoint while the compose stack does not start a render worker.

Therefore:

```text
P4-WP020-PRE1 = FINDINGS COMPLETE
CORE_V1_RELEASE_READINESS = BLOCKED
S0_FINDINGS = 0
S1_FINDINGS = 4
NEXT_DEFAULT_GATE = OWNER DECISION ON BOUNDED RELEASE-BLOCKER CORRECTIVE PLAN
LIVE_PAID_UAT = NOT YET APPROPRIATE
```

P4-WP020-A zero-billing E2E remains useful, but it cannot by itself close the four S1 production gaps above.

---

## 3. Canonical 18-Row Acceptance Evidence Matrix

Status legend:

- `EVIDENCE_PRESENT` — source + automated evidence exists; live Owner UAT may still be required before final release.
- `PARTIAL / S1` — substantial implementation exists, but a confirmed required production capability is not release-ready.
- `EVIDENCE_PRESENT / DEPENDENCY_BLOCKED` — feature logic exists but final production execution depends on another S1 blocker.

| # | Core V1 Acceptance Row | PRE1 Status | Repository Evidence / Finding |
| :---: | :--- | :--- | :--- |
| 1 | Open Multi-Project Workspace | **EVIDENCE_PRESENT** | Project CRUD/archive/unarchive/duplicate, dashboard lifecycle, workspace isolation and soft-history behavior exist. `backend/tests/test_workspace_api.py`; `frontend/src/components/dashboard/ProjectDashboard.tsx`; `frontend/src/test/ProjectDashboard.test.tsx`. |
| 2 | Create Project & Ingest References | **EVIDENCE_PRESENT** | Project creation, asset/document upload, document extraction, reference bibles and frontend reference management exist. `backend/tests/test_assets.py`, `test_document_extraction.py`, `test_reference_library.py`; `frontend/src/components/references/ReferencesPanel.tsx`. |
| 3 | Mode-Aware Creative Planning | **EVIDENCE_PRESENT** | STORY/SHORT/LOOP/SCENE are validated; orchestrator tests prove SHORT/SCENE skip Story and LOOP routes directly to shot planning. `backend/app/services/video_modes.py`; `backend/tests/test_production_orchestrator.py`. |
| 4 | Review Story / Concept | **EVIDENCE_PRESENT** | STORY generation, inspection UI, explicit approval and no-artifact/no-stage-advance behavior are tested. `backend/tests/test_story_generation.py`, `test_production_orchestrator.py`; `frontend/src/components/workspace/StoryInspectionModal.tsx`. |
| 5 | Storyboard Review | **EVIDENCE_PRESENT** | Storyboard generation/approval stage exists before downstream generation; frontend Storyboard grid is present. `backend/tests/test_production_orchestrator.py`; `frontend/src/components/storyboard/StoryboardGrid.tsx`. |
| 6 | Detailed Shot Planning | **EVIDENCE_PRESENT** | Mode-aware shot-plan generation and approval exist with shot prompts/configuration. `backend/tests/test_production_orchestrator.py`; shot/project APIs and Storyboard UI. |
| 7 | Reference / Continuity Controls | **EVIDENCE_PRESENT** | Character/location/style/brand references, continuity mapping and lock guards exist. `backend/tests/test_reference_library.py`, `test_hybrid_shots_and_locks.py`, `test_keyframe_pipeline.py`. |
| 8 | Image / Keyframe Generation | **PARTIAL / S1** | Keyframe service, lineage, cost, batch selected/retry/continue and UI orchestration exist, but `ImageProviderFactory` registers only `MockImageProviderAdapter`; default generation produces deterministic SVG blueprints, not a production image-provider result. **GAP-S1-02.** |
| 9 | Video Generation | **EVIDENCE_PRESENT; LIVE UAT PENDING** | Real `ViduProviderAdapter` is registered as default VideoProvider; durable queue, retry/reconciliation/idempotency/cost controls have tests. Live provider proof belongs to separately authorized WP020-LIVE. |
| 10 | Hybrid Shot Import | **EVIDENCE_PRESENT** | AI-generated/imported video/imported image/recorded/stock/mixed shot types and assembly fallbacks are implemented/tested. `backend/tests/test_hybrid_shots_and_locks.py`, `test_assembly_pipeline.py`. |
| 11 | Locks / History / Versioning | **EVIDENCE_PRESENT** | Project/scene/shot deletes are soft archive; lock guards fail closed; story/audio/timeline/QC/render/archive history/version evidence exists; approved timeline edits fork new revision. `test_workspace_api.py`, `test_qc_pipeline.py`, `test_assembly_pipeline.py`, archive tests. |
| 12 | Core V1 Audio Production | **PARTIAL / S1** | Audio plan, VO/BGM/SFX/Ambience data model, generation safety, history, mixing/ducking UI and tests exist, but `AudioProviderFactory` registers only `MockAudioProviderAdapter`, producing deterministic mock WAV output. **GAP-S1-03.** |
| 13 | Selective / Incomplete Recovery | **EVIDENCE_PRESENT** | Generate Selected / Retry Failed / Continue Incomplete, active-job fencing, reconciliation and budget/idempotency tests exist across generation/keyframes. `test_batch_resume.py`, `test_keyframe_pipeline.py`, `test_generation_queue.py`. |
| 14 | Auto Assembly / Simplified Timeline | **EVIDENCE_PRESENT** | Auto assembly, visual fallback, audio placement, trim/reorder/move, locks, checkpoints/restore, blockers and frontend Simple/Advanced timeline exist/tested. `test_assembly_pipeline.py`; `SimpleTimelinePanel.tsx`. |
| 15 | QC / Final Review | **EVIDENCE_PRESENT** | Blockers, warning decisions with mandatory reason, exact-revision QC binding, stale-QC rejection and history are implemented/tested. `backend/tests/test_qc_pipeline.py`; `SimpleQCReview.tsx`. |
| 16 | Human Final Approval | **EVIDENCE_PRESENT** | Final approval fails closed on blockers/stale revision; UI exposes explicit final approval; render submission requires approved timeline. `test_qc_pipeline.py`, `test_render_job.py`; `SimpleQCReview.tsx`. |
| 17 | Cloud Master Render | **PARTIAL / S1** | FFmpeg executor and durable render job/worker class are substantial and tested with mock executor, but current backend Docker image lacks FFmpeg and repository has no runnable render-worker loop/service in compose. **GAP-S1-04.** |
| 18 | Multi-Output Export | **EVIDENCE_PRESENT / DEPENDENCY_BLOCKED** | Five presets, atomic batch authorization, variant idempotency, lineage and frontend Export Presets flow exist/tested for 16:9, 9:16 and 1:1. Actual production output remains dependent on closing GAP-S1-04 render operability. |

---

## 4. Additional Mandatory Core V1 Requirement — Subtitle / Caption Export

`V1_SCOPE.md` defines:

```text
Subtitle Generation / Export where applicable = REQUIRED FOR CORE V1
```

Repository searches performed during PRE1 found no implementation references for:

```text
subtitle
caption
srt
vtt
```

No subtitle/caption domain model, API, frontend control, renderer integration or export sidecar/burn-in path was identified.

### GAP-S1-01 — Subtitle Generation / Export Absent

**Severity:** S1 — Core V1 Release Blocker

**Reason:** this is an explicit V1 feature requirement and is materially relevant to SHORT/social output as well as accessibility/distribution workflows. The requirement must not be silently deleted to make release pass.

**Corrective boundary:** implement the smallest provider-neutral subtitle/caption capability satisfying the locked V1 requirement. Do not expand into a full caption editor or translation platform unless separately authorized.

---

## 5. Confirmed Release-Gap Register

### GAP-S1-01 — Subtitle Generation / Export Absent

- **Severity:** S1
- **Evidence:** Core V1 scope requires subtitle/export; code searches returned no implementation evidence.
- **Impact:** Core V1 acceptance is incomplete; SHORT/platform export cannot truthfully claim required subtitle capability where applicable.
- **PRE1 action:** evidence only; no fix performed.

### GAP-S1-02 — ImageProvider Production Adapter Missing

- **Severity:** S1
- **Evidence:** `ImageProviderFactory` registry contains only `mock_image` / `default -> MockImageProviderAdapter`.
- **Observed runtime behavior:** default keyframe generation executes the mock adapter, which produces deterministic SVG blueprint images.
- **What is already good:** provider-neutral interface, keyframe state machine, continuity mapping, locks, batch operations, cost/idempotency and asset lineage are implemented and tested.
- **Impact:** Core V1 cannot truthfully generate production storyboard/keyframe images through a real cloud ImageProvider.
- **Corrective boundary:** add one real cloud ImageProvider implementation behind the existing adapter/factory/config boundary, preserve mocks for deterministic tests, and add zero-billing contract tests. No provider lock-in in core domain/UI.

### GAP-S1-03 — AudioProvider Production Adapter Missing

- **Severity:** S1
- **Evidence:** `AudioProviderFactory` registry contains only `mock_audio` and defaults to it.
- **Observed runtime behavior:** mock adapter emits deterministic WAV bytes for VO/BGM/SFX/Ambience and simulated costs.
- **What is already good:** audio plan/model, generation modes, history, lock/version safety, budget/idempotency/reconciliation, mix/fade/mute/ducking controls and UI are implemented/tested.
- **Impact:** Core V1 cannot truthfully produce real generated VO/BGM/SFX/Ambience using a production cloud AudioProvider.
- **Corrective boundary:** add the minimum real cloud audio provider implementation(s) needed to satisfy Core V1 audio types behind the existing AudioProvider contract. If one vendor cannot cover all required types, use bounded provider routing; do not redesign the core.

### GAP-S1-04 — Cloud Render Runtime Not Operationally Deployable

- **Severity:** S1
- **Evidence:** `FFmpegRenderExecutor` requires an `ffmpeg` binary and explicitly fails when unavailable. Current `backend/Dockerfile` installs build tools/libpq only and does not install FFmpeg. `CloudRenderWorker` provides `process_one_job()` but no runnable loop/CLI entrypoint. `docker-compose.yml` starts postgres, MinIO and backend only; no render-worker service is started.
- **What is already good:** render job approval binding, idempotency, cost reservation/reconciliation, lease/fencing, retry, output asset lineage and multi-output logic are implemented/tested.
- **Impact:** production Render Master / Export Presets can enqueue jobs but the documented/containerized runtime cannot reliably execute them to MP4.
- **Corrective boundary:** install required render runtime dependencies in the worker image, provide an explicit durable render-worker entrypoint/loop, and wire a worker service/process into the supported deployment path. Do not expand into new render architecture.

---

## 6. Non-Blocker / Verified Findings

### History-delete concern — cleared

Scene and Shot DELETE endpoints are soft-archive operations, guarded by lock checks. Scene archive also archives contained shots. No destructive hard-delete release blocker was confirmed in these normal paths.

### Four Core V1 modes — evidence present

- STORY -> Story -> Storyboard -> Shot Plan
- SHORT -> Storyboard without mandatory Story
- LOOP -> Shot Plan directly
- SCENE -> Storyboard/Scene path without mandatory Story

Automated orchestration tests explicitly verify these branches.

### Video provider boundary — production adapter exists

`ProviderFactory` registers real `ViduProviderAdapter` as the default VideoProvider. PRE1 did not execute paid live Vidu calls; real-provider proof remains a bounded WP020-LIVE activity after zero-billing and S1 corrections are green.

### Assembly / QC / final approval / multi-output / archive — substantial evidence present

These modules are not placeholder-only. They have backend implementations, API/UI surfaces and integration/regression tests. Their final release status still requires zero-billing E2E plus Owner UAT.

---

## 7. `.orbis` Portability Evidence

P4-WP019 remains accepted and PRE1 found no regression evidence requiring it to be reopened.

Existing archive tests cover at least:

- ZIP/path traversal/absolute path/forbidden extension/decompression-bomb safety;
- canonical JSON/checksum trust root and tamper detection;
- secret stripping;
- FULL_SELF_CONTAINED export;
- missing asset fail-closed behavior;
- CLONE UUID/FK remap and source lineage;
- RESTORE collision fail-closed behavior;
- graph/asset preflight;
- historical GenerationJob/RenderJob/UsageLedger preservation and execution/budget fencing.

WP020-A should add one integrated round-trip scenario binding archive behavior to the broader E2E test fixture rather than reopening the archive implementation design.

---

## 8. UAT / Test Environment Prerequisites

Before Owner live UAT, the project needs a documented runnable environment that provides:

1. PostgreSQL.
2. S3-compatible object storage / MinIO.
3. Backend API.
4. Frontend browser app (`npm run dev`/approved built serving path).
5. Generation worker (`python -m app.services.generation_worker`).
6. A corrected render worker process/entrypoint with FFmpeg installed.
7. Real Creative provider credentials only for approved live tests.
8. Real Vidu credentials only for approved live tests.
9. Real ImageProvider configuration after GAP-S1-02 corrective.
10. Real AudioProvider configuration after GAP-S1-03 corrective.
11. Dedicated UAT project/data with a hard budget cap.
12. No production secrets in repository, evidence files, archives or screenshots.

The current compose file is useful for development infrastructure but is not yet a one-command complete browser+workers production/UAT stack.

---

## 9. WP020-A Zero-Billing E2E Recommendation

After the Owner accepts this PRE1 evidence, create a bounded WP020-A scope to add system-level tests using fakes/mocks only.

Recommended minimum scenarios:

1. Deep STORY flow through story -> storyboard -> shot plan -> mock keyframes -> mock video completion -> mock audio -> assembly -> QC -> approval -> mock render -> multi-output.
2. SHORT / LOOP / SCENE smoke paths proving no invalid Story dependency.
3. Partial failure/retry/reconciliation/idempotency scenario.
4. Multi-project isolation scenario.
5. Lock/history/version preservation scenario.
6. `.orbis` FULL_SELF_CONTAINED export -> CLONE import -> new live-work eligibility/historical fencing scenario.
7. Render/export worker contract test using the production worker boundary with a fake executor.
8. Subtitle behavior tests only after GAP-S1-01 corrective contract is separately authorized and implemented.

WP020-A must not use paid provider calls.

---

## 10. Corrective Ordering Recommendation

To minimize rework and paid UAT waste:

```text
1. Accept PRE1 evidence
2. Authorize bounded S1 corrective design/implementation
   a. Subtitle minimum V1 capability
   b. Real ImageProvider
   c. Real AudioProvider
   d. Render runtime/worker operability
3. Independent review exact corrective HEAD(s)
4. Run/complete WP020-A zero-billing E2E against corrected system
5. Fix only new proven release blockers
6. Obtain separate Owner authorization for WP020-LIVE with hard budget cap
7. Owner live UAT
8. P4-WP020-CLOSE final independent review
9. Owner Core V1 release decision / tag
```

The S1 correctives may be split into small reviewable subpackages to avoid one oversized corrective PR.

---

## 11. PRE1 Closure Criteria

P4-WP020-PRE1 is complete when this evidence report is independently reviewed and accepted by the Owner.

Acceptance of PRE1 means only:

```text
EVIDENCE/GAP CLASSIFICATION ACCEPTED
```

It does **not** mean:

```text
P4-WP020 IMPLEMENTATION AUTHORIZED
S1 CORRECTIVES AUTHORIZED
WP020-A AUTHORIZED
PAID LIVE UAT AUTHORIZED
CORE V1 PASS
RELEASE TAG AUTHORIZED
```

Every subsequent mutation gate remains separately controlled by the Owner.
