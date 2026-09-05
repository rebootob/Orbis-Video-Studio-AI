# Chat Session Handoff & Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

---

## 1. Post-Merge State & Repository Snapshot

- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Branch:** `main`
- **Operational Active Branch:** `NONE`
- **Closure Sync Branch:** `ai/p0-wp001-closure-sync` *(Historical / PR #2 only)*
- **Pull Request:** `#2` ([https://github.com/rebootob/Orbis-Video-Studio-AI/pull/2](https://github.com/rebootob/Orbis-Video-Studio-AI/pull/2))
- **HANDOFF_BASE_SHA:** `def4a9ba4a5fb0f4238597a59d31a128cd2ca05a` *(Repository commit SHA immediately preceding this handoff update)*
- **P0-WP001 Status:** `PASS / CLOSED`
- **Phase:** `P0 — Foundation & Governance`
- **Active Work Package:** `NONE`
- **Implementation Status:** `NOT STARTED`
- **Next Work Package:** `P1-WP002 — PROPOSED / NOT AUTHORIZED`
- **Current Gate:** `WAITING OWNER APPROVAL FOR NEXT WP`
- **Next Allowed Action:** `ChatGPT review / Owner decision only`

---

## 2. Mandatory Handoff & Branch Rules

> [!IMPORTANT]
> **LIVE HEAD AUTHORITATIVE RULE & BRANCH SEMANTICS**
> 
> 1. **Live Branch HEAD is Authoritative:** Every new or resumed AI chat session MUST fresh-fetch the live branch HEAD from Git/GitHub (`git rev-parse HEAD`) before taking action.
> 2. **Session Base Branch:** When no Work Package is active (`ACTIVE WORK PACKAGE: NONE`), new AI sessions MUST start from fresh-fetched `main`.
> 3. **Historical Closure Branches:** A historical closure/review branch (such as `ai/p0-wp001-closure-sync`) MUST NEVER be treated as an operationally active execution branch.
> 4. **Feature Branch Creation:** A new feature branch is created ONLY after the Project Owner explicitly authorizes a new Work Package.
> 5. **Historical Baseline Context:** `HANDOFF_BASE_SHA` records the base repository SHA that was current immediately BEFORE the handoff/status document update commit was created. Mismatch between live branch HEAD and `HANDOFF_BASE_SHA` after handoff commits is expected and normal.
> 6. **No Recursive Commits:** Execution agents MUST NEVER create an additional commit solely to make a handoff SHA field match its own commit SHA.

---

## 3. Status of AI Engines

| Engine | Authorized Status | Permitted Scope |
| :--- | :--- | :--- |
| **ChatGPT** | **ACTIVE (Control Plane)** | Architect, lead, review, design approval, WP planning. |
| **Antigravity** | **STOP AFTER THIS CORRECTIVE PUSH** | Execution stopped upon pushing PR #2 correction. Must STOP. |
| **Codex** | **STOP** | Inactive. No authorization. |
| **Claude Code** | **STOP** | Inactive. No authorization. |

---

## 4. Completed Milestones & Current State

- **P0-WP001 Completed & Closed:** Initial project governance, system architecture, product models, and delivery roadmap established and merged into `main` via PR #1 (`4eddc44f0733f6d8e6e9772090183b3b3f4c3194`).
- **Post-Merge Closure Sync:** Control plane documentation updated via PR #2 to reflect PR #1 merge state, active WP status as `NONE`, and operational active branch as `NONE`.
- **Application Code:** 0% implemented; zero cloud resources provisioned.

---

## 5. Strict Prohibitions & Next Allowed Step

### Strictly Prohibited
- Do NOT start P1-WP002 or any subsequent Work Package.
- Do NOT write any application code, frontend/backend logic, or provision cloud resources.
- Do NOT make API calls to Vidu or any AI generation provider.

### Next Allowed Step
The next allowed action is **ChatGPT review** and **Project Owner decision** for P1-WP002. Execution agents MUST STOP until P1-WP002 is formally authorized by the Project Owner.
