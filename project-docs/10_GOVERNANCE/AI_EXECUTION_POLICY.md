# AI Execution Policy & Guardrails

> **Canonical Document Location:** [`project-docs/10_GOVERNANCE/AI_EXECUTION_POLICY.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/10_GOVERNANCE/AI_EXECUTION_POLICY.md)

---

## 1. Execution Principles for AI Agents

All AI execution engines (Antigravity, etc.) operating within this repository MUST strictly follow these execution principles:

1. **Bounded Execution:** Execute ONLY the active, authorized Work Package (WP). Never initiate next WPs or expand scope autonomously.
2. **Empirical Log Verification:** Base all diagnostics on actual command outputs and log files. Never guess code logic or form hypotheses without reading logs.
3. **No Superficial Symptom Patches:** Do NOT fix bugs by swallowing exceptions, adding silent dummy fallbacks, commenting out broken assertions, or returning empty 0-byte placeholders.
4. **Never Claim Success Without Verification:** Never declare a task complete without executing builds, tests, or validation commands to empirically prove success.
5. **Preserve Comments & API Contracts:** Preserve existing code comments, docstrings, and public function signatures. If changing signatures, update all call sites.
6. **No Main Thread Blocking:** Never introduce blocking calls on main UI loops or single-threaded event loops.

---

## 2. Guardrails Matrix

| Action | Policy | Enforcement |
| :--- | :--- | :--- |
| **Write Application Code in P0-WP001** | **FORBIDDEN** | Bounded execution rule; doc-only WP. |
| **Provision Cloud Infrastructure** | **FORBIDDEN** | Requires explicit infra WP authorization. |
| **Call Provider APIs (Vidu, etc.)** | **FORBIDDEN** | Requires explicit provider WP authorization. |
| **Commit to `main` Directly** | **FORBIDDEN** | Must use feature branch `ai/<wp-id>-<desc>` and PR. |
| **Autonomous Merge of PR** | **FORBIDDEN** | Must wait for ChatGPT review and Owner merge. |

---

## 3. Session Handoff & Stop Protocol

When an AI agent finishes a Work Package:
1. Ensure all code/docs compile cleanly and pass verification.
2. Commit and push the feature branch to `origin`.
3. Open a Pull Request into `main`.
4. Update [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/CHAT_HANDOFF.md) with HEAD SHA and PR details.
5. **STOP.** Do not make additional calls or start new tasks. Return final summary to Project Owner.
