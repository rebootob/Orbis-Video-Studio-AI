# Mandatory Session Startup Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/START_HERE.md`](project-docs/00_CONTROL/START_HERE.md)

---

## 1. Startup Reading Sequence

Every new ChatGPT session, AI agent, or execution engine MUST do this before project work:

1. Read root [`AGENTS.md`](../../AGENTS.md).
2. Fresh-fetch live `main` and any active feature branch / PR.
3. Read `project-docs/00_CONTROL/START_HERE.md`.
4. Read `project-docs/00_CONTROL/CURRENT_STATE.md`.
5. Read `project-docs/00_CONTROL/ACTIVE_TASK.md`.
6. Read `project-docs/00_CONTROL/DOCUMENT_INDEX.md`.
7. Read `project-docs/00_CONTROL/CHAT_HANDOFF.md`.
8. Read the exact active GitHub Issue / WP contract and latest PR review comments.
9. Read only directly relevant routed domain documents.

For work touching project creation, Story/Script routing, Scene/Shot behavior, workflow, UI, generation orchestration, timeline, or export logic, also read:

`project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md`

---

## 2. Repository Truth

- Live Git/GitHub truth newer than documentation is authoritative.
- Historical SHAs in handoff documents are context only.
- Closed WPs must not be reopened without a proven regression.
- Never infer current authorization from a stale document when Issue/PR state has advanced.

---

## 3. Bounded Execution

No execution engine may exceed the currently authorized Work Package.

If `ACTIVE_WORK_PACKAGE = NONE`, application-code implementation is prohibited until the Owner explicitly authorizes a new WP.

If an active PR is under corrective review, corrective work MUST stay in the same WP branch and PR unless the Owner explicitly authorizes otherwise.

Do not auto-start the next WP after a merge.

---

## 4. Authority Model

```text
Project Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = low-credit bounded Execution Plane when explicitly authorized
Codex = STOP by default; local-only specialist when genuinely necessary
Claude Code = STOP by default
```

---

## 5. Git / CI Governance

- Canonical branch: `main`.
- `main` is protected by active ruleset `Protect main`.
- Direct writes, force pushes, and deletion of `main` are prohibited.
- One WP = one branch = one PR.
- `backend-tests` is a required status check.
- Frontend-changing PRs must also pass `frontend-tests` when that workflow is present.
- Green CI does not override a ChatGPT `CHANGES REQUIRED` review.
- Owner approval is still required before merge.

---

## 6. Multi-Mode Rule

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Story or Script is not mandatory for every Project.

Architecture-ready future modes remain unauthorized until separately approved:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

---

## 7. Immediate Startup Actions

1. Report exact live `main` HEAD.
2. Report exact active Issue / PR / branch / HEAD.
3. Report the current authorization/review gate.
4. Read only directly relevant documents and code/diff.
5. Do not repeat completed work or expensive validation without a concrete reason.
6. Do not merge or start another WP without Owner authorization.

The local Antigravity watcher/dispatcher remains PAUSED and is not a production execution dependency.
