# Current Project State

> **Canonical Document Location:** [`project-docs/00_CONTROL/CURRENT_STATE.md`](project-docs/00_CONTROL/CURRENT_STATE.md)

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
MAIN_HEAD: a09fcab835515679bf4f0bbfce8aec84f7e15062

P0-WP001: PASS / CLOSED / MERGED
P1-WP002: PASS / CLOSED / MERGED
P1-WP003: PASS / CLOSED / MERGED
P1-WP004: PASS / CLOSED / MERGED
P1-WP005: PASS / CLOSED / MERGED
P2-WP006: PASS / CLOSED / MERGED
P2-WP007: PASS / CLOSED / MERGED
P2-WP008: PASS / CLOSED / MERGED
P2-WP009: PASS / CLOSED / MERGED
P2-WP010: PASS / CLOSED / MERGED
P2-WP011: PASS / CLOSED / MERGED
P2-WP012: PASS / CLOSED / MERGED
P2-WP013: PASS / CLOSED / MERGED
P3-WP014: PASS / CLOSED / MERGED
P3-WP015: PASS / CLOSED / MERGED
P3-WP016: PASS / CLOSED / MERGED
P3-WP017: PASS / CLOSED / MERGED
P4-WP018: PASS / CLOSED / MERGED
P4-WP019: PASS / CLOSED / MERGED

P4-WP019_PR: "#50"
P4-WP019_BRANCH: ai/p4-wp019-orbis-archive
P4-WP019_PRE1_REVIEWED_HEAD: e1deff16aa93fb3b2e68d404415971351c4a9e46
P4-WP019_PRE1_MERGE_COMMIT: 5f3ccbbcd0ee528bb85501a32efb64c5b13fbce5
P4-WP019_FINAL_REVIEWED_HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
P4-WP019_FINAL_REVIEW: PASS / READY FOR OWNER MERGE DECISION (Review ID 5135969695)
P4-WP019_MERGE_COMMIT: a09fcab835515679bf4f0bbfce8aec84f7e15062
P4-WP019_PROPOSAL: project-docs/40_DELIVERY/P4_WP019_PROPOSAL.md

ACTIVE_WORK_PACKAGE: NONE
IMPLEMENTATION_AUTHORIZED: NONE
CURRENT_GATE: POST-WP019 / READY FOR OWNER WP020 AUTHORIZATION DECISION
P4-WP020: PROPOSED / NOT AUTHORIZED

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT

VIDEO_PRODUCTION_MODES_V1:
  - STORY
  - SHORT
  - LOOP
  - SCENE
VIDEO_PRODUCTION_MODES_ARCHITECTURE_READY:
  - PRODUCT
  - EXPLAINER
  - PRESENTER
  - MONTAGE

MULTI_PROJECT: REQUIRED
FULL_HISTORY_RETENTION: REQUIRED
AUDITABLE_CHANGES: REQUIRED
NO_SILENT_HISTORY_LOSS: REQUIRED
AUTOMATION_FIRST: REQUIRED
AUTO_STORYBOARD: REQUIRED
AUTO_SHOT_PLANNING: REQUIRED
BATCH_GENERATION: REQUIRED
GUIDED_FLEXIBILITY: REQUIRED
NEXT_BEST_ACTION_GUIDANCE: REQUIRED
APPROVAL_GATED_AUTOMATION: REQUIRED
AUDIO_PRODUCTION_CORE_V1: REQUIRED
PERFORMANCE_AND_SCALABILITY: REQUIRED_PRODUCT_QUALITY_ATTRIBUTE

LOCAL_AI: DISALLOWED
CLOUD_AI: REQUIRED
VIDU: V1 DEFAULT VIDEO PROVIDER BEHIND ADAPTER
VENDOR_LOCK_IN: DISALLOWED
ANTIGRAVITY: STOP / NONE
CODEX: STOP
CLAUDE_CODE: STOP
WATCHER: PAUSED / NOT PRODUCTION-TRUSTED
```

---

## Delivery Status Matrix

| Work Package | Status | Key Truth |
| :--- | :--- | :--- |
| P0-WP001 — Governance & Architecture Documentation | PASS / CLOSED / MERGED | Foundation complete. |
| P1-WP002 — Backend Core Framework | PASS / CLOSED / MERGED | Backend/database foundation complete. |
| P1-WP003 — Object Storage & Asset API | PASS / CLOSED / MERGED | S3-compatible asset layer complete. |
| P1-WP004 — Document Ingestion Engine | PASS / CLOSED / MERGED | PDF/DOCX/PPTX/text ingestion complete. |
| P1-WP005 — Story & Script Generator | PASS / CLOSED / MERGED | Creative generation service complete behind provider boundary. |
| P2-WP006 — Reference Library & Bibles | PASS / CLOSED / MERGED | Reference context, bibles and lock safety complete. |
| P2-WP007 — Vidu Adapter & Durable Queue | PASS / CLOSED / MERGED | Durable provider job control complete. |
| P2-WP008 — Hybrid Shot / Asset Lock / Base Modes | PASS / CLOSED / MERGED | Hybrid shot engine and Core V1 modes complete. |
| P2-WP009 — Cost Control & Usage Ledger | PASS / CLOSED / MERGED | Budget and provider-neutral usage audit complete. |
| P2-WP010 — Mode-Aware Web Workspace | PASS / CLOSED / MERGED | Approval-gated, automation-first workspace complete. |
| P2-WP011 — Batch Regeneration / Resume | PASS / CLOSED / MERGED | Repeat-safe batch/resume and performance guardrails complete. |
| P2-WP012 — Production Orchestrator | PASS / CLOSED / MERGED | Server-side stage state machine and orchestration audit complete. |
| P2-WP013 — Storyboard Image / Keyframe Pipeline | PASS / CLOSED / MERGED | Provider-neutral ImageProvider pipeline complete. |
| P3-WP014 — Core V1 Audio Production | PASS / CLOSED / MERGED | AudioProvider and audio production automation complete. |
| P3-WP015 — Simplified Assembly / Timeline | PASS / CLOSED / MERGED | Assembly timeline and preview complete. |
| P3-WP016 — QC & Approval Pipeline | PASS / CLOSED / MERGED | QC findings, decisions and approval gate complete. |
| P3-WP017 — Cloud Render Workers | PASS / CLOSED / MERGED | Durable render lifecycle and worker fencing complete. |
| P4-WP018 — Multi-Output Export Presets | PASS / CLOSED / MERGED | Multi-platform render variants and presets complete. |
| P4-WP019 — Project Archive `.orbis` | PASS / CLOSED / MERGED | PR #50 merged at `a09fcab835515679bf4f0bbfce8aec84f7e15062`. Final reviewed HEAD `df691035f54c1a9ffea4934b6f43134fde35d391`, Review ID `5135969695`. |
| P4-WP020 — E2E Integration, UAT & Core V1 Release | PROPOSED / NOT AUTHORIZED | Final remaining Core V1 work package. Must not start without explicit Owner authorization. |

---

## P4-WP019 Closure Truth

P4-WP019 delivered the portable project archive boundary required for Core V1:

1. `.orbis` ZIP-compatible archive format.
2. Canonical manifest/checksum trust root and canonical JSON.
3. Archive security limits and safe path handling.
4. `FULL_SELF_CONTAINED` Core V1 export contract.
5. Full project graph export/import.
6. CLONE import with UUID/FK remapping and source lineage.
7. RESTORE import with fail-closed collision handling.
8. Phase-3 graph/referential-integrity preflight.
9. Asset completeness and payload/catalog/DB size consistency checks.
10. Historical RenderJob/GenerationJob execution truth preservation with worker fencing.
11. Historical UsageLedger financial truth preservation and budget exclusion.
12. Active partial-unique-index separation for live vs imported historical jobs/ledgers.
13. Transaction rollback and storage compensation.
14. REST API export/import endpoints.
15. Frontend export/import UX using the locked canonical archive contract.

Final exact-head evidence before merge:

```text
Reviewed HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
Independent Review: PASS / READY FOR OWNER MERGE DECISION
Review ID: 5135969695
Backend CI: PASS — 412 passed, 2 skipped
Frontend CI: PASS — 52/52 tests, build PASS, lint 0 errors
PR #50: MERGED / CLOSED
Merge Commit: a09fcab835515679bf4f0bbfce8aec84f7e15062
```

---

## Locked Product Direction

Orbis Video Studio AI is a cloud-first, provider-independent **AI Video Production Orchestrator / Production Control Plane**. It orchestrates best-of-breed Creative, Image, Video and Audio providers rather than reimplementing foundation models.

Core owns production state and control:

- multi-project state
- Story / Scene / Shot lineage
- references and continuity
- locks
- full history/versioning
- approvals
- durable jobs
- retry/resume/reconciliation
- cost/budget
- QC
- assembly
- rendering
- multi-output
- project portability/export/import

Provider-neutral boundaries remain:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Vidu remains the Core V1 default VideoProvider behind an adapter. Cloud-hosted ComfyUI remains future planning only and is not authorized Core V1 implementation.

---

## Current Gate / Next Allowed Action

```text
ACTIVE_WORK_PACKAGE = NONE
P4-WP019 = PASS / CLOSED / MERGED
P4-WP020 = PROPOSED / NOT AUTHORIZED
```

Allowed now:

1. Keep control documents synchronized with the P4-WP019 merge truth.
2. Review/define P4-WP020 scope and acceptance gates if the Owner requests it.
3. Start P4-WP020 implementation only after explicit Owner authorization.

Not allowed now:

- Do not reopen P4-WP019 without a proven regression.
- Do not auto-start P4-WP020.
- Do not expand Core V1 scope into post-V1 integrations or provider experiments.
- Do not merge future implementation without explicit Owner approval.
