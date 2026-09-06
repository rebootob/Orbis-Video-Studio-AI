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

For any work touching project creation, Story/Script routing, Scene/Shot behavior, workflow, UI, generation orchestration, timeline or export logic, also read:

`project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md`

---

## 2. Repository Truth

- Fresh-fetch live Git/GitHub HEAD before stating status.
- Live repository truth newer than documentation is authoritative.
- Historical handoff/base SHAs are context, not a reason to overwrite newer repository truth.
- Closed WPs must not be reopened without a proven regression.

---

## 3. Bounded Execution

No execution engine may exceed the currently authorized Work Package.

If `ACTIVE_WORK_PACKAGE = NONE`, application-code implementation is prohibited until the Owner explicitly authorizes a new WP.

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

ChatGPT may manage GitHub Issues, PR metadata/comments and documentation branches where permitted, but direct `main` writes and merges remain governed by Owner approval.

---

## 5. Multi-Mode Rule

Orbis is a multi-mode video production platform.

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Do not assume Story or Script is mandatory for every Project.

Architecture-ready future modes:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Architecture readiness does not authorize implementation.

---

## 6. Immediate Startup Actions

1. Fetch current `main` and active feature branch/PR if one exists.
2. Read `CURRENT_STATE.md` and `ACTIVE_TASK.md`.
3. Confirm whether any WP is actually authorized.
4. Read only directly relevant routed documents.
5. Do not repeat completed work.
6. Do not merge or start another WP without Owner authorization.

The local Antigravity watcher/dispatcher is currently PAUSED and is not a production execution dependency.
