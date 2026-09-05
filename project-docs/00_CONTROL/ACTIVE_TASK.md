# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Active Work Package:** `P1-WP003 — S3-Compatible Object Storage & Asset Management API`
- **Current Gate:** `CHATGPT INDEPENDENT REVIEW`
- **Status:** **IMPLEMENTED / WAITING CHATGPT REVIEW**
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Implement the S3-compatible object storage and Asset Management API foundation:
1. **Provider-Neutral Storage Architecture:** Abstract `ObjectStorageProvider` interface with S3-compatible adapter (`S3CompatibleObjectStorageProvider`).
2. **Asset Management API:** `/api/v1/assets/upload`, `/api/v1/assets/{asset_id}`, `/api/v1/assets/{asset_id}/download`, `/api/v1/assets/{asset_id}`, `/api/v1/projects/{project_id}/assets`.
3. **Asset Metadata & Database Schema:** Alembic migration `002_asset_object_storage_metadata` supporting `original_filename`, `content_type`, `file_size_bytes`, `checksum_sha256`, `storage_bucket`, `storage_key`.
4. **Server-Generated Safe Keys & Safety:** Key pattern `projects/{project_id}/assets/{asset_id}/{sanitized_filename}`, SHA-256 checksums, non-empty file and size validation.
5. **Presigned Private Access:** Presigned access URLs for download without public bucket exposure.
6. **Developer Environment & MinIO:** Local MinIO service in Docker Compose for integration testing.
7. **Automated Testing:** Pytest suite covering storage providers, upload/download/delete lifecycle, validation, and migration lifecycle.

---

## Strictly Enforced Constraints

> [!CAUTION]
> **BOUNDED EXECUTION & SCOPE PROTECTION**
> 
> The following actions are STRICTLY PROHIBITED in P1-WP003:
> - Starting P1-WP004 or any subsequent Work Package
> - Implementing Vidu, OpenAI, Gemini, or third-party AI provider API integrations
> - Implementing PDF, Word, or PPTX document parsers or OCR
> - Implementing frontend or web UI components
> - Implementing authentication, user management, or permission systems
> - Implementing audio, TTS, subtitles, FFmpeg, or media transcoding pipelines
> - Adding Redis, Celery, BullMQ, or extra infrastructure services

---

## Next Allowed Actions

1. ChatGPT Independent Review of P1-WP003 PR.
2. Project Owner review and sign-off.
