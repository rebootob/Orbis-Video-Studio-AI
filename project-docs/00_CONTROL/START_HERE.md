# Mandatory Session Startup Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/START_HERE.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/START_HERE.md)

---

## 1. Startup Reading Sequence

EVERY new chat session, AI agent, or execution engine MUST read the following documents in exact order before performing any operations or reading other repository files:

1. **[`project-docs/00_CONTROL/START_HERE.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/START_HERE.md)** — Mandatory session startup protocol & governance rules (This document).
2. **[`project-docs/00_CONTROL/CURRENT_STATE.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/CURRENT_STATE.md)** — Real-time project phase, execution status, and authority state flags.
3. **[`project-docs/00_CONTROL/ACTIVE_TASK.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/ACTIVE_TASK.md)** — Boundaries, requirements, and stop conditions of the current Work Package.
4. **[`project-docs/00_CONTROL/DOCUMENT_INDEX.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/DOCUMENT_INDEX.md)** — Domain-to-document routing matrix.
5. **[`project-docs/00_CONTROL/CHAT_HANDOFF.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/CHAT_HANDOFF.md)** — Session resume protocol, HEAD SHA snapshot, and handoff state (required when resuming existing work).
6. **Routed Domain Documents** — Read only specific topic documents routed by `DOCUMENT_INDEX.md` relevant to the active task.

---

## 2. Core Governance Rules

### Repository Truth Rule
- GitHub repository commits, code, and documentation are the single source of truth.
- Repository state newer than documentation is authoritative.
- If repository truth proves a document stale, update documentation **ONLY** if that update falls within the currently authorized Work Package (WP).

### Bounded Execution Rule
- AI execution engines (Antigravity) MUST NOT exceed the scope of the currently authorized Work Package.
- Code implementation, frontend/backend logic, cloud resource provisioning, Vidu API calls, secret provisioning, and deployments are strictly prohibited unless explicitly authorized in the active WP.

### Authority Hierarchy
- **Project Owner:** Final human authority.
- **ChatGPT:** Control Plane / Project Lead / Architect / Independent Reviewer.
- **Antigravity:** Low-Credit / Bounded Execution Plane.
- **Codex / Claude Code:** STOP / Inactive.

---

## 3. Immediate Action Requirements

Upon starting a session:
1. Verify `CURRENT_STATE.md` to confirm the active Work Package.
2. Check `ACTIVE_TASK.md` for explicit constraints and stop conditions.
3. Check `CHAT_HANDOFF.md` to align on branch, HEAD SHA, and pending review status.
4. Do NOT start any unauthorized tasks.
