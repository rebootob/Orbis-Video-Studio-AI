# P4-WP020-LIVE-R5-VIDU2-PREP-CLOSE — DOCS-ONLY Post-Merge Control Closure Sync

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU2-PREP-CLOSE
TYPE: DOCS-ONLY Post-Merge Control Closure Sync
OWNER_AUTHORIZED: YES (Issue #63 comment 5617902191)
CANONICAL_MAIN_SHA: fb72d683c0dd4daa721507b6a0c12dcec17d7366
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-prep-close
MERGED_IMPLEMENTATION_GATE: P4-WP020-LIVE-R5-VIDU2-PREP
VIDU2_PREP_MERGED_PR: #96
VIDU2_PREP_REVIEWED_HEAD: 8dce19e7dbd0ffba0bf358c6bbc59cbdb87e7076
VIDU2_PREP_MERGE_COMMIT: fb72d683c0dd4daa721507b6a0c12dcec17d7366
CLOSURE_PR: #97 (POST-MERGE TARGET: PASS / MERGED / COMPLETE; IN-FLIGHT: OPEN / IN REVIEW / NOT MERGED)

ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: WAITING_FOR_EXPLICIT_OWNER_NEXT_GATE
NEXT_GATE: OWNER DECISION REQUIRED

LAST_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU2-PREP
LAST_COMPLETED_STATUS: PASS / MERGED / COMPLETE (PR #96)
PREV_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1-CLOSE
PREV_COMPLETED_STATUS: PASS / MERGED / COMPLETE (PR #95)
PREV2_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1
PREV2_COMPLETED_STATUS: PASS / MERGED / COMPLETE (PR #94)

P4-WP020: ACTIVE / NOT CLOSED
COMPLETED_CORE_V1_WPS: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95%
CORE_V1_RELEASE: NOT DECLARED
CORE_V1_RELEASE_DECLARED: false
```

## Purpose

Synchronize project control documents after the successful Owner-approved merge of probe tooling PR #96 (`P4-WP020-LIVE-R5-VIDU2-PREP`).

This gate is strictly **DOCS-ONLY**. No runtime, application, test, workflow, or provider behavior changes are included.

## Merged Implementation Gate Truth (`P4-WP020-LIVE-R5-VIDU2-PREP`)

PR #96 merged to canonical `main` at commit `fb72d683c0dd4daa721507b6a0c12dcec17d7366` (reviewed HEAD `8dce19e7dbd0ffba0bf358c6bbc59cbdb87e7076`).

Delivered capabilities:
1. **Dedicated VIDU2 Runner Script (`.github/scripts/wp020_live_r5_vidu2.py`)**:
   - Binds reserved execution identity `LIVE-20260910-VIDU2-R5` (reserved in tooling only; NOT authorized for live execution).
   - Enforces `MAX_GENERATION_POSTS = 1`.
   - Strictly enforces exact lowercase resolution `720p` (never sends `720P` to provider API).
   - Model `viduq2`, mode `text-to-video`, duration `4.0`s, aspect ratio `16:9`.
   - Captures typed integer `provider_http_status` (100–599) and typed enum `failure_classification` (`HTTP_CLIENT_ERROR`, `HTTP_RATE_LIMITED`, `HTTP_SERVER_ERROR`).
   - Strict evidence sanitization strips secrets, authorization tokens, raw response bodies, and response headers.
   - Non-retryable on POST failure or ambiguous submission transport outcome (`submission_uncertain`).
   - Polling uses GET only after confirmed generation job submission.
   - Zero calls to OpenAI, Gemini, or ElevenLabs.
2. **Dedicated VIDU2 Workflow (`.github/workflows/wp020-live-r5-vidu2.yml`)**:
   - Dedicated concurrency group `wp020-live-r5-vidu2-probe`, `cancel-in-progress: false`.
   - Triggers strictly via manual `workflow_dispatch` on canonical `main` with ancestry check against base SHA `cdfe3ce44ba9a9d6219909d12c0536c1cd716cec`.
   - Issue comment pagination check using `gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments"`.
   - Requires exact Owner authorization marker `FRESH_OWNER_AUTHORIZED_VIDU2: LIVE-20260910-VIDU2-R5 @ <GITHUB_SHA>`.
   - Fail-closed validation of `VIDU_API_KEY` presence strictly BEFORE consuming execution fence `EXECUTION_STARTED: LIVE-20260910-VIDU2-R5` and strictly BEFORE exporting live execution permit.
   - Checks terminal markers `VIDU2_PROBE_PASS` and `VIDU2_PROBE_STOPPED`.
3. **Contract Test Suite (`backend/tests/test_wp020_live_r5_vidu2_contract.py`)**:
   - Automated tests covering contract requirements A through V using mock HTTP transport only (zero live provider/network calls).
4. **Tooling Isolation**:
   - Historical VIDU1 files (`.github/scripts/wp020_live_r5_vidu1.py`, `.github/workflows/wp020-live-r5-vidu1.yml`, `backend/tests/test_wp020_live_r5_vidu1_contract.py`) remained unmodified.

## VIDU2 Tooling Safety State

```text
RESERVED_TOOLING_IDENTITY: LIVE-20260910-VIDU2-R5 (TOOLING ONLY / NOT AUTHORIZED FOR LIVE EXECUTION)
VIDU2_PAID_IDENTITY: NONE / NOT AUTHORIZED
VIDU2_PAID_EXECUTION: NOT AUTHORIZED
```

There is NO:
- `FRESH_OWNER_AUTHORIZED_VIDU2: LIVE-20260910-VIDU2-R5` marker written or authorized
- `EXECUTION_STARTED: LIVE-20260910-VIDU2-R5` fence comment written or consumed
- `VIDU2_PROBE_PASS: LIVE-20260910-VIDU2-R5`
- `VIDU2_PROBE_STOPPED: LIVE-20260910-VIDU2-R5`

THIS GATE DOES NOT AUTHORIZE VIDU2 LIVE EXECUTION.

## Immutable Consumed Live History (Run 34423580310)

```text
Execution ID: LIVE-20260909-VIDU1-R5
Run: 34423580310
Execution Canonical Main: 5a818b9dbf642b1e456dba51c9a80745d966919e
Fence Comment: 5611052822
Terminal STOP Comment: 5611054713
Status: STOPPED / CONSUMED / NEVER RERUN
Generation POSTs: 1
Provider Error Code: HTTP_ERROR
Provider Job ID: null
Poll Attempts: 0
OpenAI Calls: 0
Gemini Calls: 0
ElevenLabs Calls: 0
Historical HTTP Status: UNKNOWN (not preserved in sanitized evidence of run 34423580310)
Historical Vidu Credits Consumed: UNKNOWN / NOT CONFIRMED
```

- Historical run `34423580310` / execution identity `LIVE-20260909-VIDU1-R5` is permanently consumed and **MUST NEVER BE RERUN**.
- Historical HTTP status code remains `UNKNOWN`.
- Historical Vidu credits consumed remain `UNKNOWN / NOT CONFIRMED` (zero credits are NOT claimed).

## Safety Invariants Confirmation

```text
CLOSURE provider_generation_calls = 0
CLOSURE paid_provider_calls = 0
CLOSURE vidu_generation_posts = 0
CLOSURE vidu_credits_consumed = 0 by PREP-CLOSE itself
CLOSURE paid_fence_written = false
CLOSURE paid_live_dispatch = false
```
