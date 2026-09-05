# Mandatory Session Startup Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/START_HERE.md`](project-docs/00_CONTROL/START_HERE.md)

---

## 1. Startup Reading Sequence

EVERY new chat session, AI agent, or execution engine MUST read the following documents in exact order before performing any operations or reading other repository files:

1. **[`project-docs/00_CONTROL/START_HERE.md`](project-docs/00_CONTROL/START_HERE.md)** — Mandatory session startup protocol & governance rules (This document).
2. **[`project-docs/00_CONTROL/CURRENT_STATE.md`](project-docs/00_CONTROL/CURRENT_STATE.md)** — Real-time project phase, execution status, and authority state flags.
3. **[`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)** — Boundaries, requirements, and stop conditions of the current Work Package.
4. **[`project-docs/00_CONTROL/DOCUMENT_INDEX.md`](project-docs/00_CONTROL/DOCUMENT_INDEX.md)** — Domain-to-document routing matrix.
5. **[`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)** — Session resume protocol, `HANDOFF_BASE_SHA` context, and handoff state (required when resuming existing work).
6. **Routed Domain Documents** — Read only specific topic documents routed by `DOCUMENT_INDEX.md` relevant to the active task.

---

## 2. Core Governance Rules

### Live Branch HEAD & Repository Truth Rule
- Every new or resumed session MUST fresh-fetch the live branch HEAD (`git rev-parse HEAD`). Live Git/GitHub repository state is the single source of truth.
- `HANDOFF_BASE_SHA` in handoff documents provides historical baseline context recording the commit prior to handoff updates. Mismatch with live HEAD after handoff commits is expected and normal. Never commit recursive SHA update loops.
- If repository truth proves a document stale, update documentation **ONLY** if that update falls within the currently authorized Work Package (WP).

### Bounded Execution Rule
- AI execution engines (Antigravity) MUST NOT exceed the scope of the currently authorized Work Package.
- Code implementation, frontend/backend logic, cloud resource provisioning, Vidu API calls, secret provisioning, and deployments are strictly prohibited unless explicitly authorized in the active WP.

### Authority Hierarchy
- **Project Owner:** Final human authority.
- **ChatGPT:** Control Plane / Project Lead / System Architect / Independent Reviewer.
- **Antigravity:** Low-Credit / Bounded Execution Plane.
- **Codex / Claude Code:** STOP / Inactive.

---

## 3. Immediate Action Requirements

Upon starting a session:
1. Fresh-fetch live branch HEAD from Git.
2. Verify `CURRENT_STATE.md` to confirm the active Work Package.
3. Check `ACTIVE_TASK.md` for explicit constraints and stop conditions.
4. Check `CHAT_HANDOFF.md` for historical handoff context and review status.
5. Do NOT start any unauthorized tasks.
