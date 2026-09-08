# P4-WP020-A — Deterministic Zero-Billing E2E / Integration Evidence

Status: **FINDINGS COMPLETE / PASS AS EVIDENCE STAGE**

Base `main` at authorization: `b684c27416138543d6e875244336eb4626c8401d`

Verification checkpoint before this final docs-only status sync: `0d9b34f3b177fe105414dc2c28a201af08141e7f` — Backend Tests #119 PASS; Frontend Tests #111 PASS.

## 1. Contract

This stage is evidence-first and zero-billing.

- No live/paid Creative, Image, Video, or Audio provider call is authorized.
- Mock/fake providers and deterministic local test doubles are required.
- Production changes are not allowed unless they are strictly necessary testability fixes.
- New proven Core V1 release blockers are recorded and STOP for separately bounded corrective decisions.
- Green CI does not mean release-ready when an acceptance row intentionally records current blocked truth.

## 2. New integrated evidence

`backend/tests/test_wp020a_zero_billing_e2e.py` crosses boundaries that the focused suites test independently:

1. STORY -> Storyboard -> Shot Plan -> Keyframes -> VIDEO GenerationJobs -> fake provider completion -> Final Review -> Assembly.
2. A deliberately materialized zero-billing VIDEO fixture -> Audio -> Auto Mix -> Assembly -> Thai Subtitle/SRT -> QC -> Human Approval -> Master Render -> 16:9/9:16/1:1 export -> attempted FULL_SELF_CONTAINED archive.
3. STORY/SHORT/LOOP/SCENE entry routing and multi-project isolation.
4. External HTTP is denied by an autouse fixture so accidental provider/network use fails immediately.

The existing focused suites remain authoritative for retry/reconciliation, locks/history, archive security, render runtime, provider adapter contracts, and frontend surfaces.

## 3. Scenario matrix

| ID | Scenario | WP020-A evidence result |
|---|---|---|
| E2E-01 | STORY deep full path | **BLOCKED — S1-A01 + S1-A03** |
| E2E-02 | SHORT / 9:16 / subtitle | **PASS downstream and mode smoke; generated-video path shares S1-A01** |
| E2E-03 | LOOP path | **PASS bounded mode smoke** |
| E2E-04 | SCENE path | **PASS bounded mode smoke** |
| E2E-05 | Multi-project isolation | **PASS** |
| E2E-06 | Approval / cost gate | **PASS via existing orchestrator/cost/provider suites** |
| E2E-07 | Batch / selective recovery | **PASS via existing batch/keyframe/audio suites** |
| E2E-08 | Provider failure / reconciliation / idempotency | **PASS via existing generation/render/provider suites** |
| E2E-09 | Locks / history / versioning | **PASS via existing lock/assembly/QC/archive suites** |
| E2E-10 | Audio integration | **PASS integrated with `mock_audio`, storage and render** |
| E2E-11 | QC / final human approval | **PASS integrated** |
| E2E-12 | Multi-output 16:9 / 9:16 / 1:1 | **PASS integrated through `CloudRenderWorker` + `MockRenderExecutor`** |
| E2E-13 | `.orbis` FULL_SELF_CONTAINED roundtrip | **BLOCKED — S1-A02** |
| E2E-14 | Imported historical fencing | **Focused evidence remains PASS; integrated roundtrip cannot reach import while S1-A02 is open** |
| E2E-15 | Security / secret safety | **PASS via HTTP denial + archive/provider security suites** |
| E2E-16 | Browser/cloud-first usability | **EVIDENCE PRESENT; Owner browser UAT remains WP020-LIVE** |

## 4. S1-A01 — Completed VIDEO job is not materialized into durable Orbis VIDEO Asset / Shot truth

A VIDEO `GenerationJob` can complete with provider `video_url` and settled cost, and orchestration then counts the Shot as production-ready. The completion path does not persist that generated video into Orbis object storage as a `VIDEO` Asset or bind it to `Shot.source_asset_id`.

**Severity: S1.** Generated video must become durable project truth before Assembly/QC/Render.

Bounded corrective boundary:
- retrieve completed provider output safely;
- persist durable object-storage media and immutable/auditable VIDEO Asset lineage;
- bind the exact completed GenerationJob output to the Shot without destroying prior history;
- make production-readiness depend on durable usable output, not job status alone;
- preserve retry/reconciliation/idempotency/cost fencing;
- fail closed on provider download or post-provider persistence uncertainty;
- rerun E2E-01 and affected regressions.

## 5. S1-A02 — FULL_SELF_CONTAINED export fails on real AudioClip history

The integrated downstream flow successfully reaches:

`Audio -> Assembly -> Subtitle -> QC -> Approval -> Master Render -> Multi-output`

The subsequent `.orbis` export fails in `ProjectExportService` because the exporter queries `AudioClipHistory.audio_clip_id` while the canonical model field is `clip_id`. Python raises `AttributeError` before archive construction completes.

**Severity: S1.** Core V1 FULL_SELF_CONTAINED portability must work after normal Audio history exists.

Bounded corrective boundary:
- align archive AudioClipHistory query/serialization/import references with the canonical model field;
- prove export/validate/CLONE and RESTORE collision with AudioPlan/AudioClip history present;
- preserve exact history and imported historical job/ledger fencing;
- verify subtitle portable state after corrected CLONE;
- run archive/security regressions and E2E-13/14 again.

## 6. S1-A03 — STORY-linked scenes are omitted by Assembly project-scene query

The canonical STORY flow creates scenes connected through `Story.project_id` / `Scene.story_id`. The zero-billing deep path proves these STORY scenes and Shots exist, but `AssemblyService.auto_assemble_timeline()` queries only `Scene.project_id == project_id` when building the assembly graph. In the STORY fixture that returns no scenes, producing an active timeline with **0 Shot placements**.

This is independent of S1-A01: even if generated video output were materialized correctly, Assembly would still omit the STORY graph when the scene is represented through Story lineage rather than direct `Scene.project_id`.

**Severity: S1.** STORY is the required deep Core V1 path and cannot truthfully reach Assembly/QC/Render with zero placements.

Bounded corrective boundary:
- resolve canonical active scenes using the same project-or-Story lineage rule already used by orchestration/queue services;
- exclude archived scenes/shots consistently;
- preserve manual assembly ordering/moves/locks/history;
- add direct-project and Story-linked regression fixtures;
- prove corrected STORY Assembly contains the expected placements;
- rerun E2E-01 plus assembly/QC/subtitle/render regressions.

## 7. Evidence-stage verdict

```text
P4-WP020-A = FINDINGS COMPLETE / PASS AS EVIDENCE STAGE
CORE_V1_RELEASE_READINESS = BLOCKED
OPEN_S0 = 0
OPEN_S1 = 3 (S1-A01, S1-A02, S1-A03)
LIVE_PAID_UAT = NOT YET APPROPRIATE
```

WP020-LIVE must not start until all three blockers are corrected and the affected zero-billing E2E scenarios pass.
