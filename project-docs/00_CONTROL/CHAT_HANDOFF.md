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
```

WP007 merged via PR #15.

```text
Reviewed feature HEAD:
5a03d4d7f56ac8ae39a78914276610c0512da78b

Merge commit:
9cb098dea7fc2948b023ad48163c729f566573a7
```

WP007 delivered the provider-neutral Vidu adapter and durable DB-backed generation queue with claim/lease fencing, idempotency, bounded retry/poll scheduling, safe reconciliation for ambiguous submissions, provider-neutral cancellation, secret/result safety and mocked Vidu tests. No live Vidu credits were required.

---

## Current Gate

```text
ACTIVE WORK PACKAGE = NONE
NEXT CANDIDATE = P2-WP008
P2-WP008 = PROPOSED / NOT AUTHORIZED
```

Do not start WP008 until explicit Owner authorization.

---

## Owner-Locked Multi-Mode Direction

Orbis is a multi-mode video production platform.

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready future modes:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Mode routing:

```text
STORY -> Story -> Script -> Scenes -> Shots
SHORT -> Hook/Concept -> Scene -> Shots
LOOP -> Loop Spec -> Shot(s)
SCENE -> Scene -> 1-N Shots
```

Story is optional at Project level. Video Mode is separate from Purpose, Target Platform, Aspect Ratio and Output Preset.

The earliest planned implementation point for base Video Mode configuration is P2-WP008.

---

## Roles

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane when explicitly authorized
Codex = STOP by default
Claude Code = STOP
```

GitHub connector write access is available to ChatGPT for repository control work such as Issue/PR/document operations. Direct `main` writes and merges still require governance/Owner approval.

The local Antigravity watcher/dispatcher is PAUSED. Do not depend on it for production execution until separate no-credit UAT passes.

---

## Mandatory Resume Procedure

1. Fresh-fetch current `main` HEAD.
2. Read `START_HERE.md`.
3. Read `CURRENT_STATE.md`.
4. Read `ACTIVE_TASK.md`.
5. Read `DOCUMENT_INDEX.md`.
6. Read this handoff.
7. Read `VIDEO_PRODUCTION_MODES.md` for product/mode work.
8. Read the exact active WP contract before implementation.
9. Do not repeat closed work.
10. Do not start the next WP without explicit Owner authorization.
