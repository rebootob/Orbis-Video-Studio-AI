# P4-WP020-A — Deterministic Zero-Billing E2E / Integration Evidence

Status: **EVIDENCE EXECUTION IN PROGRESS**

Base `main` at authorization: `b684c27416138543d6e875244336eb4626c8401d`

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
| E2E-01 | STORY deep full path | **BLOCKED — S1-A01** |
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

### Observed behavior

1. A VIDEO `GenerationJob` completes with a provider identity, `video_url`, and cost evidence.
2. Queue state becomes `COMPLETED` and cost settlement completes.
3. Orchestration counts that completed job as a production-ready Shot and allows `TRANSITION_TO_FINAL_REVIEW`.
4. No completed-provider path materializes the video into Orbis object storage as a `VIDEO` Asset or binds it to `Shot.source_asset_id`.
5. Assembly therefore cannot consume the generated video. With a keyframe it falls back to `KEYFRAME`; without a fallback it would be missing.

### Severity

**S1 Core V1 release blocker.** Generated video must become durable project truth before Assembly/QC/Render.

### Bounded corrective boundary

A separately authorized corrective should only:

- safely retrieve completed provider video output;
- persist it in Orbis object storage;
- create auditable `VIDEO` Asset lineage tied to the exact GenerationJob/Shot;
- avoid destructive overwrite of prior video history;
- change production-readiness to require durable usable output, not job status alone;
- preserve idempotency/retry/reconciliation/cost fencing;
- fail closed for provider download or post-provider persistence uncertainty;
- re-run E2E-01 and affected regressions.

## 5. S1-A02 — FULL_SELF_CONTAINED export fails on real AudioClip history

### Observed behavior

The downstream integration successfully reaches:

`Audio -> Assembly -> Subtitle -> QC -> Approval -> Master Render -> Multi-output`

but the subsequent `.orbis` export fails inside `ProjectExportService` when audio history exists:

- exporter queries `AudioClipHistory.audio_clip_id`;
- the current AudioClipHistory model exposes the canonical relation field as `clip_id`;
- Python raises `AttributeError` before archive construction can complete.

This gap was not exposed by the earlier archive tests because those fixtures did not bind the full Core V1 Audio history into an integrated export path.

### Severity

**S1 Core V1 release blocker.** `.orbis` FULL_SELF_CONTAINED portability is required for Core V1 and must work after normal audio production/history has occurred.

### Bounded corrective boundary

A separately authorized corrective should only:

- align archive AudioClipHistory query/serialization/import references with the actual canonical model field;
- prove export/validate/CLONE and RESTORE-collision behavior with AudioPlan/AudioClip history present;
- preserve history exactly and keep imported historical jobs/ledgers fenced;
- verify subtitle portable mirror survives the corrected integrated CLONE;
- run archive/security regressions and WP020-A E2E-13/14 again.

No archive production corrective is authorized by WP020-A itself.

## 6. Current release consequence

If exact-head CI passes while intentionally asserting these current blocked truths, the expected evidence-stage verdict is:

```text
P4-WP020-A = FINDINGS COMPLETE / PASS AS EVIDENCE STAGE
CORE_V1_RELEASE_READINESS = BLOCKED
OPEN_S0 = 0
OPEN_S1 = 2 (S1-A01, S1-A02)
LIVE_PAID_UAT = NOT YET APPROPRIATE
```

WP020-LIVE must not start until both blockers are corrected and the affected zero-billing E2E scenarios pass.
