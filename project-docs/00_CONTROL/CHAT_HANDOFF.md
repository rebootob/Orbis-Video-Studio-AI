# Chat Session Handoff & Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

---

## 1. Post-Merge State & Repository Snapshot

- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Branch:** `main`
- **Active Branch:** `ai/p0-wp001-closure-sync`
- **P0-WP001 Status:** `PASS / CLOSED`
- **PR #1 Status:** `MERGED` ([https://github.com/rebootob/Orbis-Video-Studio-AI/pull/1](https://github.com/rebootob/Orbis-Video-Studio-AI/pull/1))
- **Approved Feature HEAD:** `cd34ae01536c61cae628660cc814946ebc7596fe`
- **Main HEAD After Merge:** `4eddc44f0733f6d8e6e9772090183b3b3f4c3194`
- **HANDOFF_BASE_SHA:** `4eddc44f0733f6d8e6e9772090183b3b3f4c3194` *(Repository commit SHA immediately preceding this handoff update)*
- **Phase:** `P0 — Foundation & Governance`
- **Active Work Package:** `NONE`
- **Implementation Status:** `NOT STARTED`
- **Next Work Package:** `P1-WP002 — PROPOSED / NOT AUTHORIZED`
- **Current Gate:** `WAITING OWNER APPROVAL FOR NEXT WP`
- **Next Allowed Action:** `ChatGPT planning / Owner approval for P1-WP002 only`

---

## 2. Mandatory Handoff & SHA Rules

> [!IMPORTANT]
> **LIVE HEAD AUTHORITATIVE RULE & HANDOFF_BASE_SHA SEMANTICS**
> 
> 1. **Live Branch HEAD is Authoritative:** Every new or resumed AI chat session MUST fresh-fetch the live branch HEAD from Git/GitHub (`git rev-parse HEAD`) before taking action.
> 2. **Historical Baseline Context:** `HANDOFF_BASE_SHA` records the base repository SHA that was current immediately BEFORE the handoff/status document update commit was created.
> 3. **Expected Mismatch:** A mismatch between live branch HEAD and `HANDOFF_BASE_SHA` is expected and normal whenever the handoff document itself was committed after `HANDOFF_BASE_SHA`.
> 4. **No Recursive Commits:** Execution agents MUST NEVER create an additional commit solely to make a handoff SHA field match its own commit SHA.

---

## 3. Status of AI Engines

| Engine | Authorized Status | Permitted Scope |
| :--- | :--- | :--- |
| **ChatGPT** | **ACTIVE (Control Plane)** | Architect, lead, review, design approval, WP planning. |
| **Antigravity** | **STOP** | Execution stopped upon P0-WP001 closure sync PR push. Must STOP. |
| **Codex** | **STOP** | Inactive. No authorization. |
| **Claude Code** | **STOP** | Inactive. No authorization. |

---

## 4. Completed Milestones & Current State

- **P0-WP001 Completed & Closed:** Initial project governance, system architecture, product models, and delivery roadmap established and merged into `main` via PR #1 (`4eddc44f0733f6d8e6e9772090183b3b3f4c3194`).
- **Post-Merge Closure Sync:** Control plane documentation updated to reflect PR #1 merge state and active WP status as `NONE`.
- **Application Code:** 0% implemented; zero cloud resources provisioned.

---

## 5. Strict Prohibitions & Next Allowed Step

### Strictly Prohibited
- Do NOT start P1-WP002 or any subsequent Work Package.
- Do NOT write any application code, frontend/backend logic, or provision cloud resources.
- Do NOT make API calls to Vidu or any AI generation provider.

### Next Allowed Step
The next allowed action is **ChatGPT planning** and **Project Owner review/approval** for P1-WP002. Execution agents MUST STOP until P1-WP002 is formally authorized by the Project Owner.
