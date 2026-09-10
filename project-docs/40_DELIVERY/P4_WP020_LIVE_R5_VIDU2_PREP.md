# P4-WP020-LIVE-R5-VIDU2-PREP — NO-PAID Fresh Dedicated Vidu 1-Call Probe Tooling

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU2-PREP
TYPE: NO-PAID / Fresh Dedicated Vidu 1-Call Probe Tooling
OWNER_AUTHORIZED: YES (Issue #63 comment 5615321579)
CANONICAL_BASE_MAIN: cdfe3ce44ba9a9d6219909d12c0536c1cd716cec
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-prep
RESERVED_EXECUTION_IDENTITY: LIVE-20260910-VIDU2-R5 (TOOLING ONLY / NOT AUTHORIZED FOR LIVE EXECUTION)
HISTORICAL_RUN_34423580310: CONSUMED / NEVER RERUN
HISTORICAL_VIDU1_IDENTITY: LIVE-20260909-VIDU1-R5 (STOPPED / CONSUMED)
PREP_PROVIDER_GENERATION_CALLS: 0
PREP_PAID_PROVIDER_CALLS: 0
PREP_VIDU_GENERATION_POSTS: 0
PREP_VIDU_CREDITS_CONSUMED: 0
PREP_PAID_FENCE_WRITTEN: false
PREP_PAID_LIVE_DISPATCH: false
CORE_V1_RELEASE: NOT DECLARED
STATUS: PASS / MERGED / COMPLETE (PR #96)
MERGE_COMMIT: fb72d683c0dd4daa721507b6a0c12dcec17d7366
REVIEWED_HEAD: 8dce19e7dbd0ffba0bf358c6bbc59cbdb87e7076
ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: WAITING_FOR_EXPLICIT_OWNER_NEXT_GATE
NEXT_GATE: OWNER DECISION REQUIRED
LAST_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU2-PREP
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

## Purpose of VIDU2-PREP Gate

Prepare fresh, dedicated, independent probe tooling for a potential future Vidu single-generation probe WITHOUT consuming live credits or performing live calls:
1. Dedicated runner script `.github/scripts/wp020_live_r5_vidu2.py` binding reserved identity `LIVE-20260910-VIDU2-R5`.
2. Dedicated workflow `.github/workflows/wp020-live-r5-vidu2.yml` with concurrency group `wp020-live-r5-vidu2-probe`, manual `workflow_dispatch` only, canonical `main` guard, issue comment pagination, and fail-closed safety fences.
3. Dedicated contract test suite `backend/tests/test_wp020_live_r5_vidu2_contract.py` covering requirements A through U using mock HTTP transport only.
4. Tooling isolation: historical VIDU1 files (`.github/scripts/wp020_live_r5_vidu1.py`, `.github/workflows/wp020-live-r5-vidu1.yml`, `backend/tests/test_wp020_live_r5_vidu1_contract.py`) are unmodified.

## Tooling Invariants & Request Contract

- **Target Model**: `viduq2`
- **Target Mode**: `text-to-video`
- **Target Duration**: `4.0` seconds
- **Target Resolution**: exact lowercase `720p` (never send `720P` to provider API)
- **Target Aspect Ratio**: `16:9`
- **Target Endpoint**: `POST https://api.vidu.com/ent/v2/text2video`
- **Authorization**: `Token <API_KEY>`
- **Generation Post Cap**: `MAX_GENERATION_POSTS = 1`
- **Safe HTTP Diagnostics**: Preserves typed integer `provider_http_status` (100–599) and typed `failure_classification` (`HTTP_CLIENT_ERROR`, `HTTP_RATE_LIMITED`, `HTTP_SERVER_ERROR`). Raw response bodies, headers, and secrets are strictly excluded.
- **Fail-Closed on Transport Ambiguity**: Uncertain submission transport failures immediately halt with `SUBMISSION_UNCERTAIN` and zero retry.
- **Zero Other Provider Calls**: Strictly 0 calls to OpenAI, Gemini, or ElevenLabs.

## Safety Invariants Confirmation

```text
PREP provider_generation_calls = 0
PREP paid_provider_calls = 0
PREP vidu_generation_posts = 0
PREP vidu_credits_consumed = 0
PREP paid_fence_written = false
PREP paid_live_dispatch = false
```
