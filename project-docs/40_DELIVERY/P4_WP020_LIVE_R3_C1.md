# P4-WP020-LIVE-R3-C1 — Gemini 429 Quota/Rate-Limit Evidence Corrective

## Status

```text
OWNER_AUTHORIZED = YES
TYPE = NO-PAID / CODE + TEST + CONTROL-DOC
BASE_MAIN = 82ce42116e3f866227dd598814cf79c0b9c640c4
BRANCH = ai/p4-wp020-live-r3-c1-gemini-429-evidence
PR = #78
EXACT_REVIEWED_HEAD = b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6
MERGE_COMMIT = 1c63045497eb7ee708cd81876f6bf7a011907f77
STATUS = PASS / MERGED / CLOSED
PROVIDER_CALLS = 0
SPEND = USD 0.00
R3_RERUN = FORBIDDEN
R4 = NOT AUTHORIZED
```

## Triggering Evidence

R3 paid run:
- execution ID `LIVE-20260909-363F-R3`;
- workflow run `34297314995`;
- exact execution main `82ce42116e3f866227dd598814cf79c0b9c640c4`;
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

## Implemented Corrective

For HTTP 429 only, the Gemini adapter parses response JSON in memory and retains only a strict allowlist:

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

`quota_class` is derived conservatively from the allowlisted structured fields:
- `QUOTA_ZERO`;
- `DAILY_QUOTA`;
- `RATE_LIMIT`;
- `QUOTA_EXHAUSTED`;
- `RESOURCE_EXHAUSTED`.

Unknown or malformed structures fall back to the pre-existing base HTTP evidence.

A second nested allowlist in the R3 STOP-artifact sanitizer preserves only the same safe structured quota evidence. This prevents the durable artifact from copying arbitrary `GenerationJob.result` fields.

## Explicitly Excluded Evidence

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

## Test / Review Evidence

Simulated zero-network coverage includes:
1. quota value zero;
2. daily quota identifier;
3. per-minute rate identifier;
4. safe RetryInfo delay;
5. unknown detail types excluded;
6. malformed/non-dict body falls back safely;
7. `GenerationJob.result` persists the same sanitized allowlist;
8. STOP-artifact sanitizer keeps only nested safe quota fields;
9. secrets/provider human messages are absent.

Exact-head evidence before merge:
- backend CI run `34298997460` = SUCCESS;
- backend tests = 511 passed / 2 skipped / 3 warnings;
- PostgreSQL migrations `fresh-head` = PASS;
- PostgreSQL migrations `from-revision-010` = PASS;
- frontend CI run `34298997360` = SUCCESS;
- independent review = PASS / READY FOR OWNER MERGE DECISION;
- provider calls = 0;
- spend = USD 0.00.

## Closure

Owner approved merge of PR #78 at exact reviewed HEAD `b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6`.

PR #78 merged to canonical `main` as `1c63045497eb7ee708cd81876f6bf7a011907f77`.

C1 is therefore **PASS / MERGED / CLOSED**.

## Post-C1 Account-Side Evidence

After C1 merge, Owner supplied Google AI Studio evidence identifying and correcting the account-side condition that caused the R3 image request to stop:

```text
Prior image-model tier: Free tier
Prior Nano Banana 2 (Gemini 3.1 Flash Image) quota: 0 / 0 / 0
Replacement project: Orbis-Video-Production
Current billing tier: Tier 1 / Prepay
Observed credit balance: USD 5.00
Current Nano Banana 2 quota:
  RPM: 100
  TPM: 200K
  RPD: 1K
```

This evidence supports the R3 HTTP 429 as the prior Free-tier image quota-zero condition rather than a proven Orbis code defect.

Owner also reported updating the GitHub Actions `GEMINI_API_KEY` secret to the new Orbis project key. The secret value is intentionally not available in repository evidence. Runtime adoption of that replacement secret remains unproven until a separately authorized NO-PAID runtime preflight is executed.

This account-side remediation does not modify C1 code and does not authorize R4.

Merge/closure does not authorize:
- R4;
- any provider call;
- any paid/live execution;
- a new execution fence;
- model/endpoint/pricing/retry-policy changes;
- release/tag/deploy.

No gate auto-authorizes the next one.
