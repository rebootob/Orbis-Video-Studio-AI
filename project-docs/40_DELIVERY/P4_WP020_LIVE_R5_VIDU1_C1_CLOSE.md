# P4-WP020-LIVE-R5-VIDU1-C1-CLOSE — DOCS-ONLY Post-Merge Control Closure Sync

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU1-C1-CLOSE
TYPE: DOCS-ONLY Post-Merge Control Closure Sync
OWNER_AUTHORIZED: YES (Issue #63 comment 5611514449)
CANONICAL_MAIN_SHA: b8d935b2d9e63668663dda0b9d92b5e3c20f1546
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu1-c1-close
MERGED_IMPLEMENTATION_GATE: P4-WP020-LIVE-R5-VIDU1-C1
C1_MERGED_PR: #94
C1_REVIEWED_HEAD: a1c2b50eaa25e7f993fd555a39f37be8db76fa6c
C1_MERGE_COMMIT: b8d935b2d9e63668663dda0b9d92b5e3c20f1546
CLOSURE_PR: #95 (POST-MERGE TARGET: PASS / MERGED / COMPLETE; IN-FLIGHT: OPEN / IN REVIEW / NOT MERGED)

ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: WAITING_FOR_EXPLICIT_OWNER_NEXT_GATE
NEXT_GATE: OWNER DECISION REQUIRED

LAST_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1-CLOSE
LAST_COMPLETED_STATUS: PASS / MERGED / COMPLETE (PR #95)
PREV_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1
PREV_COMPLETED_STATUS: PASS / MERGED / COMPLETE
PREV2_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-COR1
PREV2_COMPLETED_STATUS: PASS / MERGED / COMPLETE

P4-WP020: ACTIVE / NOT CLOSED
COMPLETED_CORE_V1_WPS: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95%
CORE_V1_RELEASE: NOT DECLARED
CORE_V1_RELEASE_DECLARED: false
```

## Purpose

Synchronize project control documents after the successful Owner-approved merge of implementation PR #94 (`P4-WP020-LIVE-R5-VIDU1-C1`).

This gate is strictly **DOCS-ONLY**. No runtime, application, or provider behavior changes are included.

## Merged Implementation Gate Truth (`P4-WP020-LIVE-R5-VIDU1-C1`)

PR #94 merged to canonical `main` at commit `b8d935b2d9e63668663dda0b9d92b5e3c20f1546` (reviewed HEAD `a1c2b50eaa25e7f993fd555a39f37be8db76fa6c`).

Delivered capabilities:
1. **Safe HTTP Status Diagnostics**: Preserves typed `provider_http_status` (100–599) and typed `failure_classification` (`HTTP_CLIENT_ERROR`, `HTTP_RATE_LIMITED`, `HTTP_SERVER_ERROR`) in sanitized evidence without leaking raw bodies, headers, or secrets.
2. **Vidu Outbound Request Contract**: Explicitly targets `POST /text2video` with headers `Authorization: Token <API_KEY>`, `Content-Type: application/json`, and payload `model=viduq2`, `duration=4`, `aspect_ratio=16:9`, `resolution=720p`. Added adapter-level casing normalization from legacy/internal `"720P"` to provider-accepted `"720p"`.
3. **Mock Contract Coverage**: Added automated mock tests covering HTTP 400, 401, 403, 429, and 500 error responses to verify status preservation and fail-closed behavior without live provider calls.

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
- The historical `HTTP_ERROR` is not reinterpreted.

## Future Paid Status

```text
VIDU1_PAID_IDENTITY = NONE / NOT AUTHORIZED
VIDU1_PAID_EXECUTION = NOT AUTHORIZED
R5_PAID_IDENTITY = NONE / NOT AUTHORIZED
R5_PAID_EXECUTION = NOT AUTHORIZED
```

Any future Vidu probe strictly requires:
- a new dedicated execution identity
- fresh explicit Owner authorization
- fresh exact authorization marker bound to the then-current canonical main SHA
- a new unconsumed fence

## Safety Invariants Confirmation

```text
CLOSURE provider_generation_calls = 0
CLOSURE paid_provider_calls = 0
CLOSURE vidu_generation_posts = 0
CLOSURE vidu_credits_consumed = 0
CLOSURE paid_fence_written = false
CLOSURE paid_live_dispatch = false
```
