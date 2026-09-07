# Chat Session Handoff

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

Repository: `rebootob/Orbis-Video-Studio-AI`

Canonical branch: `main`

Live repository truth newer than this handoff is authoritative.

---

## Completed Work

```text
P0-WP001 = PASS / CLOSED / MERGED
P1-WP002 = PASS / CLOSED / MERGED
P1-WP003 = PASS / CLOSED / MERGED
P1-WP004 = PASS / CLOSED / MERGED
P1-WP005 = PASS / CLOSED / MERGED
P2-WP006 = PASS / CLOSED / MERGED
P2-WP007 = PASS / CLOSED / MERGED
P2-WP008 = PASS / CLOSED / MERGED
P2-WP009 = PASS / CLOSED / MERGED
P2-WP010 = PASS / CLOSED / MERGED
P2-WP011 = PASS / CLOSED / MERGED
P2-WP012 = PASS / CLOSED / MERGED
P2-WP013 = PASS / CLOSED / MERGED
P3-WP014 = PASS / CLOSED / MERGED
P3-WP015 = PASS / CLOSED / MERGED
```

Key reviewed/merge truth:

```text
WP007 reviewed HEAD: 5a03d4d7f56ac8ae39a78914276610c0512da78b
WP007 merge: 9cb098dea7fc2948b023ad48163c729f566573a7

WP008 reviewed HEAD: a2c3f3d4e80a0b0aedb58fba5a04a436c9e88797
WP008 merge: a360c3b38d1d962f9f3c5f6412e3107e90fae7db

WP009 reviewed HEAD: 250df0bb6df24577e2e1f14c7ada3d0dbbaf75fa
WP009 merge: 9f094a5cbe9a4faeb5741231d0a819da0da283c1

WP010 reviewed HEAD: 0f0a16fa95c8110bc8ab7a0c52d45351eaa82182
WP010 merge: 639e61fb69b6abee8598074add458035db906ceb
WP010 PR: #25 (MERGED / CLOSED)
WP010 Final Review: PASS / READY TO MERGE (Review ID 5124386306)

WP011 reviewed HEAD: b2f349adb6d5704fa1aadfb19e06644b40a37080
WP011 merge / main base HEAD: 643614b089a295ea96be179e470707609cbe4b53
WP011 PR: #29 (MERGED / CLOSED)
WP011 Final Review: PASS / READY TO MERGE (Review ID 5124729394)

WP012 Issue: #31
WP012 PR: #32 (MERGED / CLOSED)
WP012 Reviewed HEAD: a781926bbf607cad1b992d089920be6f094e41c9
WP012 Merge commit: cdd79aaa80eaefa8be6c4e4894cb40db0b097a60
WP012 Final Review: PASS / READY TO MERGE (Review ID 5125098674)

WP013 Issue: #33
WP013 PR: #34 (MERGED / CLOSED)
WP013 Reviewed HEAD: f9fd46b917390224a5ab58bad0d3be238edbd7b3
WP013 Merge commit: c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd
WP013 Status: PASS / CLOSED / MERGED

WP014 Issue: #35
WP014 PR: #36 (MERGED / CLOSED)
WP014 Reviewed HEAD: cbbcea8c9a84bd9c08222dabf95d1788b2d3945e
WP014 Merge commit: f50e2568d197b3c4bab5e4303f31af817db6e1bf
WP014 Final Review: PASS / READY TO MERGE (Review ID 5125802846)
WP014 Status: PASS / CLOSED / MERGED

WP015 Issue: #37
WP015 PR: #38 (MERGED / CLOSED)
WP015 Reviewed HEAD: 640212f71182ba3f6a5024a442beb363868eabc1
WP015 Merge commit: 35b31c3c41834209fcb9d63ad7ac52e9632d63d2
WP015 Final Review: PASS / READY TO MERGE (Review ID 5127082342)
WP015 Status: PASS / CLOSED / MERGED
```

---

## Current Gate

```text
ACTIVE WORK PACKAGE = NONE
STATUS = POST-WP015 / READY FOR OWNER NEXT-WP AUTHORIZATION
BRANCH = main
ANTIGRAVITY = STOP / NONE (bounded low-credit Execution Plane when authorized)
CODEX = STOP
CLAUDE_CODE = STOP
```

No active Work Package implementation. Await explicit Owner authorization before starting WP016.
Do NOT merge without Owner approval.
Do NOT start or implement WP016.

### Performance & Scalability Guardrails Delivered in WP011

`PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE`

The following guardrails were delivered and verified in P2-WP011:
- Keyset-based pagination `(created_at, id)` eliminating unbounded in-memory candidate materialization
- Streaming execution in chunks of $\le 50$ (`EXECUTE_CHUNK_SIZE = 50`)
- Set-based DB queries in candidate evaluation and batch run listings (zero N+1 queries)
- Reversible Alembic migration `011_batch_resume_runs_and_indexes.py` with targeted indexes
- Bounded memory retention for created jobs (`MAX_COMPATIBILITY_RETURNED_JOBS = 100`, `accumulate_jobs=False` on canonical resume)
- Fail-closed legacy `/jobs/batch` execution boundary ($\le 100$) with atomic rollback on capacity breach

### ComfyUI / Cloud GPU Future Planning Note

Preserve provider-neutral architecture.

ComfyUI + Cloud GPU is a FUTURE provider/execution candidate.

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

Status:
```text
PROPOSED / NOT AUTHORIZED / NOT IMPLEMENTED
```

Important product locks:
- Vidu remains the only currently implemented registered VideoProvider.
- ComfyUI must not replace the provider abstraction.
- Do not add ComfyUI source code in this docs sync.
- Do not select a GPU cloud vendor yet.
- `LOCAL_AI` remains disallowed.
- Cloud-hosted ComfyUI is compatible with `CLOUD_AI` direction.

### Future-Performance Backlog Note (Preserved)

- server-side Project pagination
- Asset/Job history pagination
- media thumbnail/lazy-loading
- streaming/multipart large-file upload
- media preview streaming
- frontend virtualization where needed

---

## Owner-Locked Product Direction

Orbis is not intended to recreate foundation AI models. It is an **AI Video Production Orchestrator / Production Control Plane** that coordinates best-of-breed Creative, Image, Video and Audio providers behind adapters.

Provider-neutral direction:

```text
CreativeProvider
  -> OpenAI / Gemini / future

ImageProvider
  -> Gemini Image / OpenAI Image / future

VideoProvider
  -> Vidu / Veo / future

AudioProvider
  -> TTS / music / SFX / future
```

The Orbis-owned value is production orchestration and control: Projects, modes, references, Story/Scene/Shot structure, approvals, history/version lineage, locks, durable queue/retry/recovery, cost/budget, QC, assembly and export.

### Core V1 Modes

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready later:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

### Multi-Project / History Locks

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
```

### Automation-First Locks

```text
AUTOMATION_FIRST = REQUIRED
AUTO_STORYBOARD = REQUIRED
AUTO_SHOT_PLANNING = REQUIRED
AUTO_PROMPT_GENERATION = REQUIRED
BATCH_GENERATION = REQUIRED
HUMAN_REVIEW_NOT_HUMAN_MICROMANAGEMENT = REQUIRED
```

Target flow:

```text
Brief / References
-> Story
-> Review / Approve
-> Storyboard
-> Review / Approve
-> Detailed Shot Plan + Prompts
-> Review / Approve
-> Images / Keyframes
-> Continuity QC
-> Review / Approve
-> Video Generation
-> VO / BGM / SFX / Ambience
-> Auto Assembly
-> Final QC
-> Final Approval
-> Render / Export
```

The user must be able to stop at Story or Storyboard before generating detailed shots/images/video and consuming expensive provider credits.

### Guided Flexibility

The UI should always suggest a sensible next action, use safe defaults and progressive disclosure, avoid dead ends, explain failures in plain language and preserve Advanced controls without trapping the user in a rigid wizard.

### Audio

Audio Production is Core V1 and must include VO, BGM, SFX, ambience, basic mixing/fades/mute/volume and basic auto-ducking. Advanced DAW-style editing is outside V1.

---

## Roles

```text
Owner = final human authority / UAT / authorization of next WP
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = STOP / NONE (bounded low-credit Execution Plane when explicitly authorized)
Codex = STOP by default
Claude Code = STOP
```

The local Antigravity watcher/dispatcher is PAUSED and must not be treated as a production dependency.

---

## Mandatory Resume Procedure

1. Fresh-fetch current `main` HEAD (`35b31c3c41834209fcb9d63ad7ac52e9632d63d2`).
2. Read `START_HERE.md`.
3. Read `CURRENT_STATE.md`.
4. Read `ACTIVE_TASK.md`.
5. Read `DOCUMENT_INDEX.md`.
6. Read this handoff.
7. Confirm `ACTIVE_WORK_PACKAGE = NONE` and wait for explicit Owner authorization before starting implementation.
8. Do not repeat closed work.
9. Do not start WP016 automatically. P3-WP016 remains PROPOSED / NOT AUTHORIZED.
