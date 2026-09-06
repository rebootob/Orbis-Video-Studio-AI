# Mandatory Session Startup Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/START_HERE.md`](project-docs/00_CONTROL/START_HERE.md)

---

## 1. Startup Reading Sequence

Every new chat session, AI agent or execution engine MUST read in this order before doing project work:

1. `project-docs/00_CONTROL/START_HERE.md`
2. `project-docs/00_CONTROL/CURRENT_STATE.md`
3. `project-docs/00_CONTROL/ACTIVE_TASK.md`
4. `project-docs/00_CONTROL/DOCUMENT_INDEX.md`
5. `project-docs/00_CONTROL/CHAT_HANDOFF.md`
6. Routed domain documents relevant to the active task only

For work touching product flow, project creation, Story/Storyboard/Shot behavior, UI/UX, generation orchestration, cost gates, audio, timeline, QC, render or export, also read:

- `project-docs/30_PRODUCT/PRODUCT_VISION.md`
- `project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md`
- `project-docs/30_PRODUCT/USER_WORKFLOW.md`
- `project-docs/30_PRODUCT/V1_SCOPE.md`

---

## 2. Repository Truth

- Fresh-fetch live `main` HEAD before stating status.
- If an active PR exists, fresh-fetch its exact HEAD and CI status too.
- Live repository truth newer than documentation is authoritative.
- Historical handoff/base SHAs are context, not a reason to overwrite newer repository truth.
- Closed WPs must not be reopened without a proven regression.

---

## 3. Bounded Execution

No execution engine may exceed the currently authorized Work Package.

If `ACTIVE_WORK_PACKAGE = NONE`, application-code implementation is prohibited until the Owner explicitly authorizes a new WP.

If a WP is in `CHANGES REQUIRED`, corrective work stays on the same authorized branch/PR unless the Owner explicitly changes that contract.

Do not auto-start the next WP after a merge.

---

## 4. Authority Model

```text
Project Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = low-credit bounded Execution Plane when explicitly authorized
Codex = STOP by default
Claude Code = STOP
```

ChatGPT may manage GitHub Issues, PR metadata/comments and documentation branches where permitted. Direct `main` writes and merges remain governed by Owner approval.

---

## 5. Product Control Rules

Orbis is an AI Video Production Orchestrator / Production Control Plane, not a foundation-model development project and not a Premiere-class NLE clone.

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Owner locks that must be preserved in relevant work:

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUTOMATION_FIRST = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION = CORE_V1_REQUIRED
LOCAL_AI = DISALLOWED
VENDOR_LOCK_IN = DISALLOWED
```

The user must be able to review creative structure before expensive downstream generation. Guidance must assist the user without trapping them in a rigid wizard.

---

## 6. Immediate Startup Actions

1. Fetch current `main` and active feature branch/PR if one exists.
2. Read `CURRENT_STATE.md` and `ACTIVE_TASK.md`.
3. Confirm exact authorization and review gate.
4. Read only directly relevant routed documents and the active Issue/PR contract.
5. Do not repeat completed work.
6. Do not merge or start another WP without Owner authorization.

The local Antigravity watcher/dispatcher is PAUSED and is not a production execution dependency.
