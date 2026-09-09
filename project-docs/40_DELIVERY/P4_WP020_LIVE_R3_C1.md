# P4-WP020-LIVE-R3-C1 — Gemini 429 Quota/Rate-Limit Evidence Corrective

## Status

```text
OWNER_AUTHORIZED = YES
TYPE = NO-PAID / CODE + TEST + CONTROL-DOC
BASE_MAIN = 82ce42116e3f866227dd598814cf79c0b9c640c4
BRANCH = ai/p4-wp020-live-r3-c1-gemini-429-evidence
PROVIDER_CALLS_AUTHORIZED = 0
SPEND_AUTHORIZATION = USD 0.00
R3_RERUN = FORBIDDEN
R4 = NOT AUTHORIZED
```

## Triggering Evidence

R3 paid run:
- execution ID `LIVE-20260909-363F-R3`;
- workflow run `34297314995`;
- exact main `82ce42116e3f866227dd598814cf79c0b9c640c4`;
- immediate pre-fence preflight PASS;
- execution fence consumed;
- OpenAI STORY succeeded;
- Gemini IMAGE failed HTTP 429;
- `retryable=true`;
- `submission_uncertain=false`;
- STOP at `LIVE-02-GEMINI-IMAGE`;
- conservative calls 2/6;
- last known committed/actual Orbis UAT cost USD 0.0065;
- Vidu / ElevenLabs / downstream not executed.

R3 is immutable and must never be rerun.

## Problem

R2-C1 made the exact HTTP status durable. R3 therefore proved Gemini returned HTTP 429, but the existing adapter intentionally discarded all provider-body details. That is safe but insufficient to distinguish observable quota/rate categories.

C1 must improve diagnosis without retaining unrestricted provider text.

## Authorized Implementation

For HTTP 429 only, the Gemini adapter may parse the response JSON in memory and retain only a strict allowlist:

```text
provider
model
http_status
error_code
retryable
submission_uncertain
provider_status
quota_failures[].quota_metric
quota_failures[].quota_id
quota_failures[].quota_value
quota_failures[].quota_dimensions.model
quota_failures[].quota_dimensions.location
retry_delay
quota_class
```

`quota_class` may only be derived conservatively from the allowlisted structured fields:
- `QUOTA_ZERO`;
- `DAILY_QUOTA`;
- `RATE_LIMIT`;
- `QUOTA_EXHAUSTED`;
- `RESOURCE_EXHAUSTED`.

Unknown or malformed structures fall back to the pre-existing base HTTP evidence.

## Explicitly Forbidden Evidence

Never persist:
- provider `message`;
- complete/raw response body;
- HTTP headers;
- API keys or credentials;
- prompt or negative prompt;
- reference image bytes/URLs;
- arbitrary quota dimensions such as project identifiers;
- Help/debug links or descriptions;
- unknown structured detail objects.

## Tests

Simulated local tests only:
1. quota value zero;
2. daily quota identifier;
3. per-minute rate identifier;
4. safe RetryInfo delay;
5. unknown detail types excluded;
6. malformed/non-dict body falls back safely;
7. `GenerationJob.result` persists the same sanitized allowlist;
8. secrets/provider human messages are absent.

No real provider request is permitted during C1.

## Non-Goals

- do not change Gemini model;
- do not change endpoint;
- do not change pricing;
- do not change retry behavior;
- do not add automatic retry;
- do not change R3/R4 execution workflow;
- do not fix Google account quota/billing settings from code;
- do not authorize R4;
- do not release/tag/deploy.

## Acceptance

C1 can be considered PASS only when:
- exact-head backend CI passes;
- migration checks pass;
- frontend CI remains green;
- diff remains within C1 scope;
- independent review verifies no provider dispatch and no secret/body leakage;
- control docs record R3 as STOPPED / CONSUMED and R4 as NOT AUTHORIZED.

Then STOP for Owner merge decision. Merge does not authorize a future paid attempt.
