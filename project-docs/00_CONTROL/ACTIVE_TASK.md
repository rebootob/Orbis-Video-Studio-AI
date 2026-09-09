# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R4-PRE1
LAST_CLOSED_TITLE = NO-PAID Runtime Readiness Verification
LAST_CLOSED_STATUS = PASS / COMPLETED
CLOSURE_SYNC = P4-WP020-LIVE-R4-PRE1-CLOSE
CLOSURE_TYPE = CONTROL-DOC ONLY
CANONICAL_MAIN = 170e82d19315e80cc7393922d7daa1b1c7f2093b
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
PAID_LIVE_EXECUTION = STOP / NOT AUTHORIZED
R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_PAID_EXECUTION = NOT AUTHORIZED
R4_EXECUTION_ID = NONE
R4_EXECUTION_FENCE = NONE
NEXT_CANDIDATE_GATE = R4 PAID EXECUTION PLANNING/AUTHORIZATION / REQUIRES SEPARATE OWNER AUTHORIZATION
```

---

## Closed R4-PRE1 Evidence

`P4-WP020-LIVE-R4-PRE1 — NO-PAID Runtime Readiness Verification`

Owner-authorized boundary:
- exact canonical main `170e82d19315e80cc7393922d7daa1b1c7f2093b`;
- evidence-only/no-paid runtime validation;
- no image generation;
- no paid workflow execution;
- no execution-fence consumption.

Observed evidence:

```text
Run 34302711166
Workflow: WP020 LIVE R3 No-Paid Preflight
Conclusion: SUCCESS
Head SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
PREFLIGHT_PASS
required_credentials_present=true
generation_request_sent=false
paid_provider_calls=0
execution_fence_written=false

Run 34302730786
Workflow: WP020 LIVE R3 PRE1 Gemini Access Probe (No-Paid)
Conclusion: SUCCESS
Head SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
provider=gemini_image
model=gemini-3.1-flash-image
http_status=200
status=ACCESS_PROBE_PASS
generation_request_sent=false
paid_generation_calls=0
```

The current GitHub Actions Gemini credential successfully authenticated in runtime and could read metadata for `gemini-3.1-flash-image`. The secret value itself remains unreadable and is not recorded.

The two NO-PAID runs overlapped briefly but used the same exact main SHA and no paid mutable execution state or fence, so the evidence remains valid.

R4-PRE1 provider generation calls = 0.
R4-PRE1 spend added = USD 0.00.

---

## Confirmed External Gemini Remediation

Owner-supplied Google AI Studio evidence:

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

Together with the successful runtime metadata probe, this closes the immediate credential/quota readiness blocker that caused the prior R3 Gemini HTTP 429. It does not authorize any new provider generation request.

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
7. R3 identity must never be rerun.

---

## Stop Rule After R4-PRE1

No new implementation or paid/live execution is active.

Do not auto-start R4 paid execution. After this closure sync merges, any R4 paid attempt requires a separate Owner-approved planning/authorization gate that creates a new immutable execution identity and binds it to the exact then-current main.

A future R4 paid run must still require fresh no-paid preflight, new one-shot fence, bounded budget/call limits, and separate explicit Owner run authorization.

No gate auto-authorizes the next one.
