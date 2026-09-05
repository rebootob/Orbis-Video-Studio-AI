# Chat Session Handoff & Protocol

> **Canonical Document Location:** [`project-docs/00_CONTROL/CHAT_HANDOFF.md`](project-docs/00_CONTROL/CHAT_HANDOFF.md)

---

## 1. Post-Implementation State & Repository Snapshot

- **Repository:** `rebootob/Orbis-Video-Studio-AI`
- **Canonical Branch:** `main`
- **Active Feature Branch:** `ai/p1-wp005-story-script-generator`
- **HANDOFF_BASE_SHA:** `d8eba293823734a05b1ed20f78ce9c5bbbd2a48e` *(Repository commit SHA immediately preceding this WP commit)*
- **P0-WP001 Status:** `PASS / CLOSED`
- **P1-WP002 Status:** `PASS / MERGED`
- **P1-WP003 Status:** `PASS / MERGED`
- **P1-WP004 Status:** `PASS / MERGED`
- **P1-WP005 Status:** `IMPLEMENTED / WAITING CHATGPT REVIEW`
- **Phase:** `P1 — Core Architecture & Data Engine`
- **Active Work Package:** `P1-WP005`
- **Implementation Status:** `STORY & SCRIPT GENERATOR SERVICE IMPLEMENTED & TESTED`
- **Next Work Package:** `P2-WP006 — PROPOSED / NOT AUTHORIZED`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Next Allowed Action:** `ChatGPT review only`

---

## 2. Mandatory Handoff & Branch Rules

> [!IMPORTANT]
> **LIVE HEAD AUTHORITATIVE RULE & BRANCH SEMANTICS**
> 
> 1. **Live Branch HEAD is Authoritative:** Every new or resumed AI chat session MUST fresh-fetch the live branch HEAD from Git/GitHub (`git rev-parse HEAD`) before taking action.
> 2. **Session Base Branch:** When an authorized Work Package is active (`P1-WP005`), work takes place on the feature branch `ai/p1-wp005-story-script-generator`.
> 3. **Historical Baseline Context:** `HANDOFF_BASE_SHA` records the base repository SHA that was current immediately BEFORE the handoff/status document update commit was created. Mismatch between live branch HEAD and `HANDOFF_BASE_SHA` after handoff commits is expected and normal.
> 4. **No Recursive Commits:** Execution agents MUST NEVER create an additional commit solely to make a handoff SHA field match its own commit SHA.

---

## 3. Status of AI Engines

| Engine | Authorized Status | Permitted Scope |
| :--- | :--- | :--- |
| **ChatGPT** | **ACTIVE (Control Plane)** | Architect, lead, review, design approval, WP review. |
| **Antigravity** | **BOUNDED EXECUTION COMPLETE** | P1-WP005 implementation complete. Must STOP and await review. |
| **Codex** | **STOP** | Inactive. No authorization. |
| **Claude Code** | **STOP** | Inactive. No authorization. |

---

## 4. Completed Milestones & Current State

- **P0-WP001 Completed & Closed:** Governance and architecture foundation merged into `main`.
- **P1-WP002 Completed & Closed:** Backend core framework, SQLAlchemy domain entities, and database foundation merged into `main`.
- **P1-WP003 Completed & Closed:** Provider-neutral object storage abstraction, MinIO integration, and Asset API merged into `main`.
- **P1-WP004 Completed & Closed:** Fast document ingestion and text extraction engine merged into `main`.
- **P1-WP005 Implemented & Tested:**
  - `CreativeGenerationProvider` abstract interface with OpenAI (`OpenAICreativeGenerationProvider`) implementation and zero-credit test double (`FakeCreativeGenerationProvider`).
  - Deterministic prompt composer layer (`StoryPromptComposer`, `ScenePromptComposer`, `ShotPromptComposer`) separating factual source extractions from creative direction.
  - Story, Scene, and Shot generation with Thai & English Unicode preservation and image/video prompt creation.
  - Lock protection preventing accidental overwrite of entities marked `is_locked=True`.
  - Schema extensions and Alembic migration `004_add_story_script_fields` plus `GenerationAuditLog` table.
  - Endpoints `/projects/{project_id}/story/generate`, `/stories/{story_id}/scenes/generate`, `/scenes/{scene_id}/shots/generate`, `/projects/{project_id}/story`.
  - Pytest suite (37 passing tests) covering story generation, lock safety, Unicode, error status mappings, and Alembic migration lifecycle.

---

## 5. Strict Prohibitions & Next Allowed Step

### Strictly Prohibited
- Do NOT start P2-WP006 or any subsequent Work Package.
- Do NOT implement Gemini LLM, image generation, video rendering (Vidu/Veo), audio/TTS, or frontend code.
- Do NOT merge PR automatically.

### Next Allowed Step
The next allowed action is **ChatGPT Independent Review** and **Project Owner approval** for P1-WP005. Execution agents MUST STOP until review is completed.
