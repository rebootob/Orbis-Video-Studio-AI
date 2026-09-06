# AI Execution Policy & Guardrails

> **Canonical Document Location:** [`project-docs/10_GOVERNANCE/AI_EXECUTION_POLICY.md`](project-docs/10_GOVERNANCE/AI_EXECUTION_POLICY.md)

---

## 1. Execution Principles

All AI execution engines operating in this repository MUST follow:

1. **Repository Truth First:** fresh-fetch live branch/PR state before status or implementation decisions.
2. **Bounded Execution:** execute only the active Owner-authorized WP/corrective scope.
3. **One Writer per Working Tree:** never allow multiple implementation agents to mutate the same checkout concurrently; prefer a dedicated worktree for Antigravity when needed.
4. **Evidence over Claims:** diagnostics and success claims must be grounded in actual diff/log/test/CI evidence.
5. **No Superficial Patches:** do not swallow exceptions, fake states, fabricate provider/config/cost data, or weaken safety assertions to make tests pass.
6. **Preserve Contracts and History:** do not silently destroy production history, public contracts, audit evidence, or locked state.
7. **Low-Credit Routing:** Antigravity handles repetitive implementation/test loops; Codex is STOP by default and reserved for genuinely necessary local-only work.
8. **Focused Tests During Iteration:** run tests relevant to changed code during corrective loops; avoid repeated full-suite runs.
9. **Final Gate Validation:** run required full regression once, migration lifecycle once if schema changed, and environment-specific validation required by the WP.
10. **No Autonomous Next WP:** stop after delivery/corrective push and return control to ChatGPT/Owner.

---

## 2. Git / CI Guardrails

| Action | Policy | Enforcement |
| :--- | :--- | :--- |
| Direct application/doc write to `main` | FORBIDDEN | Active `Protect main` ruleset; use feature/doc branch + PR. |
| Force push / delete `main` | FORBIDDEN | Repository ruleset. |
| New branch/PR for corrective on same WP | FORBIDDEN by default | Corrective stays on same WP branch/PR. |
| Autonomous merge | FORBIDDEN | Requires ChatGPT PASS + explicit Owner approval. |
| Merge with failing `backend-tests` | FORBIDDEN | Required GitHub status check. |
| Merge frontend changes with failing `frontend-tests` | FORBIDDEN | Frontend CI evidence required when workflow applies. |
| Merge with unresolved review conversation | FORBIDDEN | Repository ruleset. |
| Multiple implementation agents in one checkout | FORBIDDEN | One-writer policy. |

Green CI is necessary but does not override architectural/product/security review findings.

---

## 3. Agent Routing

### ChatGPT
- Control Plane / Project Lead / Architect / Independent Reviewer
- Reads GitHub truth, defines bounded work, reviews exact diffs and evidence
- Does not rely on executor self-assessment as final authority

### Antigravity
- Primary bounded Execution Plane
- Implementation, repetitive edits, focused tests, migrations, local validation and corrective cycles
- Pushes to the authorized branch and stops for independent review

### Codex
- STOP by default
- Use only when a local-only reproduction, browser/runtime/environment issue, or independent final validation cannot be done efficiently through GitHub/Antigravity
- Must not duplicate repetitive implementation/test loops

### Claude Code
- STOP by default unless explicitly authorized for a specialist ambiguity

---

## 4. Session Handoff & Stop Protocol

When an execution agent finishes an authorized WP or corrective round:

1. Confirm it is on the authorized branch and the working tree is coherent.
2. Run focused validation required for the changed scope.
3. At final gate, run the required full validation once.
4. `git diff --check`.
5. Commit and push the SAME authorized branch.
6. Keep the existing PR for corrective work.
7. Report exact HEAD, files changed, tests, CI expectations, scope deviations and blockers.
8. STOP. Do not merge and do not start another WP.

ChatGPT then independently reviews repository truth. Owner remains final merge authority.
