# Current Project State

> **Canonical Document Location:** [`project-docs/00_CONTROL/CURRENT_STATE.md`](project-docs/00_CONTROL/CURRENT_STATE.md)

---

## State Flags

```yaml
PHASE: P2 — Generation & Multi-Mode Production Pipeline
CANONICAL_BRANCH: main
MAIN_HEAD_AFTER_WP007: 9cb098dea7fc2948b023ad48163c729f566573a7

P2-WP006: PASS / CLOSED / MERGED
P2-WP007: PASS / CLOSED / MERGED
P2-WP007_PR: "#15"
P2-WP007_REVIEWED_HEAD: 5a03d4d7f56ac8ae39a78914276610c0512da78b
P2-WP007_MERGE_COMMIT: 9cb098dea7fc2948b023ad48163c729f566573a7

ACTIVE_WORK_PACKAGE: P2-WP008
CURRENT_GATE: CHATGPT INDEPENDENT REVIEW
P2-WP008: IMPLEMENTED / WAITING CHATGPT REVIEW

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

LOCAL_AI: DISALLOWED
CLOUD_AI: REQUIRED
VIDU: V1 DEFAULT VIDEO PROVIDER / ADAPTER MERGED
VENDOR_LOCK_IN: DISALLOWED
ANTIGRAVITY: BOUNDED EXECUTION COMPLETE / AWAITING CHATGPT REVIEW
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
| Story & Script Generator (P1-WP005) | PASS / CLOSED / MERGED | OpenAI creative generation service complete. |
| Reference Library & Bibles (P2-WP006) | PASS / CLOSED / MERGED | Reference context, bibles and lock safety complete. |
| Vidu Provider Adapter & Durable Queue (P2-WP007) | PASS / CLOSED / MERGED | PR #15 merged; durable claim/lease fencing, retry/poll scheduling, cancellation, reconciliation, secret safety and mocked Vidu contract tests complete. |
| Hybrid Shot / Asset Lock / Base Video Modes (P2-WP008) | IMPLEMENTED / WAITING REVIEW | Hybrid shot engine (6 sources), asset ownership validation, AssetLock machine with audit trail, Core V1 video modes (STORY/SHORT/LOOP/SCENE), config inheritance, migration 008. |
| Watcher / Dispatcher automation | PAUSED | Do not depend on it for production project delivery until separate no-credit UAT passes. |

---

## Locked Product Direction

Orbis Video Studio AI is a cloud-first, provider-independent, reference-driven, shot-based, **multi-mode** video production platform.

The system MUST NOT require a complete Story -> Script workflow for every project.

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

Video Mode is separate from Purpose, Target Platform, Aspect Ratio and Output Preset.

---

## Next Allowed Action

1. Keep WP007 closed; do not reopen without a proven regression.
2. Review the P2-WP008 proposal.
3. Start P2-WP008 only after explicit Project Owner authorization.
4. Do not automatically start any later WP.

Live GitHub/repository truth newer than this document is authoritative.
