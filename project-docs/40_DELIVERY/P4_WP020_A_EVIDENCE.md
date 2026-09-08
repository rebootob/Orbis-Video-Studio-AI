# P4-WP020-A — Deterministic Zero-Billing E2E / Integration Evidence

Status: **EVIDENCE EXECUTION IN PROGRESS**

Base `main` at authorization: `b684c27416138543d6e875244336eb4626c8401d`

## 1. Contract

This stage is evidence-first and zero-billing.

- No live/paid Creative, Image, Video, or Audio provider call is authorized.
- Mock/fake providers and deterministic local test doubles are required.
- Production changes are not allowed unless they are strictly necessary testability fixes.
- New proven Core V1 release blockers are recorded and STOP for a separately bounded corrective decision.
- Passing CI does not mean Core V1 release-ready if an acceptance scenario records a blocker.

## 2. New integrated evidence

`backend/tests/test_wp020a_zero_billing_e2e.py` adds cross-module evidence that complements the existing focused suites:

1. Deep STORY creative path through Story -> Storyboard -> Shot Plan -> Keyframes -> Video GenerationJob completion -> Final Review transition -> Assembly truth.
2. Downstream production path using a deliberately materialized zero-billing VIDEO fixture: Audio -> Auto Mix -> Assembly -> Thai Subtitle/SRT -> QC -> Human Final Approval -> Master Render -> 16:9/9:16/1:1 exports -> FULL_SELF_CONTAINED `.orbis` CLONE and historical fencing.
3. STORY/SHORT/LOOP/SCENE entry routing and multi-project isolation.
4. An autouse external-HTTP denial guard so an accidental paid/live provider request fails the WP020-A test immediately.

Existing focused suites remain authoritative for concurrency, retry, reconciliation, locks/history, archive security, runtime render smoke, provider adapters, and browser UI components.

## 3. E2E scenario matrix

| ID | Scenario | Evidence | WP020-A result |
|---|---|---|---|
| E2E-01 | STORY deep full path | `test_wp020a_zero_billing_e2e.py::test_e2e_01_story_provider_completion_exposes_video_asset_materialization_gap` + existing orchestrator/keyframe/queue suites | **BLOCKED — S1-A01** |
| E2E-02 | SHORT path / 9:16 / subtitle | mode-routing test + downstream SHORT fixture + subtitle/SRT + 9:16 export | **PASS, except common S1-A01 video materialization dependency for generated-video path** |
| E2E-03 | LOOP path | mode-routing test + existing `test_loop_mode_shot_plan` | **PASS (bounded mode smoke)** |
| E2E-04 | SCENE path | mode-routing test + existing `test_scene_mode_skips_story` | **PASS (bounded mode smoke)** |
| E2E-05 | Multi-project isolation | mode/isolation test + workspace/assembly/QC ownership tests | **PASS** |
| E2E-06 | Approval / cost gate | existing orchestrator, cost ledger, R3/R4 provider-cost tests | **PASS** |
| E2E-07 | Batch / selective recovery | existing `test_batch_resume.py`, keyframe and audio batch tests | **PASS** |
| E2E-08 | Provider failure / reconciliation / idempotency | existing `test_generation_queue.py`, render and provider tests | **PASS** |
| E2E-09 | Locks / history / versioning | existing lock, assembly, QC, archive history suites | **PASS** |
| E2E-10 | Audio integration | downstream integrated test using `mock_audio` across generation/storage/mix/render | **PASS** |
| E2E-11 | QC / final human approval | downstream integrated test + `test_qc_pipeline.py` | **PASS** |
| E2E-12 | Multi-output 16:9 / 9:16 / 1:1 | downstream integrated test executes 3 export jobs through `CloudRenderWorker` + `MockRenderExecutor` | **PASS** |
| E2E-13 | `.orbis` export/validate/CLONE/new truth; RESTORE collision | downstream integrated CLONE + existing archive roundtrip/RESTORE collision suite | **PASS** |
| E2E-14 | Imported historical fencing | downstream integrated archive clone + existing historical job/ledger fencing suite | **PASS** |
| E2E-15 | Security / secret safety | HTTP denial guard + archive security/secret stripping + provider response allowlist suites | **PASS** |
| E2E-16 | Browser/cloud-first usability | frontend lint/typecheck/build/tests + render runtime smoke/compose evidence | **EVIDENCE PRESENT; Owner browser UAT remains WP020-LIVE** |

## 4. New release blocker — S1-A01

### S1-A01 — Completed VideoProvider output is not materialized into durable Orbis VIDEO Asset / Shot truth

**Observed cross-module behavior**

1. A VIDEO `GenerationJob` can be claimed and completed with a provider result containing `video_url` and cost evidence.
2. `JobDispatchService` persists the job as `COMPLETED` and settles cost.
3. The orchestration readiness calculation treats a completed VIDEO job as a production-ready Shot and allows `TRANSITION_TO_FINAL_REVIEW`.
4. The completion path does not materialize the provider output into Orbis object storage as a `VIDEO` Asset and does not bind that Asset to `Shot.source_asset_id`.
5. `AssemblyService` therefore cannot consume the generated video as VIDEO truth. When a keyframe exists, assembly falls back to the KEYFRAME; without a fallback it becomes MISSING.

**Why this is S1**

Core V1 requires generated video shots to flow into assembly/QC/render. A provider-completed job that never becomes a durable project Asset breaks the STORY deep E2E and can allow workflow state to advance while final assembly does not contain the generated video.

**Bounded corrective boundary**

A later separately authorized corrective should do only the minimum needed to:

- safely retrieve a completed provider video output;
- persist it in Orbis object storage;
- create immutable/auditable `VIDEO` Asset lineage;
- bind the exact completed generation result to the Shot without silently overwriting historical assets;
- make production-readiness require durable usable output truth rather than job status alone;
- preserve retry/reconciliation/idempotency and cost fencing;
- prove provider URL/download failure and ambiguous post-provider persistence fail closed;
- re-run WP020-A E2E-01 and affected regression gates.

No such production corrective is authorized by WP020-A itself.

## 5. Release readiness consequence

Until exact-head CI confirms the evidence branch, the stage remains `IN PROGRESS`.

Expected decision if the integrated evidence remains as observed:

```text
P4-WP020-A = FINDINGS COMPLETE / PASS AS EVIDENCE STAGE
CORE_V1_RELEASE_READINESS = BLOCKED
OPEN_S0 = 0
OPEN_S1 = 1 (S1-A01)
LIVE_PAID_UAT = NOT YET APPROPRIATE
```

WP020-LIVE must not start while S1-A01 remains open.
