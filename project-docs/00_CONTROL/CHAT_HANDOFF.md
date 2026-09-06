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
```

Key reviewed/merge truth:

```text
WP007 reviewed HEAD: 5a03d4d7f56ac8ae39a78914276610c0512da78b
WP007 merge: 9cb098dea7fc2948b023ad48163c729f566573a7

WP008 reviewed HEAD: a2c3f3d4e80a0b0aedb58fba5a04a436c9e88797
WP008 merge: a360c3b38d1d962f9f3c5f6412e3107e90fae7db

WP009 reviewed HEAD: 250df0bb6df24577e2e1f14c7ada3d0dbbaf75fa
WP009 merge / current documented main HEAD: 9f094a5cbe9a4faeb5741231d0a819da0da283c1
```

---

## Current Gate

```text
ACTIVE WORK PACKAGE = P2-WP010
ISSUE = #24
PR = #25
BRANCH = ai/p2-wp010-mode-aware-web-workspace
LAST REVIEWED HEAD = 9fb1d6fdeee8ec14ffcf2063133fca5263754640
STATUS = CORRECTIVE PUSHED / WAITING CHATGPT INDEPENDENT RE-REVIEW
NEXT ALLOWED ACTION = ChatGPT independent re-review of PR #25
```

Do not merge PR #25 yet. Do not start WP011.

Antigravity corrective commit has been pushed addressing the 8 review blockers (soft-archive retention, staged mode-aware workflow, truthful readiness copy, provider-neutral routing, multi-project metrics, unsaved edit protection, and upload error surfacing). Antigravity is STOPPED waiting for ChatGPT independent re-review.

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
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane when explicitly authorized
Codex = STOP by default
Claude Code = STOP
```

The local Antigravity watcher/dispatcher is PAUSED and must not be treated as a production dependency.

---

## Mandatory Resume Procedure

1. Fresh-fetch current `main` HEAD and PR #25 HEAD.
2. Read `START_HERE.md`.
3. Read `CURRENT_STATE.md`.
4. Read `ACTIVE_TASK.md`.
5. Read `DOCUMENT_INDEX.md`.
6. Read this handoff.
7. Read `VIDEO_PRODUCTION_MODES.md`, `PRODUCT_VISION.md`, `USER_WORKFLOW.md` and only other documents directly relevant to the active task.
8. Read Issue #24 plus all Product Lock / UX addendum comments and the latest PR #25 review/corrective comment.
9. Do not repeat closed work.
10. Do not start the next WP or merge without explicit Owner authorization.
