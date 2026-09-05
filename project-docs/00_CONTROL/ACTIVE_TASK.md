# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Active Work Package:** `P1-WP005 — Story & Screenplay Script Generator Service`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Status:** **IMPLEMENTED / WAITING CHATGPT REVIEW**
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Implement the Story and Screenplay Script Generator Service:
1. **Provider Isolation Architecture:** Provider-neutral `CreativeGenerationProvider` interface with OpenAI `OpenAICreativeGenerationProvider` implementation and `FakeCreativeGenerationProvider` test double.
2. **Deterministic Prompt Composers:** Reusable `StoryPromptComposer`, `ScenePromptComposer`, and `ShotPromptComposer` modules separating factual source material from creative direction.
3. **Structured JSON Output:** Structured story, scene, and shot generation with Thai and English script support.
4. **WP004 Ingestion Integration:** Feed extracted document text into prompt factual context.
5. **Lock Protection:** Respect `is_locked` flags on `Story`, `Scene`, and `Shot` entities to reject accidental overwrites.
6. **Schema Extensions & Audit Logging:** Extended Story/Scene/Shot fields and Alembic migration `004_add_story_script_fields` plus `GenerationAuditLog` table.
7. **API Endpoints:** `/projects/{project_id}/story/generate`, `/stories/{story_id}/scenes/generate`, `/scenes/{scene_id}/shots/generate`, `/projects/{project_id}/story`.
8. **Automated Testing:** Pytest suite (37 passing tests) covering story generation, lock safety, Unicode, error status mappings, and Alembic migration lifecycle.

---

## Strictly Enforced Constraints

> [!CAUTION]
> **BOUNDED EXECUTION & SCOPE PROTECTION**
> 
> The following actions are STRICTLY PROHIBITED in P1-WP005:
> - Starting P2-WP006 or any subsequent Work Package
> - Implementing local AI (Ollama, local LLM, local vision models)
> - Implementing Gemini creative LLM or Gemini media generation
> - Implementing Vidu, Veo, image generation, video generation, or audio/TTS rendering
> - Implementing frontend or web UI components
> - Merging PR automatically

---

## Next Allowed Actions

1. ChatGPT Independent Review of P1-WP005 PR.
2. Project Owner review and sign-off.
