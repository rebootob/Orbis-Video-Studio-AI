# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Active Work Package:** `P2-WP007 — Vidu Provider Adapter & Durable Job Dispatch Queue`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Status:** **IMPLEMENTED / WAITING CHATGPT REVIEW**
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Implement Vidu Provider Adapter & Durable Job Dispatch Queue:
1. **Provider Abstraction:** `IVideoGenerationProviderAdapter`, `VideoGenerationParams`, `ProviderJobResult`, `ProviderFactory`.
2. **Vidu Provider Adapter:** `ViduProviderAdapter` aligned with official Vidu v2 API (`Token` auth, explicit `text2video` and `reference2video` mappings, creations status polling, cancel).
3. **Durable DB Job Queue:** Real DB-backed atomic claim, restart recovery, retry classification (network/429/5xx retry vs 400/401/403/rejection no-retry), bounded retry and bounded polling, no Redis/Celery.
4. **Idempotency & Concurrency:** DB-level uniqueness constraint on `(shot_id, idempotency_key)`, safe race handling, no duplicate provider submission after restart.
5. **Secret & Error Safety:** Sanitization of keys/tokens/credentials in logs, errors, and DB results; no raw provider payloads persisted blindly.
6. **Output Asset Safety:** Provider output URL kept in job/result; no fabricated Asset records with zero file size or dummy checksums.
7. **Migrations & Tests:** Alembic migration 006 updating generation_jobs; 100% mocked HTTP pytest test suite with full backend regression.

---

## Strictly Enforced Constraints

> [!CAUTION]
> **BOUNDED EXECUTION & SCOPE PROTECTION**
> 
> The following actions are STRICTLY PROHIBITED in P2-WP007:
> - Starting P2-WP008 or any subsequent Work Package
> - Using live Vidu credits / making live unmocked HTTP requests
> - Introducing Redis, Celery, or external queue brokers
> - Implementing frontend or web UI components
> - Merging PR automatically or force pushing

---

## Next Allowed Actions

1. ChatGPT Independent Review of P2-WP007 PR #15.
2. Project Owner review and sign-off.

