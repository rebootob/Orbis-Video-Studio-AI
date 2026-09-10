# P4-WP020-LIVE-R5-VIDU1-C1 — NO-PAID HTTP Failure Evidence & Request Contract Diagnostic Corrective

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU1-C1
TYPE: NO-PAID / HTTP Failure Evidence & Request Contract Diagnostic Corrective
OWNER_AUTHORIZED: YES (Issue #63 comment 5611111664)
CANONICAL_BASE_MAIN: 5a818b9dbf642b1e456dba51c9a80745d966919e
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu1-c1
CONSUMED_RUN: 34423580310 (Execution ID: LIVE-20260909-VIDU1-R5)
CONSUMED_FENCE_COMMENT: 5611052822
CONSUMED_TERMINAL_STOP_COMMENT: 5611054713
C1_PROVIDER_GENERATION_CALLS: 0
C1_PAID_PROVIDER_CALLS: 0
C1_VIDU_GENERATION_POSTS: 0
C1_VIDU_CREDITS_CONSUMED: 0 (by C1 itself)
C1_PAID_FENCE_WRITTEN: false
C1_PAID_LIVE_DISPATCH: false
CORE_V1_RELEASE: NOT DECLARED
STATUS: PASS / MERGED / COMPLETE (PR #94)
MERGE_COMMIT: b8d935b2d9e63668663dda0b9d92b5e3c20f1546
REVIEWED_HEAD: a1c2b50eaa25e7f993fd555a39f37be8db76fa6c
ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: WAITING_FOR_EXPLICIT_OWNER_NEXT_GATE
NEXT_GATE: OWNER DECISION REQUIRED
LAST_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1
```

## Immutable Historical Truth (Run 34423580310)

The live probe run `34423580310` executed on canonical `main` (`5a818b9dbf642b1e456dba51c9a80745d966919e`) was consumed:

```text
Execution ID: LIVE-20260909-VIDU1-R5
Status: STOPPED / CONSUMED / NEVER RERUN
Generation POSTs: 1
Provider Error Code: HTTP_ERROR
Provider Job ID: null
Poll Attempts: 0
OpenAI Calls: 0
Gemini Calls: 0
ElevenLabs Calls: 0
Historical HTTP Status: UNKNOWN (not preserved in sanitized evidence of run 34423580310)
Vidu Credits Consumed: UNKNOWN / NOT CONFIRMED
```

The run made exactly one Vidu generation POST. It failed with `HTTP_ERROR` before receiving a job ID or beginning polling. The historical HTTP status code was not preserved in the runner's sanitized evidence and remains `UNKNOWN`. Vidu credits consumed for run `34423580310` remain `UNKNOWN / NOT CONFIRMED` (zero credits are NOT claimed).

`LIVE-20260909-VIDU1-R5` is consumed and MUST NEVER BE RERUN.

## Purpose of C1 Corrective

Diagnose the consumed VIDU1 HTTP failure safely WITHOUT another provider call:
1. Preserve safe HTTP status metadata and failure classification in future probe evidence.
2. Verify the outbound Vidu request contract (endpoint, headers, payload structure) using mocks only.
3. Synchronize control and delivery truth while strictly maintaining NO-PAID boundaries.

## Delivered Corrective Changes

1. **Safe HTTP Status Evidence (`.github/scripts/wp020_live_r5_vidu1.py`)**:
   - Added `provider_http_status` (typed integer within 100–599) and `failure_classification` (`HTTP_CLIENT_ERROR`, `HTTP_RATE_LIMITED`, `HTTP_SERVER_ERROR`) to runner state and sanitized evidence.
   - Added `classify_http_status` helper.
   - Propagated HTTP status code from `submission_result.status_code` into evidence on failure or submission uncertainty.
   - Preserved fail-closed evidence sanitization: raw response bodies, response headers, Authorization tokens, API keys, and unsafe provider messages remain strictly excluded.
   - Updated workflow canonical base SHA to `5a818b9dbf642b1e456dba51c9a80745d966919e`.

2. **Outbound Vidu Request Contract Verification (`backend/tests/test_wp020_live_r5_vidu1_contract.py`)**:
   - Verified outbound request contract using mock HTTP transport:
     - Target endpoint: `POST https://api.vidu.com/ent/v2/text2video`
     - Headers: `Authorization: Token <API_KEY>`, `Content-Type: application/json`
     - Payload: `model=viduq2`, `duration=4`, `aspect_ratio=16:9`, `resolution=720p` (with adapter-level normalization from `720P`), non-empty prompt.
   - Added mock behavioral tests for HTTP 400, 401, 403, 429, and 500 responses verifying status preservation and fail-closed behavior.
   - Verified `MAX_GENERATION_POSTS = 1` and zero calls to OpenAI, Gemini, or ElevenLabs.

## Safety Invariants Confirmation

```text
C1 provider_generation_calls = 0
C1 paid_provider_calls = 0
C1 vidu_generation_posts = 0
C1 vidu_credits_consumed = 0 (by C1 itself)
C1 paid_fence_written = false
C1 paid_live_dispatch = false
```
