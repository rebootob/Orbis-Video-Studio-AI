# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R3-C1
TITLE = Gemini 429 Quota/Rate-Limit Evidence Corrective
TYPE = NO-PAID / CODE + TEST + CONTROL-DOC
STATUS = OWNER AUTHORIZED / IMPLEMENTATION + CI REVIEW
BRANCH = ai/p4-wp020-live-r3-c1-gemini-429-evidence
BASE_MAIN = 82ce42116e3f866227dd598814cf79c0b9c640c4
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
PAID_LIVE_EXECUTION = STOP / NOT AUTHORIZED
C1_PROVIDER_CALLS = 0
C1_SPEND_AUTHORIZATION = USD 0.00
R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4 = NOT AUTHORIZED
```

---

## Owner-Authorized C1 Scope

1. Parse only structured Gemini HTTP 429 error metadata already returned by a failed request.
2. Persist only an allowlisted sanitized subset:
   - provider/model/http status/error code/retryable/submission uncertainty;
   - provider status;
   - quota metric / quota id / quota value;
   - quota dimensions limited to model/location;
   - retry delay when structurally safe;
   - conservative quota class.
3. Add simulated zero-network tests for quota-zero, daily-quota, minute-rate, retry-delay, malformed/unknown detail, and durable `GenerationJob.result` persistence.
4. Synchronize control documents to immutable R3 STOP truth.

Forbidden:
- no OpenAI/Gemini/Vidu/ElevenLabs generation request;
- no metadata probe required by this corrective;
- no R3 rerun;
- no R4 tooling or paid authorization;
- no model/endpoint/pricing/retry-policy change;
- no release/tag/deployment.

---

## Immutable LIVE Truth

### R1
- consumed / immutable / never rerun;
- OpenAI HTTP 429 STOP.

### R2
- execution `LIVE-20260909-BB75-R2`;
- consumed / never rerun;
- OpenAI STORY PASS;
- Gemini non-success `HTTP_ERROR`;
- 2/6 conservative calls;
- last known committed UAT cost USD 0.0072.

### R3
```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Preflight immediately before fence: PASS
Execution fence: CONSUMED
STOP phase: LIVE-02-GEMINI-IMAGE
```

Observed sequence:
1. OpenAI STORY = SUCCESS.
2. OpenAI usage = 546 prompt / 513 completion tokens.
3. Last known committed/actual Orbis UAT cost at STOP = USD 0.0065.
4. Gemini IMAGE = HTTP 429 / retryable true / submission_uncertain false.
5. Conservative chargeable requests consumed = 2/6.
6. Vidu / ElevenLabs / downstream = NOT EXECUTED.
7. STOP marker exists; R3 identity must never be rerun.

The USD 0.0065 value is Orbis known committed/actual evidence. It is not proof that the failed Gemini request incurred no external provider charge.

---

## C1 Stop / Review Rule

C1 stops after implementation + exact-head CI + independent review and waits for Owner merge decision.

C1 merge does not authorize:
- R4;
- any provider call;
- any paid/live execution;
- a new execution fence;
- Core V1 release.

Contract:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R3_C1.md`
