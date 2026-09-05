# Core Domain Model & Schemas

> **Canonical Document Location:** [`project-docs/20_ARCHITECTURE/DOMAIN_MODEL.md`](project-docs/20_ARCHITECTURE/DOMAIN_MODEL.md)

---

## 1. Domain Entity Relationship Diagram

```mermaid
erDiagram
    PROJECT ||--o{ DOCUMENT : ingests
    PROJECT ||--11 STORY : contains
    STORY ||--11 SCRIPT : generates
    SCRIPT ||--o{ SCENE : divides_into
    SCENE ||--o{ SHOT : contains
    PROJECT ||--o{ REFERENCE_ASSET : owns
    SHOT ||--o{ SHOT_REFERENCE : links
    SHOT ||--11 SHOT_LOCK : maintains
    PROJECT ||--o{ AUDIO_TRACK : includes
    PROJECT ||--11 EDIT_TIMELINE : orchestrates
    PROJECT ||--o{ GENERATION_JOB : records
    PROJECT ||--o{ OUTPUT_PRESET : configures
    OUTPUT_PRESET ||--o{ RENDER_JOB : executes
```

---

## 2. Core Entity Specifications

### `Project`
Root container for a video production story.
- `id` (UUID): Primary key.
- `title` (String): Project title.
- `description` (Text): Brief / initial prompt.
- `default_config` (JSON): Global default settings (aspect ratio, style preset, default provider, cost ceiling).
- `status` (Enum): `DRAFT`, `STORY_GENERATED`, `SCRIPT_APPROVED`, `GENERATING_SHOTS`, `IN_EDITING`, `COMPLETED`, `ARCHIVED`.
- `created_at`, `updated_at` (Timestamp).

### `Document`
Uploaded source files (Brief, Word, PDF, PowerPoint).
- `id` (UUID): Primary key.
- `project_id` (UUID): FK to Project.
- `file_name` (String): Original file name.
- `file_type` (Enum): `PDF`, `DOCX`, `PPTX`, `TXT`, `MD`.
- `storage_path` (String): Object storage key.
- `extracted_text` (Text): Parsed text payload.

### `Story`
High-level narrative outline derived from Brief/Documents.
- `id` (UUID): Primary key.
- `project_id` (UUID): FK to Project.
- `logline` (Text): One-sentence story logline.
- `synopsis` (Text): Full narrative synopsis.
- `genre` (String): Cinematic style / genre.
- `status` (Enum): `DRAFT`, `LOCKED`.

### `Script` & `Scene` & `Shot`
- **`Script`**: Full formatted screenplay text.
- **`Scene`**: Narrative location/time scene block (`scene_number`, `heading`, `location_ref_id`, `description`, `locked`).
- **`Shot`**: Individual camera shot block.
  - `shot_number` (Integer).
  - `shot_type` (Enum): `AI_GENERATED`, `IMPORTED_VIDEO`, `IMPORTED_IMAGE`, `RECORDED_FOOTAGE`, `STOCK_ASSET`, `MIXED`.
  - `visual_prompt` (Text): Prompt sent to provider.
  - `duration_seconds` (Float): Shot duration.
  - `camera_motion` (String): Pan, tilt, zoom, dolly spec.
  - `provider_config` (JSON): Provider-specific settings (e.g. Vidu seed, motion score).
  - `media_asset_url` (String): Storage URL for generated/imported shot clip.
  - `status` (Enum): `PENDING`, `GENERATING`, `COMPLETED`, `FAILED`, `LOCKED`.

### `ReferenceAsset`
Centralized character, location, prop, or style reference item.
- `id` (UUID): Primary key.
- `project_id` (UUID): FK to Project.
- `asset_type` (Enum): `CHARACTER`, `LOCATION`, `DOCUMENT`, `PROP`, `BRAND`, `STYLE`, `IMAGE`, `EXISTING_SHOT`, `AUDIO`.
- `name` (String): Character/location name.
- `description` (Text): Text description.
- `media_urls` (Array of Strings): Reference image/audio storage paths.
- `embedding_data` (JSON): Feature vector metadata for visual consistency.

### `AssetLock`
Lock state tracker protecting approved entities from accidental regeneration.
- `entity_type` (Enum): `SCRIPT`, `SCENE`, `SHOT`, `CHARACTER`, `LOCATION`, `VOICE`, `TIMING`.
- `entity_id` (UUID): Target entity ID.
- `is_locked` (Boolean): Lock status flag.
- `locked_by` (String): User/agent identifier.
- `locked_at` (Timestamp).

### `AudioTrack` & `EditTimeline`
- **`AudioTrack`**: Dialogue, VO, BGM, SFX audio stems with ducking parameters (`track_type`, `media_url`, `start_time`, `volume_db`, `ducking_ratio`).
- **`EditTimeline`**: Master sequence track layout mapping shots and audio stems onto time axes.

### `GenerationJob` & `CostRecord`
- **`GenerationJob`**: Provider API invocation record (`provider_name`, `job_id`, `status`, `cost_usd`, `idempotency_key`).
- **`CostRecord`**: Granular usage ledger auditing provider charges per shot.
