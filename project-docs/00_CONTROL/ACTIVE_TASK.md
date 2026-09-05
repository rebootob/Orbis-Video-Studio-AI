# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Active Work Package:** `P2-WP006 — Reference Library & Character/Location Bibles`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Status:** **IMPLEMENTED / WAITING CHATGPT REVIEW**
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Implement the Reference Library and Character/Location Bibles:
1. **Domain Models & Schemas:** Defined `ProjectReference`, `CharacterBible`, `LocationBible`, `StyleBible`, and `BrandBible` ORM models and Pydantic schemas.
2. **Alembic Migration:** `005_add_reference_library_tables.py` creating all 5 reference tables.
3. **Reference Service:** `ReferenceService` enforcing CRUD operations, cross-project asset link validation (raising `INVALID_ASSET_LINK` 400), and `is_locked` enforcement (raising `REFERENCE_LOCKED` 409).
4. **Deterministic Reference Context Builder:** `ReferenceContextBuilder` assembling compact prioritized reference contexts (Factual Docs -> Locked Bibles -> Brand/Style -> Project References) bounded by `MAX_REFERENCE_CONTEXT_CHARACTERS = 50000`.
5. **Prompt Composer Integration:** Integrated locked reference context into WP005 prompt composers (`StoryPromptComposer`, `ScenePromptComposer`, `ShotPromptComposer`) under `=== LOCKED PROJECT REFERENCES ===`.
6. **API Endpoints:** REST endpoints for project references, characters, locations, styles, and brands under `/api/v1/projects/{project_id}/...` and `/api/v1/...`.
7. **Automated Testing:** Pytest suite (45 total passing tests) covering CRUD, lock protection, asset link validation, context prioritization/bounding, and Unicode preservation.

---

## Strictly Enforced Constraints

> [!CAUTION]
> **BOUNDED EXECUTION & SCOPE PROTECTION**
> 
> The following actions are STRICTLY PROHIBITED in P2-WP006:
> - Starting P2-WP007 or any subsequent Work Package
> - Implementing local AI or vector DB/embeddings
> - Implementing media generation (Gemini, Vidu, Veo rendering)
> - Implementing frontend or web UI components
> - Merging PR automatically

---

## Next Allowed Actions

1. ChatGPT Independent Review of P2-WP006 PR.
2. Project Owner review and sign-off.
