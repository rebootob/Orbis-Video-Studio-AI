# Current Project State

> **Canonical Document Location:** [`project-docs/00_CONTROL/CURRENT_STATE.md`](project-docs/00_CONTROL/CURRENT_STATE.md)

---

## State Flags

```yaml
PHASE: P2 — Generation & Multi-Mode Production Pipeline
CANONICAL_BRANCH: main
MAIN_HEAD: 643614b089a295ea96be179e470707609cbe4b53

P2-WP006: PASS / CLOSED / MERGED
P2-WP007: PASS / CLOSED / MERGED
P2-WP007_PR: "#15"
P2-WP007_REVIEWED_HEAD: 5a03d4d7f56ac8ae39a78914276610c0512da78b
P2-WP007_MERGE_COMMIT: 9cb098dea7fc2948b023ad48163c729f566573a7

P2-WP008: PASS / CLOSED / MERGED
P2-WP008_PR: "#19"
P2-WP008_REVIEWED_HEAD: a2c3f3d4e80a0b0aedb58fba5a04a436c9e88797
P2-WP008_MERGE_COMMIT: a360c3b38d1d962f9f3c5f6412e3107e90fae7db

P2-WP009: PASS / CLOSED / MERGED
P2-WP009_PR: "#23"
P2-WP009_REVIEWED_HEAD: 250df0bb6df24577e2e1f14c7ada3d0dbbaf75fa
P2-WP009_MERGE_COMMIT: 9f094a5cbe9a4faeb5741231d0a819da0da283c1

P2-WP010: PASS / CLOSED / MERGED
P2-WP010_ISSUE: "#24"
P2-WP010_PR: "#25"
P2-WP010_BRANCH: ai/p2-wp010-mode-aware-web-workspace
P2-WP010_REVIEWED_HEAD: 0f0a16fa95c8110bc8ab7a0c52d45351eaa82182
P2-WP010_MERGE_COMMIT: 639e61fb69b6abee8598074add458035db906ceb
P2-WP010_FINAL_REVIEW: PASS / READY TO MERGE (Review ID 5124386306)

P2-WP011: PASS / CLOSED / MERGED
P2-WP011_ISSUE: "#28"
P2-WP011_PR: "#29"
P2-WP011_BRANCH: ai/p2-wp011-batch-resume
P2-WP011_REVIEWED_HEAD: b2f349adb6d5704fa1aadfb19e06644b40a37080
P2-WP011_MERGE_COMMIT: 643614b089a295ea96be179e470707609cbe4b53
P2-WP011_FINAL_REVIEW: PASS / READY TO MERGE (Review ID 5124729394)

ACTIVE_WORK_PACKAGE: P2-WP012
CURRENT_GATE: IMPLEMENTATION COMPLETE / READY FOR CHATGPT INDEPENDENT REVIEW

P2-WP012: IMPLEMENTED / AWAITING INDEPENDENT REVIEW
P2-WP012_ISSUE: "#31"
P2-WP012_BRANCH: ai/p2-wp012-production-orchestrator

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

## Detailed Status Matrix

| Component / Layer | Status | Notes |
| :--- | :--- | :--- |
| Governance & Documentation (P0-WP001) | PASS / CLOSED / MERGED | Foundation complete. |
| Backend Core Framework (P1-WP002) | PASS / CLOSED / MERGED | Backend/database foundation complete. |
| Object Storage & Asset API (P1-WP003) | PASS / CLOSED / MERGED | S3-compatible asset layer complete. |
| Document Ingestion Engine (P1-WP004) | PASS / CLOSED / MERGED | PDF/DOCX/PPTX/text ingestion complete. |
| Story & Script Generator (P1-WP005) | PASS / CLOSED / MERGED | Creative generation service complete behind provider-oriented service boundary. |
| Reference Library & Bibles (P2-WP006) | PASS / CLOSED / MERGED | Reference context, bibles and lock safety complete. |
| Vidu Provider Adapter & Durable Queue (P2-WP007) | PASS / CLOSED / MERGED | Durable job control, retries, reconciliation, cancellation and secret safety complete. |
| Hybrid Shot / Asset Lock / Base Video Modes (P2-WP008) | PASS / CLOSED / MERGED | Hybrid shot engine, lock machine, Core V1 video modes and config inheritance complete. |
| Cost Control & Granular Usage Audit Ledger (P2-WP009) | PASS / CLOSED / MERGED | Provider-neutral usage ledger, budget controls, pricing abstraction, audit adjustments and DB-level idempotency complete. |
| Mode-Aware Web Workspace & Automation-First Storyboard UX (P2-WP010) | PASS / CLOSED / MERGED | PR #25 merged into main at 639e61fb69b6abee8598074add458035db906ceb. Mode-aware workspace, staged approvals, full-history retention, queue controls and safety gates complete. |
| Selective / Batch Regeneration & Resume Service (P2-WP011) | PASS / CLOSED / MERGED | Canonical candidate selection, shot deduplication, repeat-safe resume, set-based DB queries (no N+1), transactional job/audit persistence, bounded keyset execution, memory-bounded created_jobs accumulation, and BatchRun audit complete. PR #29 merged into main at 643614b089a295ea96be179e470707609cbe4b53. |
| Production Orchestrator & Staged Approval State Machine (P2-WP012) | IMPLEMENTED / AWAITING REVIEW | Server-side orchestrator service, stage transition gates, mode routing (STORY, SHORT, LOOP, SCENE), automation modes (MANUAL, ASSISTED, AUTO), append-only orchestration audit ledger, frontend integration replacing client status mutations. Branch ai/p2-wp012-production-orchestrator. |
| Watcher / Dispatcher automation | PAUSED | Do not depend on it for production delivery until separate no-credit UAT passes. |

---

## Locked Product Direction

Orbis Video Studio AI is a cloud-first, provider-independent **AI Video Production Orchestrator / Production Control Plane**. It should orchestrate best-of-breed creative, image, video and audio providers rather than reimplement foundation models.

The system owns production state and control: Project, Story/Scene/Shot structure, references, locks, approvals, history/version lineage, durable jobs, cost/budget, QC, assembly and export.

Target guided production flow:

```text
Brief / References
-> Story
-> Review / Approve
-> Storyboard
-> Review / Approve
-> Shot Plan + Prompts
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

Users may stop, review, go back, regenerate selected items, restore previous versions and continue from incomplete work. Full Auto remains an option, but it must never remove safe review/control.

UI principle:

```text
Simple enough for first-time users
Powerful enough for advanced users
Consistent across every screen
Safe for costly AI actions
Beautiful but not distracting
```

---

## Next Allowed Action

1. Keep WP001-WP011 closed unless a proven regression exists.
2. `ACTIVE_WORK_PACKAGE = P2-WP012`.
3. `CURRENT_GATE = IMPLEMENTATION COMPLETE / READY FOR CHATGPT INDEPENDENT REVIEW`.
4. Await ChatGPT Independent Review for P2-WP012 PR.
5. Antigravity = STOP / NONE.
6. Codex = STOP.
7. Claude Code = STOP.
8. Do NOT merge without Owner approval.
9. Do NOT start WP013.

Live GitHub/repository truth newer than this document is authoritative.
