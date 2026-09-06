# Current Project State

> **Canonical Document Location:** [`project-docs/00_CONTROL/CURRENT_STATE.md`](project-docs/00_CONTROL/CURRENT_STATE.md)

Live GitHub/repository truth newer than this document is authoritative.

---

## State Flags

```yaml
PHASE: P2 — Generation & Multi-Mode Production Pipeline
CANONICAL_BRANCH: main
CURRENT_MAIN_HEAD: 9f094a5cbe9a4faeb5741231d0a819da0da283c1

P2-WP006: PASS / CLOSED / MERGED
P2-WP007: PASS / CLOSED / MERGED
P2-WP007_PR: "#15"
P2-WP008: PASS / CLOSED / MERGED
P2-WP008_PR: "#19"
P2-WP009: PASS / CLOSED / MERGED
P2-WP009_PR: "#23"
P2-WP009_MERGE_COMMIT: 9f094a5cbe9a4faeb5741231d0a819da0da283c1

ACTIVE_WORK_PACKAGE: P2-WP010
ACTIVE_ISSUE: "#24"
ACTIVE_PR: "#25"
ACTIVE_BRANCH: ai/p2-wp010-mode-aware-web-workspace
INITIAL_REVIEWED_HEAD: 291ea773681831a0a68e585eb7e0664902102be3
CURRENT_PR_HEAD: a687c7adca1bf204767410d51ef0e1cad3ee9436
CURRENT_GATE: CORRECTIVE PUSHED / WAITING CHATGPT INDEPENDENT RE-REVIEW
P2-WP010: NOT READY TO MERGE UNTIL RE-REVIEW PASS

CI_AT_CURRENT_HEAD:
  backend-tests: PASS
  frontend-tests: PASS

ANTIGRAVITY: CORRECTIVE PUSH COMPLETE / STOP FOR RE-REVIEW
CODEX: STOP BY DEFAULT
CLAUDE_CODE: STOP
WATCHER: PAUSED / NOT PRODUCTION-TRUSTED
```

---

## Repository Governance Now Active

- Root `AGENTS.md` is merged and is the first agent policy router.
- GitHub Actions backend workflow is merged.
- `main` is protected by active ruleset `Protect main`.
- PRs must pass required `backend-tests` before merge.
- Review conversations must be resolved before merge.
- Force push and deletion of `main` are blocked.
- Head branches are automatically deleted after merge.
- Frontend CI workflow exists in the active WP010 PR and is green at current HEAD.

---

## Detailed Status Matrix

| Component / Layer | Status | Notes |
| :--- | :--- | :--- |
| Governance & Documentation (P0-WP001) | PASS / CLOSED / MERGED | Foundation plus current `AGENTS.md`, protected `main`, PR/CI workflow. |
| Backend Core Framework (P1-WP002) | PASS / CLOSED / MERGED | Backend/database foundation complete. |
| Object Storage & Asset API (P1-WP003) | PASS / CLOSED / MERGED | S3-compatible asset layer complete. |
| Document Ingestion Engine (P1-WP004) | PASS / CLOSED / MERGED | PDF/DOCX/PPTX/text ingestion complete. |
| Story & Script Generator (P1-WP005) | PASS / CLOSED / MERGED | OpenAI creative generation service complete. |
| Reference Library & Bibles (P2-WP006) | PASS / CLOSED / MERGED | Reference context, bibles and lock safety complete. |
| Vidu Provider Adapter & Durable Queue (P2-WP007) | PASS / CLOSED / MERGED | Provider-neutral adapter/queue, idempotency, reconciliation, cancellation and secret safety. |
| Hybrid Shot / Asset Lock / Base Video Modes (P2-WP008) | PASS / CLOSED / MERGED | PR #19 merged; hybrid shots, ownership validation, lock machine, V1 modes, config inheritance. |
| Cost Control & Granular Usage Audit Ledger (P2-WP009) | PASS / CLOSED / MERGED | PR #23 merged; provider-neutral ledger, budget controls, pricing abstraction, manual adjustments, migration 009. |
| Mode-Aware Web Workspace (P2-WP010) | WAITING RE-REVIEW | PR #25 corrective commit pushed; CI green; exact corrective diff still requires independent review. |
| Watcher / Dispatcher automation | PAUSED | Not a production execution dependency. |

---

## P2-WP010 Review History

Initial independent review at HEAD `291ea773681831a0a68e585eb7e0664902102be3` returned **CHANGES REQUIRED / NOT READY TO MERGE**.

Blocking areas were:

1. destructive hard delete vs full history retention
2. missing staged Story / Storyboard / Shot Plan / Images / Video review gates
3. missing state-aware Guided Flexibility / Next Best Action
4. incomplete multi-project dashboard actions/summaries
5. placeholder reference/document upload and weak effective-reference visibility
6. untruthful history/version claims
7. fabricated audio/provider/config readiness claims
8. QC states not grounded in backend truth
9. fake approval semantics through raw status mutation
10. missing Generate Selected / cost-safe batch confirmation / provider-neutral effective config
11. incomplete reorder/duplicate/autosave UX
12. unsafe CORS configuration
13. additional truthful progress, language and status-validation issues

Antigravity then pushed corrective commit:

`a687c7adca1bf204767410d51ef0e1cad3ee9436`

Commit message:
`fix(wp010): address review blockers with soft retention, cost confirmation, staged workflow, and truthful readiness`

Both backend and frontend GitHub Actions are green at this corrective HEAD.

**Important:** previous blockers are not considered closed merely because a corrective commit and green CI exist. ChatGPT must independently review the exact new HEAD.

---

## Locked Product Direction

Orbis Video Studio AI is a cloud-first, provider-independent, reference-driven, shot-based, multi-mode AI video production automation workspace.

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

Story is optional at Project level. Video Mode remains separate from Purpose, Target Platform, Aspect Ratio, and Output Preset.

---

## Next Allowed Action

1. Keep WP006-WP009 closed unless a proven regression exists.
2. ChatGPT independently re-review exact PR #25 HEAD `a687c7adca1bf204767410d51ef0e1cad3ee9436` against Issue #24 and the prior blocking findings.
3. If PASS: report READY TO MERGE and wait for explicit Owner merge approval.
4. If findings remain: send only bounded corrective findings back to Antigravity on the SAME branch/PR.
5. Do not create a replacement PR.
6. Do not start WP011.
7. Do not merge until ChatGPT PASS and explicit Owner approval.
