# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX
```

Status:

```text
CORRECTIVE PUSHED / WAITING CHATGPT INDEPENDENT RE-REVIEW / DO NOT MERGE YET
```

Owner Authorization:
GitHub Issue #24.

Existing delivery branch:
`ai/p2-wp010-mode-aware-web-workspace`

Existing PR:
`#25`

Initial reviewed HEAD:
`291ea773681831a0a68e585eb7e0664902102be3`

Latest known corrective **code** HEAD:
`a687c7adca1bf204767410d51ef0e1cad3ee9436`

Documentation-sync commits may follow the corrective code commit; therefore the exact current PR HEAD must always be fresh-fetched before review.

CI at the corrective code HEAD:
- `backend-tests` PASS
- `frontend-tests` PASS

Execution Engine:
Antigravity corrective push is complete and MUST STOP for independent re-review. Codex and Claude Code remain STOP by default.

---

## Objective

Deliver a safe, first-time-user-friendly, mode-aware browser workspace for STORY / SHORT / LOOP / SCENE that favors automation and human review over per-shot micromanagement, while preserving provider-neutral backend boundaries, cost controls, lock safety, full history retention, and truthful UI state.

---

## Review Context

The initial implementation at `291ea773...` received CHANGES REQUIRED for history retention, staged review workflow, guided next action, multi-project completeness, real upload/reference UX, truthful history/audio/QC semantics, approval/status safety, cost-safe selected/batch generation, storyboard editing/autosave, provider neutrality, truthful progress/language/status handling, and CORS.

Antigravity pushed corrective code commit `a687c7ad...` claiming to address those review blockers. CI was green at that code HEAD.

Do not assume any blocker is closed until ChatGPT independently verifies the corrective diff and exact current PR state.

---

## Current Required Action

ChatGPT independent re-review of the exact current PR #25 HEAD after a fresh fetch.

Review priorities:

1. Verify destructive delete has been replaced/disabled safely and history is preserved.
2. Verify staged Story -> Storyboard -> Shot Plan -> Images -> Video review/readiness behavior.
3. Verify state-aware Next Best Action guidance.
4. Verify minimum multi-project management and summaries.
5. Verify real reference/document upload and effective-reference visibility.
6. Verify history/audio/QC/readiness labels are truthful and backend-grounded.
7. Verify approval/status semantics do not imply unsupported workflow authority.
8. Verify Generate Selected and cost estimate/confirmation behavior.
9. Verify provider config remains neutral and not hard-coded in core/frontend semantics.
10. Verify scene/shot reorder, safe duplication and autosave/saved-state behavior.
11. Verify safe configured CORS.
12. Verify progress, language (including Thai/general support), status validation, lock and cross-project safety.
13. Verify tests and CI actually cover the corrected behavior.

---

## Validation Policy

During any further corrective round:
- run focused tests relevant to the exact finding
- do not repeatedly run full suites after every small edit

At final gate:
- frontend lint/typecheck/build/tests
- backend focused tests and full regression
- migration lifecycle if schema changed
- `git diff --check`
- GitHub Actions `backend-tests` PASS
- GitHub Actions `frontend-tests` PASS
- no live paid provider calls

---

## Current Roles

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Architect / Independent Reviewer
Antigravity = STOP until re-review findings or next explicit authorization
Codex = STOP by default
Claude Code = STOP
```

---

## Next Allowed Action

Fresh-fetch and re-review PR #25 exact current HEAD.

Use `a687c7adca1bf204767410d51ef0e1cad3ee9436` as the latest known corrective-code baseline, not as an assumption that it is still the PR HEAD.

If PASS: wait for Owner merge approval.

If CHANGES REQUIRED: issue bounded corrective findings to Antigravity on the SAME branch/PR, then STOP for re-review again.

Do not merge and do not start WP011 automatically.
