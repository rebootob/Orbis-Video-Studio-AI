# P4-WP020-LIVE-R5-PRE1 — NO-PAID Readiness / Preflight Tooling Preparation

## Status

```text
TYPE: NO-PAID / READINESS-PREFLIGHT / TOOLING-ONLY
OWNER_AUTHORIZED: YES (Issue #63 comment 5600206595)
EXECUTION_CONTRACT: Issue #63 comment 5600227540
CANONICAL_BASE_MAIN: 8c8eb871b6d2a0522b1764c4d5e1eeae0ea1e822
BRANCH: ai/p4-wp020-live-r5-pre1
READINESS_IDENTITY: WP020-LIVE-R5-PRE1
PROVIDER_GENERATION_AUTHORIZED: NO
PAID_PROVIDER_CALLS: 0
VIDU_CREDITS_CONSUMED: 0
SPEND_AUTHORIZED: USD 0.00
PAID_EXECUTION_FENCE: NONE / NOT WRITTEN
PAID_EXECUTION_AUTHORIZED: NO
CORE_V1_RELEASE: NOT DECLARED
```

## Purpose

Prepare dedicated, immutable NO-PAID readiness/preflight tooling for R5 following Owner authorization in Issue #63 (comment 5600206595) and execution contract (comment 5600227540).

This package prepares and verifies tooling only. It MUST NOT:
- dispatch provider generation requests;
- consume Vidu credits;
- make paid provider calls;
- write an execution fence or paid authorization marker;
- dispatch paid/live workflows;
- declare Core V1 release.

## Delivered Tooling

1. `.github/workflows/wp020-live-r5-pre1.yml`
   - Manual `workflow_dispatch` only;
   - Scoped strictly to canonical `main`;
   - Read-only permissions (`contents: read`);
   - Ephemeral PostgreSQL 16 service + `alembic upgrade head`;
   - Ephemeral MinIO container + health-check verification;
   - Rerun no-paid guards: credentials presence, adapter configuration, pricing estimation, object storage, zero-job/zero-ledger DB verification;
   - Cannot write execution fence or comment on issues (`issues: write` omitted).

2. `.github/scripts/wp020_live_r5_pre1.py`
   - Pure preflight/readiness script without provider generation methods;
   - Validates credential presence for `OPENAI_API_KEY`, `GEMINI_API_KEY`, `VIDU_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_DEFAULT_VOICE_ID` without leaking secret values;
   - Validates production adapter constructors and `.validate_config({})` without making generation calls;
   - Validates local pricing estimator for all 6 sequential provider targets and USD 1.00 reservation ceiling;
   - Verifies ephemeral object storage write/read/delete;
   - Verifies clean starting DB state (0 usage ledger rows, 0 generation jobs);
   - Records Owner-provided Vidu 2,000 credits as readiness evidence only (no conversion to USD);
   - Reports explicit metrics: `provider_generation_calls = 0`, `paid_provider_calls = 0`, `vidu_credits_consumed = 0`, `paid_fence_written = false`, `paid_live_dispatch = false`.

3. `backend/tests/test_wp020_live_r5_pre1_contract.py`
   - Static AST validation that `wp020_live_r5_pre1.py` contains no forbidden generation calls (`generate_story`, `generate_image`, `generate_video`, `generate_audio`, `submit_generation`, `create_task`);
   - Workflow trigger assertion (`workflow_dispatch:` only, no `push:`, no `pull_request:`, no `issues: write`);
   - Zero-call / zero-consumption metric assertions.

## Invariant and Safety Enforcement

- **Immutable R4 Separation:** R4 scripts and workflows are completely untouched. R4 remains STOPPED / CONSUMED / NEVER RERUN.
- **Readiness Identity Only:** `WP020-LIVE-R5-PRE1` is used exclusively for readiness. No paid R5 execution identity is created.
- **No Paid Fence / Marker:** No `EXECUTION_STARTED` or `FRESH_OWNER_AUTHORIZED` marker is generated or written.
- **Vidu Credit Policy:** Owner-provided balance of 2,000 credits is documented as manual readiness evidence only. It is never converted to USD or treated as generation proof.
- **Fail Closed:** Any missing credential, invalid config, UNKNOWN pricing, DB migration error, or storage failure aborts immediately.

## Status Summary

```text
P4-WP020-LIVE-R5-PRE1: TOOLING PREPARED / NO-PAID
R4 RUN1: STOPPED / CONSUMED / NEVER RERUN
R5 PAID EXECUTION: NOT AUTHORIZED
CORE_V1_RELEASE: NOT DECLARED
```
