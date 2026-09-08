# P4-WP020-LIVE-R2-C1 — Gemini HTTP Evidence + Control-Truth Corrective

**Status:** PASS / MERGED / CLOSED  
**Base canonical main:** `570acda49245ecae7ae48e1e66ed8839e4bfc2e2`  
**Working branch:** `ai/p4-wp020-live-r2-c1-gemini-evidence`  
**Reviewed implementation HEAD:** `6c66650312ebbd2433e5b00c7864c086ea37e28e`  
**PR:** `#74`  
**Merge commit:** `d706acacd1f51224c955fb9c8d0d9eab3deda186`  
**Paid/live provider execution during C1:** NONE  
**Provider calls during C1:** `0`  
**Paid spend during C1:** `USD 0.00`

## Purpose

C1 closed the evidence gap exposed by the consumed R2 live run without issuing another provider request.

R2 stopped at Gemini Image after the service surfaced only `HTTP_ERROR`. The adapter already retained the HTTP status in the transient `ImageJobResult`, but the durable `GenerationJob.result` evidence path persisted only `raw_response`, which was empty for non-2xx Gemini responses.

C1 preserved provider behavior and added sanitized durable error metadata, tests, and control-document synchronization.

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
- Exact historical Gemini HTTP status was not retained in durable evidence.
- Vidu: NOT EXECUTED.
- ElevenLabs: NOT EXECUTED.
- Assembly / subtitle / QC / approval / render / multi-output / archive live downstream proof: NOT EXECUTED.

## Delivered C1 scope

1. Gemini non-2xx HTTP failure evidence now uses the existing `GenerationJob.result` JSON boundary.
2. Durable metadata is limited to:
   - `provider`
   - `model`
   - `http_status`
   - `error_code`
   - `retryable`
   - `submission_uncertain`
3. Provider response body, response headers, credentials, API keys, prompt payload secrets and reference bytes remain excluded.
4. Tests cover HTTP 400 / 401 / 403 / 429 / 503 classification.
5. Deterministic failures remain deterministic and uncertain 5xx outcomes remain `RECONCILIATION_REQUIRED` at the service boundary.
6. Sanitized metadata is durably persisted to `GenerationJob.result`.
7. Control documents were synchronized to the consumed R2 truth.

## Verified evidence before merge

```text
Backend: 470 passed / 2 skipped
Fresh PostgreSQL migrations: PASS
Frontend: 52/52 PASS
Frontend build/typecheck: PASS
Frontend lint: 0 errors / warnings only
Paid provider calls during C1: 0
Paid spend during C1: USD 0.00
```

Independent exact-head review returned PASS before Owner-approved merge of PR #74.

## Historical non-scope remains locked

C1 did not authorize or perform:

- real OpenAI, Gemini, Vidu, or ElevenLabs request;
- paid/live workflow dispatch;
- reuse of R1 or R2 execution IDs;
- R3 paid execution;
- model/endpoint/pricing/retry-policy change;
- database migration/schema change;
- release tag or Core V1 release declaration;
- post-Core-V1 scope expansion.

## Post-C1 truth

After merge, repository review established that R2's PostgreSQL and MinIO state was ephemeral. Its artifact preserves accepted historical evidence but not reusable canonical Story/project state. Therefore a future coherent end-to-end R3 LIVE PASS cannot truthfully resume the exact R2 Story record.

The next authorized gate is `P4-WP020-LIVE-R3-PRE1`, a NO-PAID Gemini metadata-access / contract-preparation gate. The proposed R3 paid contract is a fresh full-chain six-call UAT and remains NOT AUTHORIZED until later explicit Owner gates.

See:
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`
