# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Active Work Package:** `P1-WP002 — Backend Core Framework & Domain Database Foundation`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Status:** **IMPLEMENTED / WAITING CHATGPT REVIEW**
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Implement the backend core framework and relational domain database foundation:
1. **FastAPI Application:** App bootstrap, `/health` and `/api/v1/health` endpoints returning HTTP 200 `{"status": "ok"}`.
2. **Configuration & Secrets:** Environment configuration via Pydantic Settings and `.env.example`.
3. **Database Foundation:** PostgreSQL connectivity, SQLAlchemy 2.x ORM declarative models, and Alembic migrations.
4. **Domain Entities:** `Project`, `Story`, `Scene`, `Shot`, `Asset`, `GenerationJob` with clean relationships.
5. **Developer Environment:** Docker Compose (`backend` + `db` PostgreSQL services).
6. **Automated Testing:** `pytest` suite covering health endpoints, domain models, and Alembic migration lifecycle (`upgrade head` -> `downgrade base` -> `upgrade head`).

---

## Strictly Enforced Constraints

> [!CAUTION]
> **BOUNDED EXECUTION & SCOPE PROTECTION**
> 
> The following actions are STRICTLY PROHIBITED in P1-WP002:
> - Starting P1-WP003 or any subsequent Work Package
> - Implementing Vidu, OpenAI, Gemini, or third-party AI provider API integrations
> - Implementing S3 object storage or file/media upload pipelines
> - Implementing PDF, Word, or PPTX document parsers
> - Implementing frontend or web UI components
> - Implementing authentication, user management, or permission systems
> - Implementing audio, TTS, subtitles, or FFmpeg rendering pipelines
> - Adding Redis, Celery, or BullMQ infrastructure

---

## Next Allowed Actions

1. ChatGPT Independent Review of P1-WP002 PR.
2. Project Owner review and sign-off.
