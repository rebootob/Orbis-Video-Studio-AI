# Chat Session Handoff & Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

---

## 1. Post-Implementation State & Repository Snapshot

- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Branch:** `main`
- **Active Feature Branch:** `ai/p1-wp004-document-ingestion`
- **HANDOFF_BASE_SHA:** `b9b3271655bda016b2dc57f5e8e00ff392f0eeae` *(Repository commit SHA immediately preceding this WP commit)*
- **P0-WP001 Status:** `PASS / CLOSED`
- **P1-WP002 Status:** `PASS / MERGED`
- **P1-WP003 Status:** `PASS / MERGED`
- **P1-WP004 Status:** `IMPLEMENTED / WAITING CHATGPT REVIEW`
- **Phase:** `P1 — Core Architecture & Data Engine`
- **Active Work Package:** `P1-WP004`
- **Implementation Status:** `FAST DOCUMENT INGESTION ENGINE IMPLEMENTED & TESTED`
- **Next Work Package:** `P1-WP005 — PROPOSED / NOT AUTHORIZED`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Next Allowed Action:** `ChatGPT review only`

---

## 2. Mandatory Handoff & Branch Rules

> [!IMPORTANT]
> **LIVE HEAD AUTHORITATIVE RULE & BRANCH SEMANTICS**
> 
> 1. **Live Branch HEAD is Authoritative:** Every new or resumed AI chat session MUST fresh-fetch the live branch HEAD from Git/GitHub (`git rev-parse HEAD`) before taking action.
> 2. **Session Base Branch:** When an authorized Work Package is active (`P1-WP004`), work takes place on the feature branch `ai/p1-wp004-document-ingestion`.
> 3. **Historical Baseline Context:** `HANDOFF_BASE_SHA` records the base repository SHA that was current immediately BEFORE the handoff/status document update commit was created. Mismatch between live branch HEAD and `HANDOFF_BASE_SHA` after handoff commits is expected and normal.
> 4. **No Recursive Commits:** Execution agents MUST NEVER create an additional commit solely to make a handoff SHA field match its own commit SHA.

---

## 3. Status of AI Engines

| Engine | Authorized Status | Permitted Scope |
| :--- | :--- | :--- |
| **ChatGPT** | **ACTIVE (Control Plane)** | Architect, lead, review, design approval, WP review. |
| **Antigravity** | **BOUNDED EXECUTION COMPLETE** | P1-WP004 implementation complete. Must STOP and await review. |
| **Codex** | **STOP** | Inactive. No authorization. |
| **Claude Code** | **STOP** | Inactive. No authorization. |

---

## 4. Completed Milestones & Current State

- **P0-WP001 Completed & Closed:** Governance and architecture foundation merged into `main`.
- **P1-WP002 Completed & Closed:** Backend core framework, SQLAlchemy domain entities, and database foundation merged into `main`.
- **P1-WP003 Completed & Closed:** Provider-neutral object storage abstraction, MinIO integration, and Asset API merged into `main`.
- **P1-WP004 Implemented & Tested:**
  - Fast native document extractors for PDF (PyMuPDF), DOCX (python-docx), PPTX (python-pptx), and TXT/Markdown (text-decoder).
  - Conservative DocumentTypeDetector combining magic headers, file extensions, and content-type metadata.
  - Strict performance-first & no-OCR/no-local-AI architecture principles.
  - `DocumentExtraction` model & Alembic migration `003_add_document_extraction` storing text, page/slide segments, character counts, warnings, and `extraction_duration_ms`.
  - Preservation of Thai, English, Japanese, and mixed Unicode scripts.
  - Endpoints `POST /api/v1/assets/{asset_id}/extract` and `GET /api/v1/assets/{asset_id}/extraction`.
  - Pytest suite (26 passing tests) covering format extractors, limits, error handling, and migration lifecycle.

---

## 5. Strict Prohibitions & Next Allowed Step

### Strictly Prohibited
- Do NOT start P1-WP005 or any subsequent Work Package.
- Do NOT implement local AI, Ollama, cloud AI APIs (OpenAI/Gemini/Vidu), story generation, script writing, or frontend code.
- Do NOT merge PR automatically.

### Next Allowed Step
The next allowed action is **ChatGPT Independent Review** and **Project Owner approval** for P1-WP004. Execution agents MUST STOP until review is completed.
