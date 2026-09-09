# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-BILL1-CLOSE
ACTIVE_STATUS = OWNER AUTHORIZED / CONTROL-DOC ONLY
CANONICAL_MAIN_AT_BILL1_CLOSE_START = da381bbd2cc407393e7326e9824bef68ea356e6b

LAST_COMPLETED_EVIDENCE_GATE = P4-WP020-LIVE-R4-BILL1
LAST_COMPLETED_STATUS = PASS / EVIDENCE ACCEPTED / NOT CHARGED
BILL1_AUTH_COMMENT = 5598882289
BILL1_DISPOSITION_COMMENT = 5598962073

P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED

R4_EXECUTION_ID = LIVE-20260909-DE17-R4
R4_EXECUTION_RUN = 34316188814
R4_EXECUTION_MAIN = b1538f655bf526384845c1e8c536ad6fddc66ca7
R4_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_PAID_EXECUTION = STOPPED
R4_STOP_PHASE = LIVE-03-VIDU-VIDEO
R4_CONSERVATIVE_PAID_CALLS = 3 / 6
R4_LAST_KNOWN_COMMITTED_ACTUAL_UAT_COST = USD 0.0738
R4_VIDU_JOB_ESTIMATE = USD 0.15 / ESTIMATED
R4_VIDU_EXTERNAL_BILLING = NOT CHARGED / PROVIDER-SIDE EVIDENCE ACCEPTED

BILL1_PROVIDER_CALLS = 0
BILL1_SPEND_ADDED = USD 0.00
VIDU_BALANCE_READINESS_EVIDENCE = 2000 CREDITS / OWNER-PROVIDED SCREENSHOT / NOT USD BILLING EVIDENCE

R5_IDENTITY = NONE / NOT AUTHORIZED
NEXT_GATE_AFTER_CLOSE = OWNER DECISION REQUIRED
```

---

## BILL1 Evidence Accepted

`P4-WP020-LIVE-R4-BILL1 — Vidu Provider-Side Billing Evidence Disposition (EVIDENCE-ONLY / NO-PAID)` is complete at the evidence-disposition level.

Accepted evidence:
- Owner-provided Vidu Usage view for `2026-09-09` in `UTC0`;
- `All Keys` selected;
- task/model filters set to `ALL`;
- no Usage History records shown for the date;
- therefore no provider-recorded usage entry exists for the R4 interval around `2026-09-09T05:45:42Z` through `2026-09-09T05:47:19Z`.

Controlled disposition:

```text
BILL1 = PASS / EVIDENCE ACCEPTED
FAILED R4 VIDU TASK EXTERNAL BILLING = NOT CHARGED
VIDU INTERNAL JOB ESTIMATE = USD 0.15 / ESTIMATED ONLY
R4 LAST KNOWN COMMITTED/ACTUAL ORBIS UAT COST = USD 0.0738
BILL1 PROVIDER CALLS = 0
BILL1 SPEND ADDED = USD 0.00
```

No credits-to-USD conversion is authorized or inferred.

The Owner subsequently provided Vidu Credit Balance evidence showing `2,000 credits` after top-up. Treat this only as readiness evidence for a possible future gate. It does not alter historical R4 billing evidence and does not authorize any provider request.

---

## Immutable R4 Execution Truth

```text
Execution ID: LIVE-20260909-DE17-R4
Workflow run: 34316188814
Execution main: b1538f655bf526384845c1e8c536ad6fddc66ca7
Conclusion: FAILURE / STOP
Fence comment: 5596464603
STOP comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative paid calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Provider sequence reached:
- OpenAI STORY: SUCCESS;
- Gemini IMAGE: SUCCESS;
- Vidu VIDEO: terminal `FAILED`;
- ElevenLabs TTS / Music / Ambience: NOT CALLED.

`LIVE-20260909-DE17-R4` is consumed and MUST NEVER be rerun.

---

## BILL1-CLOSE Contract

This gate may synchronize control/delivery documentation only to the accepted BILL1 evidence.

Hard exclusions:
- no source/test/workflow/provider implementation changes;
- no Vidu API call;
- no provider generation call;
- no R4 rerun;
- no R5 identity;
- no paid authorization marker;
- no execution fence;
- no paid/live workflow dispatch;
- no billing adjustment;
- no credits-to-USD conversion;
- no release/tag/deploy.

After exact-head CI and independent review, STOP for explicit Owner merge decision.

If merged, `ACTIVE_WORK_PACKAGE` returns to `NONE`. Any R5 readiness/preflight work requires a new explicit Owner authorization and remains NO-PAID unless separately authorized otherwise.
