# Chat Session Handoff & Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

---

## 1. Post-Implementation State & Repository Snapshot

- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Branch:** `main`
- **Active Feature Branch:** `ai/p2-wp006-reference-library`
- **HANDOFF_BASE_SHA:** `a3cf384bc312eb257ef8b838922debdbc71bdc24` *(Repository commit SHA immediately preceding this WP commit)*
- **P0-WP001 Status:** `PASS / CLOSED`
- **P1-WP002 Status:** `PASS / MERGED`
- **P1-WP003 Status:** `PASS / MERGED`
- **P1-WP004 Status:** `PASS / MERGED`
- **P1-WP005 Status:** `PASS / MERGED`
- **P2-WP006 Status:** `IMPLEMENTED / WAITING CHATGPT REVIEW`
- **Phase:** `P2 — Multi-Modal Reference, Continuity & Scene Engine`
- **Active Work Package:** `P2-WP006`
- **Implementation Status:** `REFERENCE LIBRARY & CONTINUITY BIBLES IMPLEMENTED & TESTED`
- **Next Work Package:** `P2-WP007 — PROPOSED / NOT AUTHORIZED`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Next Allowed Action:** `ChatGPT review only`

---

## 2. Mandatory Handoff & Branch Rules

> [!IMPORTANT]
> **LIVE HEAD AUTHORITATIVE RULE & BRANCH SEMANTICS**
> 
> 1. **Live Branch HEAD is Authoritative:** Every new or resumed AI chat session MUST fresh-fetch the live branch HEAD from Git/GitHub (`git rev-parse HEAD`) before taking action.
> 2. **Session Base Branch:** When an authorized Work Package is active (`P2-WP006`), work takes place on the feature branch `ai/p2-wp006-reference-library`.
> 3. **Historical Baseline Context:** `HANDOFF_BASE_SHA` records the base repository SHA that was current immediately BEFORE the handoff/status document update commit was created. Mismatch between live branch HEAD and `HANDOFF_BASE_SHA` after handoff commits is expected and normal.
> 4. **No Recursive Commits:** Execution agents MUST NEVER create an additional commit solely to make a handoff SHA field match its own commit SHA.

---

## 3. Status of AI Engines

| Engine | Authorized Status | Permitted Scope |
| :--- | :--- | :--- |
| **ChatGPT** | **ACTIVE (Control Plane)** | Architect, lead, review, design approval, WP review. |
| **Antigravity** | **BOUNDED EXECUTION COMPLETE** | P2-WP006 implementation complete. Must STOP and await review. |
| **Codex** | **STOP** | Inactive. No authorization. |
| **Claude Code** | **STOP** | Inactive. No authorization. |

---

## 4. Completed Milestones & Current State

- **P0-WP001 Completed & Closed:** Governance and architecture foundation merged into `main`.
- **P1-WP002 Completed & Closed:** Backend core framework, SQLAlchemy domain entities, and database foundation merged into `main`.
- **P1-WP003 Completed & Closed:** Provider-neutral object storage abstraction, MinIO integration, and Asset API merged into `main`.
- **P1-WP004 Completed & Closed:** Fast document ingestion and text extraction engine merged into `main`.
- **P1-WP005 Completed & Closed:** Story & screenplay script generator service merged into `main` at commit `a3cf384bc312eb257ef8b838922debdbc71bdc24`.
- **P2-WP006 Implemented & Tested:**
  - ORM entities (`ProjectReference`, `CharacterBible`, `LocationBible`, `StyleBible`, `BrandBible`) and Alembic migration `005_add_reference_library_tables.py`.
  - `ReferenceService` providing full CRUD, cross-project asset validation (`INVALID_ASSET_LINK` 400), and lock safety (`REFERENCE_LOCKED` 409).
  - Zero-AI `ReferenceContextBuilder` assembling compact prioritized reference contexts bounded by 50,000 characters.
  - Prompt composer integration inserting locked reference context into WP005 prompts under `=== LOCKED PROJECT REFERENCES ===`.
  - Pytest suite (45 passing tests) covering reference library endpoints, lock behavior, context builder, prompt composer, and migration lifecycle.

---

## 5. Strict Prohibitions & Next Allowed Step

### Strictly Prohibited
- Do NOT start P2-WP007 or any subsequent Work Package.
- Do NOT implement local AI, vector DB/embeddings, Gemini LLM, image generation, video rendering (Vidu/Veo), or frontend code.
- Do NOT merge PR automatically.

### Next Allowed Step
The next allowed action is **ChatGPT Independent Review** and **Project Owner approval** for P2-WP006. Execution agents MUST STOP until review is completed.
