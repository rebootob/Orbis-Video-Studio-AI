# P4-WP020-LIVE-R2-C1 — Gemini HTTP Evidence + Control-Truth Corrective

**Status:** OWNER AUTHORIZED / NO-PAID CORRECTIVE IN PROGRESS  
**Base canonical main:** `570acda49245ecae7ae48e1e66ed8839e4bfc2e2`  
**Working branch:** `ai/p4-wp020-live-r2-c1-gemini-evidence`  
**Paid/live provider execution:** NOT AUTHORIZED  
**Allowed provider calls in this corrective:** 0

## Purpose

Close the evidence gap exposed by the consumed R2 live run without issuing another provider request.

R2 stopped at Gemini Image after the service surfaced only `HTTP_ERROR`. The adapter already retained the HTTP status in the transient `ImageJobResult`, but the durable `GenerationJob.result` evidence path persisted only `raw_response`, which was `None` for non-2xx Gemini responses.

This corrective preserves provider behavior and only adds sanitized durable error metadata plus tests and control-document synchronization.

## Accepted live truth before C1

### R1

- R1 execution identity is consumed and immutable.
- OpenAI live request returned HTTP 429.
- No automatic paid retry was authorized.

### R2

- Execution ID: `LIVE-20260909-BB75-R2`
- Canonical main used for the run: `570acda49245ecae7ae48e1e66ed8839e4bfc2e2`
- GitHub Actions run: `34287696335`
- No-paid preflight: PASS before execution fence.
- `EXECUTION_STARTED` was written, so R2 is consumed and must never be rerun.
- OpenAI STORY: SUCCESS.
- OpenAI usage evidence: 544 prompt tokens / 585 completion tokens.
- Last known confirmed/committed UAT cost at STOP: USD 0.0072.
- Gemini IMAGE: provider request reached; Orbis received non-success HTTP and surfaced `HTTP_ERROR`.
- Chargeable calls conservatively consumed by R2: 2/6.
- Exact Gemini HTTP status was not retained in durable evidence.
- Vidu: NOT EXECUTED.
- ElevenLabs: NOT EXECUTED.
- Assembly / subtitle / QC / approval / render / multi-output / archive live downstream proof: NOT EXECUTED.
- STOP is mandatory. No paid rerun is authorized by C1.

## Authorized implementation scope

1. Preserve Gemini HTTP failure evidence using the existing `GenerationJob.result` JSON boundary.
2. Persist only sanitized metadata for non-2xx HTTP responses:
   - `provider`
   - `model`
   - `http_status`
   - `error_code`
   - `retryable`
   - `submission_uncertain`
3. Never persist provider response body, response headers, credentials, API keys, prompt payload secrets, or reference bytes as failure evidence.
4. Add deterministic tests for HTTP 400 / 401 / 403 / 429 / 503 classification.
5. Verify deterministic failures remain deterministic and 5xx uncertain outcomes remain `RECONCILIATION_REQUIRED` at the service boundary.
6. Verify sanitized metadata is durably persisted to `GenerationJob.result`.
7. Synchronize control documents to the actual P4-WP020 LIVE state.

## Explicit non-scope

- No real OpenAI, Gemini, Vidu, or ElevenLabs call.
- No GitHub paid/live workflow dispatch.
- No reuse of R1 or R2 execution IDs.
- No new R3 execution ID in this corrective.
- No model change.
- No endpoint change.
- No pricing change.
- No retry-policy change.
- No database migration or schema change.
- No release tag or Core V1 release declaration.
- No post-Core-V1 provider or product expansion.

## Required verification

C1 can be proposed for merge only when:

1. backend targeted Gemini tests PASS;
2. full backend CI PASS;
3. fresh PostgreSQL migration CI PASS;
4. frontend CI remains PASS if triggered by repository policy;
5. no secret/provider response body is present in durable failure evidence;
6. no paid workflow was dispatched by this corrective;
7. exact branch diff remains inside the authorized C1 scope.

## Post-C1 gate

After C1 is merged and independently reviewed, STOP.

A later R3 live attempt requires all of the following:

1. a fresh execution identity;
2. a bounded resume contract that does not unnecessarily repeat already-proven OpenAI work;
3. a no-paid preflight on then-current canonical main;
4. fresh Owner paid/live authorization tied to exact main;
5. a new one-shot execution fence before any chargeable provider request.

C1 by itself authorizes none of those paid/live actions.
