# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R2-C1
TITLE = Gemini HTTP Evidence + Control-Truth Corrective
STATUS = OWNER AUTHORIZED / NO-PAID CORRECTIVE IN PROGRESS
BASE_MAIN = 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
WORKING_BRANCH = ai/p4-wp020-live-r2-c1-gemini-evidence
PROVIDER_CALLS_ALLOWED = 0
PAID_SPEND_ALLOWED = USD 0.00
```

P4-WP020 itself remains **ACTIVE / NOT CLOSED**. Core V1 release is not declared.

---

## Why C1 Exists

The consumed R2 live run reached real providers in this order:

1. OpenAI STORY succeeded.
2. Gemini IMAGE returned a non-success HTTP response.
3. Orbis surfaced only `HTTP_ERROR` in durable execution evidence.
4. The transient provider result contained an HTTP status, but `GenerationJob.result` persisted only `raw_response`, which was empty for the Gemini non-2xx path.
5. The live contract stopped execution before Vidu, ElevenLabs, and all downstream live proof.

R2 is consumed and must not be rerun.

---

## Accepted R2 Evidence

```text
Execution ID: LIVE-20260909-BB75-R2
Run ID: 34287696335
Main SHA: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
Execution fence: CONSUMED
OpenAI STORY: SUCCESS
OpenAI usage: 544 prompt / 585 completion tokens
Last known confirmed/committed UAT cost at STOP: USD 0.0072
Gemini IMAGE: HTTP_ERROR
Chargeable calls conservatively consumed: 2/6
Vidu: NOT EXECUTED
ElevenLabs: NOT EXECUTED
Downstream live proof: NOT EXECUTED
```

No paid retry is authorized by C1.

---

## Authorized C1 Scope

Implementation may only:

1. make Gemini non-2xx failure evidence durable using the existing `GenerationJob.result` JSON field;
2. persist only sanitized metadata:
   - provider;
   - model;
   - HTTP status;
   - error code;
   - retryable flag;
   - submission-uncertain flag;
3. keep provider response body, headers, API keys, credentials and reference bytes out of durable failure evidence;
4. add tests for HTTP 400 / 401 / 403 / 429 / 503;
5. verify deterministic failure vs `RECONCILIATION_REQUIRED` semantics;
6. synchronize control docs to current WP020/R2/C1 truth.

No schema migration is required or authorized.

---

## Explicitly Forbidden in C1

- no real OpenAI call;
- no real Gemini call;
- no Vidu call;
- no ElevenLabs call;
- no paid/live workflow dispatch;
- no R1 or R2 rerun;
- no R3 live execution identity;
- no automatic paid retry;
- no Gemini model or endpoint change;
- no pricing-policy change;
- no retry-policy change;
- no release tag;
- no production deployment;
- no post-Core-V1 scope expansion.

---

## Verification Required Before Merge Proposal

```text
TARGETED_GEMINI_TESTS = PASS required
FULL_BACKEND_CI = PASS required
FRESH_POSTGRES_MIGRATIONS = PASS required
FRONTEND_CI = PASS if repository policy triggers it
SECRET_LEAK_CHECK = PASS required
PAID_WORKFLOW_DISPATCH_COUNT_DURING_C1 = 0 required
EXACT_DIFF_SCOPE = C1 only
```

After independent exact-head review, STOP for Owner merge decision.

---

## Roles

```text
Owner = final human authority / authorization / merge / paid-live gates
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane only when explicitly authorized
Codex = STOP
Claude Code = STOP
```

Detailed C1 contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R2_C1.md`.
