# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Active Work Package:** `P1-WP004 — Document Ingestion & Text Extraction Engine`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Status:** **IMPLEMENTED / WAITING CHATGPT REVIEW**
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Implement the fast, native document ingestion and text extraction engine:
1. **Lightweight Fast Native Extractors:** Provider-neutral `DocumentExtractor` interface with PyMuPDF (PDF), python-docx (DOCX), python-pptx (PPTX), and text-decoder (TXT, Markdown).
2. **Document Type Detector:** Conservative format detection combining magic headers, file extensions, and content-type metadata.
3. **No-OCR & Performance Principles:** Native text-layer extraction without local/cloud AI dependencies, OCR runtimes, or subprocess conversions.
4. **Normalized Result & Persistence:** `DocumentExtraction` database entity storing extracted text, segment structures, character counts, warnings, and `extraction_duration_ms`.
5. **Unicode & Safety:** Full preservation of Thai, English, Japanese, and mixed Unicode text; configurable document size, page count, and character limits.
6. **API Endpoints:** `/api/v1/assets/{asset_id}/extract` and `/api/v1/assets/{asset_id}/extraction`.
7. **Database Migration:** Alembic migration `003_add_document_extraction` supporting `upgrade head` -> `downgrade -1` -> `upgrade head`.
8. **Automated Testing:** Pytest suite covering all supported formats, Thai/Japanese Unicode, size/page limits, missing objects, and migration lifecycle.

---

## Strictly Enforced Constraints

> [!CAUTION]
> **BOUNDED EXECUTION & SCOPE PROTECTION**
> 
> The following actions are STRICTLY PROHIBITED in P1-WP004:
> - Starting P1-WP005 or any subsequent Work Package
> - Implementing local AI (Ollama, local LLM, local vision/OCR models)
> - Implementing cloud AI API integrations (OpenAI, Gemini, Vidu, Veo)
> - Implementing Story generation, script writing, translation, or summarization
> - Implementing frontend or web UI components
> - Implementing authentication, user management, or permission systems
> - Implementing audio, TTS, subtitles, FFmpeg, or media transcoding pipelines
> - Adding Redis, Celery, BullMQ, or extra infrastructure services

---

## Next Allowed Actions

1. ChatGPT Independent Review of P1-WP004 PR.
2. Project Owner review and sign-off.
