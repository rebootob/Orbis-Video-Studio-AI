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
P3-WP016 = PASS / CLOSED / MERGED
P3-WP017 = PASS / CLOSED / MERGED
P4-WP018 = PASS / CLOSED / MERGED
P4-WP019 = PASS / CLOSED / MERGED
```

Current delivery count:

```text
19 of 20 planned Core V1 work packages merged = 95% by WP count
```

---

## P4-WP019 Closure Truth

```text
WP019 PRE1 PR: #49
WP019 PRE1 reviewed HEAD: e1deff16aa93fb3b2e68d404415971351c4a9e46
WP019 PRE1 merge commit: 5f3ccbbcd0ee528bb85501a32efb64c5b13fbce5

WP019 implementation PR: #50 (MERGED / CLOSED)
WP019 implementation branch: ai/p4-wp019-orbis-archive
WP019 final reviewed HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
WP019 final independent review: PASS / READY FOR OWNER MERGE DECISION
WP019 final review ID: 5135969695
WP019 merge commit / current canonical main HEAD: a09fcab835515679bf4f0bbfce8aec84f7e15062
```

Final exact-head evidence before merge:

```text
Backend: 412 passed, 2 skipped
Frontend: 52/52 tests PASS
Frontend build/typecheck: PASS
Frontend lint: 0 errors
```

Accepted WP019 capabilities:

1. `.orbis` ZIP-compatible portable archive.
2. Canonical manifest/checksum trust root and canonical JSON.
3. Safe archive path handling and bounded extraction/security limits.
4. Core V1 canonical package: `FULL_SELF_CONTAINED` only.
5. Full project graph export/import.
6. CLONE import with UUID/FK remap, asset re-upload and source lineage.
7. RESTORE import with fail-closed collision handling.
8. Phase-3 graph/referential-integrity preflight.
9. Asset completeness and payload/catalog/DB consistency validation.
10. Historical job status/attempt/error/timestamp truth preservation.
11. `imported_historical` / `execution_disabled` worker fencing.
12. RenderJob / GenerationJob / UsageLedger partial-index separation for historical vs live state.
13. Historical UsageLedger financial truth preservation and live budget exclusion.
14. Transaction rollback and storage compensation.
15. REST API and frontend Export/Import workflow.

P4-WP019 is closed. Do not reopen it without a proven regression.

---

## Current Gate

```text
CANONICAL_MAIN_HEAD = a09fcab835515679bf4f0bbfce8aec84f7e15062
ACTIVE_WORK_PACKAGE = NONE
IMPLEMENTATION_AUTHORIZED = NONE
CURRENT_GATE = POST-WP019 / READY FOR OWNER WP020 AUTHORIZATION DECISION
P4-WP019 = PASS / CLOSED / MERGED
P4-WP020 = PROPOSED / NOT AUTHORIZED
ANTIGRAVITY = STOP / NONE
CODEX = STOP
CLAUDE_CODE = STOP
```

Completion of WP019 does **not** auto-authorize WP020.

---

## Remaining Core V1 Work

Only one planned Core V1 work package remains:

### P4-WP020 — End-to-End System Integration, UAT & Core V1 Release

Status:

```text
PROPOSED / NOT AUTHORIZED
```

WP020 should be bounded to system-level integration verification, UAT, release readiness and Core V1 closure. It must not silently absorb post-V1 integrations, new providers or unrelated product expansion.

Before implementation, ChatGPT should inspect current repository truth and define the exact WP020 scope, UAT matrix, release gates, evidence requirements and rollback/closure criteria for Owner approval.

---

## Owner-Locked Product Direction

Orbis Video Studio AI is an **AI Video Production Orchestrator / Production Control Plane**, not a foundation-model project and not a heavyweight manual NLE clone.

Provider-neutral boundaries:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Core-owned value:

- multi-project state
- Story / Scene / Shot structure and lineage
- references and continuity
- locks
- full history/versioning
- approvals
- durable job execution
- retry/resume/reconciliation
- cost/budget
- QC
- assembly
- render/multi-output
- project portability/export/import

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready later only:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Product locks:

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
HUMAN_REVIEW_NOT_HUMAN_MICROMANAGEMENT = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION_CORE_V1 = REQUIRED
PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
VENDOR_LOCK_IN = DISALLOWED
```

Vidu remains the implemented Core V1 default VideoProvider behind an adapter. ComfyUI/cloud-GPU execution remains future planning only and must not enter WP020 unless separately authorized.

---

## Roles

```text
Owner = final human authority / authorization / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = low-credit bounded Execution Plane only when explicitly authorized
Codex = STOP by default
Claude Code = STOP
```

The local Antigravity watcher/dispatcher remains PAUSED and must not be treated as a production dependency.

---

## Mandatory Resume Procedure

1. Fresh-fetch current `main` HEAD.
2. Read `project-docs/00_CONTROL/START_HERE.md`.
3. Read `project-docs/00_CONTROL/CURRENT_STATE.md`.
4. Read `project-docs/00_CONTROL/ACTIVE_TASK.md`.
5. Read `project-docs/00_CONTROL/DOCUMENT_INDEX.md`.
6. Read this handoff.
7. Read `project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md` when preparing a new session.
8. Confirm `ACTIVE_WORK_PACKAGE = NONE` unless newer repository truth says otherwise.
9. Do not start WP020 without explicit Owner authorization.
10. Do not repeat closed WP019 work unless a proven regression exists.
