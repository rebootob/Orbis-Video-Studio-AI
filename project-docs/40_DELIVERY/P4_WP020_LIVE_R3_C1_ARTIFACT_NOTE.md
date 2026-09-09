# P4-WP020-LIVE-R3-C1 — STOP Artifact Evidence Note

This note records the C1 artifact-boundary corrective only.

- `GenerationJob.result` may retain only the authorized sanitized Gemini 429 fields.
- `.github/scripts/wp020_live_r3_contract.py::sanitize_generation_job` applies a second allowlist before any STOP artifact copies those fields out of the ephemeral database.
- Allowed nested quota fields are limited to metric, quota id, quota value, model, and location.
- Provider message text, raw body, headers, prompt, API keys, arbitrary project dimensions, descriptions, and unknown detail objects remain excluded.
- This change performs no provider I/O and does not authorize or modify any R3/R4 paid execution workflow.
