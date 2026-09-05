# Chat Session Handoff & Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

---

## 1. Post-PR State & Repository Snapshot

- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Branch:** `main`
- **Active Branch:** `ai/p0-wp001-doc-foundation`
- **Pull Request:** `#1` ([https://github.com/rebootob/Orbis-Video-Studio-AI/pull/1](https://github.com/rebootob/Orbis-Video-Studio-AI/pull/1))
- **HANDOFF_BASE_SHA:** `7969fa1e34787814bd6ff80fbb90e9011d62e994` *(Repository commit SHA immediately preceding this handoff update)*
- **Phase:** `P0 — Foundation & Governance`
- **Active Work Package:** `P0-WP001 — Project Governance & Architecture Documentation Foundation`
- **Current Gate:** `CHATGPT INDEPENDENT CORRECTIVE REVIEW`
- **Documentation:** `COMPLETE / CORRECTIVE APPLIED`
- **Implementation:** `NOT AUTHORIZED`
- **Next WP:** `DO NOT START`
- **Next Allowed Action:** `ChatGPT review only`

---

## 2. Mandatory Handoff & SHA Rules

> [!IMPORTANT]
> **LIVE HEAD AUTHORITATIVE RULE & HANDOFF_BASE_SHA SEMANTICS**
> 
> 1. **Live Branch HEAD is Authoritative:** Every new or resumed AI chat session MUST fresh-fetch the live branch HEAD from Git/GitHub (`git rev-parse HEAD`) before taking action.
> 2. **Historical Context Only:** `HANDOFF_BASE_SHA` records the base repository SHA that was current immediately BEFORE the handoff/status document update commit was created.
> 3. **Expected Mismatch:** A mismatch between live branch HEAD and `HANDOFF_BASE_SHA` is expected and normal whenever the handoff document itself was committed after `HANDOFF_BASE_SHA`.
> 4. **No Recursive Commits:** Execution agents MUST NEVER create an additional commit solely to make a handoff SHA field match its own commit SHA.

---

## 3. Status of AI Engines

| Engine | Authorized Status | Permitted Scope |
| :--- | :--- | :--- |
| **ChatGPT** | **ACTIVE (Control Plane)** | Architect, lead, review, design approval, independent review. |
| **Antigravity** | **STOP AFTER CORRECTIVE PUSH** | Bounded execution complete for P0-WP001 corrective pass. Must STOP. |
| **Codex** | **STOP** | Inactive. No authorization. |
| **Claude Code** | **STOP** | Inactive. No authorization. |

---

## 4. Completed Corrective Actions

- Corrected Handoff SHA semantics: replaced self-invalidating "Current HEAD SHA" concept with `HANDOFF_BASE_SHA` and established live Git HEAD authority rules across all control documents.
- Corrected V1 Integration Scope distinction: preserved Integration Architecture Readiness (REST API boundary, webhooks, auth, permissions, audit, idempotency) as a locked V1 design requirement, while clarifying that full operational Hermes/n8n Integration Gateway implementation is POST-CORE V1 / V1.x.
- Replaced ALL local machine-specific links (`file:///c:/...`) with repository-relative Markdown links across all 27 documentation files.
- Clarified technology selection parameters across architectural documents by explicitly distinguishing **REQUIRED CAPABILITY**, **RECOMMENDED CANDIDATE**, and **TBD / NOT YET LOCKED**.
- Committed corrective changes to `ai/p0-wp001-doc-foundation` and pushed to PR `#1`.

---

## 5. Strict Prohibitions & Next Allowed Step

### Strictly Prohibited
- Do NOT merge PR `#1` automatically.
- Do NOT start P0-WP002 or any subsequent Work Package.
- Do NOT write any application code, frontend/backend logic, or provision cloud resources.

### Next Allowed Step
After pushing corrective commit to PR `#1`, execution engine (Antigravity) MUST STOP immediately. The next allowed action is **ChatGPT Independent Corrective Review** and Project Owner approval.
