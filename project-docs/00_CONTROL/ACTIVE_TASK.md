# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R3-C1
LAST_CLOSED_TITLE = Gemini 429 Quota/Rate-Limit Evidence Corrective
LAST_CLOSED_STATUS = PASS / MERGED / CLOSED
CLOSURE_SYNC = P4-WP020-LIVE-R3-C1-CLOSE
CLOSURE_TYPE = CONTROL-DOC ONLY
CLOSURE_PR = #79
CANONICAL_MAIN = 1c63045497eb7ee708cd81876f6bf7a011907f77
MERGED_PR = #78
MERGED_C1_HEAD = b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
PAID_LIVE_EXECUTION = STOP / NOT AUTHORIZED
R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4 = NOT AUTHORIZED
NEXT_CANDIDATE_GATE = P4-WP020-LIVE-R4-PRE1 / NO-PAID / REQUIRES SEPARATE OWNER AUTHORIZATION
```

---

## Closed C1 Evidence

`P4-WP020-LIVE-R3-C1 — Gemini 429 Quota/Rate-Limit Evidence Corrective`

Closure truth:
- Owner-authorized NO-PAID corrective;
- PR #78 merged exact reviewed HEAD `b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6`;
- merge commit / canonical main `1c63045497eb7ee708cd81876f6bf7a011907f77`;
- backend CI run `34298997460` = SUCCESS;
- backend tests = 511 passed / 2 skipped / 3 warnings;
- PostgreSQL migration paths `fresh-head` and `from-revision-010` = PASS;
- frontend CI run `34298997360` = SUCCESS;
- independent review = PASS / READY FOR OWNER MERGE DECISION before merge;
- C1 provider calls = 0;
- C1 spend = USD 0.00;
- no model/endpoint/pricing/retry-policy change;
- no paid workflow dispatch;
- no release/tag/deploy.

C1 added strict sanitized Gemini HTTP 429 evidence classification and nested STOP-artifact allowlisting without retaining raw provider body, message, headers, credentials, prompt, arbitrary project dimensions, or debug/help payloads.

---

## External Account-Side Corrective Evidence

Owner supplied current Google AI Studio evidence after C1 merge:

```text
Project: Orbis-Video-Production
Billing: Tier 1 / Prepay
Observed credit: USD 5.00
Nano Banana 2 (Gemini 3.1 Flash Image):
  RPM 100
  TPM 200K
  RPD 1K
Prior Free-tier image quota: 0 / 0 / 0
```

Owner also reported updating GitHub Actions `GEMINI_API_KEY` to the new Orbis project key. The secret value is not readable or recorded.

Interpretation: the R3 HTTP 429 is consistent with the prior Free-tier image quota-zero condition. Runtime adoption of the replacement secret is still unproven and must be validated only through a separately authorized NO-PAID preflight.

This does not authorize a provider generation request or R4 paid execution.

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
- conservative calls 2/6;
- last known committed UAT cost USD 0.0072.

### R3
```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Execution main: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence: CONSUMED
Status: STOPPED
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

USD 0.0065 is Orbis known committed/actual evidence only. It does not prove whether the failed Gemini request incurred an external provider charge.

---

## Stop Rule After C1 Closure

No new implementation or paid/live execution is active.

Do not auto-start R4. The next candidate gate is `P4-WP020-LIVE-R4-PRE1`, a NO-PAID runtime readiness check requiring separate Owner authorization. It may validate credential/config presence and runtime adoption only; it must not generate an image or consume a paid execution fence.

Any future R4 paid attempt requires a new immutable execution identity, fresh exact-main authorization, fresh no-paid preflight, a new one-shot execution fence, and separate Owner run authorization.

Contract retained for history:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R3_C1.md`
