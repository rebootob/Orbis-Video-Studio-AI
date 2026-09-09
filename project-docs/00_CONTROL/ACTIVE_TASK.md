# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-C1
ACTIVE_TITLE = Vidu Failure Evidence & Billing Reconciliation
ACTIVE_TYPE = NO-PAID CORRECTIVE
OWNER_AUTHORIZED = YES
CANONICAL_MAIN_AT_START = b1538f655bf526384845c1e8c536ad6fddc66ca7
ACTIVE_BRANCH = ai/p4-wp020-live-r4-c1

LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R4-PF1-CLOSE
LAST_CLOSED_STATUS = PASS / MERGED / COMPLETE
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED

R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_EXECUTION_ID = LIVE-20260909-DE17-R4
R4_EXECUTION_RUN = 34316188814
R4_EXECUTION_MAIN = b1538f655bf526384845c1e8c536ad6fddc66ca7
R4_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_PAID_EXECUTION = STOPPED
R4_STOP_PHASE = LIVE-03-VIDU-VIDEO
R4_CONSERVATIVE_PAID_CALLS = 3 / 6
R4_LAST_KNOWN_COMMITTED_ACTUAL_UAT_COST = USD 0.0738
R4_VIDU_JOB_ESTIMATE = USD 0.15
R4_VIDU_EXTERNAL_BILLING = UNKNOWN / RECONCILIATION REQUIRED

C1_PROVIDER_CALLS = 0
C1_SPEND_ADDED = USD 0.00
NEXT_GATE = EXACT-HEAD CI + INDEPENDENT REVIEW -> OWNER MERGE DECISION
```

---

## Immutable R4 Execution Truth

Owner separately authorized R4 paid execution and manually dispatched run `34316188814` on exact main `b1538f655bf526384845c1e8c536ad6fddc66ca7`.

```text
Execution ID: LIVE-20260909-DE17-R4
Workflow: WP020 LIVE R4 Paid One-Shot Execution
Run: 34316188814
Conclusion: FAILURE / STOP
Fence comment: 5596464603
STOP comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative paid calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Provider sequence reached:
- OpenAI STORY: SUCCESS;
- Gemini IMAGE: SUCCESS and durable keyframe evidence created;
- Vidu VIDEO: terminal provider state `FAILED`;
- ElevenLabs TTS / Music / Ambience: NOT CALLED.

`LIVE-20260909-DE17-R4` is consumed and MUST NEVER be rerun.

---

## C1 Evidence Problem

The R4 failure artifact retained a Vidu `GenerationJob.cost_usd` value of USD 0.15. Repository code shows that field is the dispatch-time estimated cost, not proof of an external Vidu charge.

Therefore:

```text
USD 0.15 = INTERNAL ESTIMATED JOB COST
USD 0.0738 = LAST KNOWN COMMITTED/ACTUAL ORBIS UAT COST AT STOP
FAILED VIDU TASK EXTERNAL BILLING = UNKNOWN
```

Do not reinterpret the USD 0.15 estimate as confirmed external billing and do not reinterpret the Vidu failure as free.

Provider-side usage/billing evidence remains required to close the external billing question. The target reconciliation window is the R4 run around `2026-09-09T05:45:42Z` through the STOP record at `2026-09-09T05:47:19Z`.

---

## Authorized C1 Corrective Scope

C1 may only:
- preserve sanitized Vidu terminal task identity and typed provider metadata such as provider state, safe provider error code and provider credits when returned;
- keep raw provider bodies, headers, prompts and secrets excluded from durable evidence;
- label Vidu job cost as estimated rather than confirmed billing;
- label failed Vidu external billing as `UNKNOWN` until provider-side reconciliation evidence exists;
- add mocked regression tests for failed Vidu responses and durable evidence boundaries;
- synchronize control/delivery documentation with immutable R4 STOP truth.

C1 must not:
- call OpenAI, Gemini, Vidu or ElevenLabs;
- dispatch any LIVE workflow;
- create an R5 execution identity;
- create or consume a new execution fence;
- adjust provider billing without evidence;
- release, tag or deploy.

---

## Stop Rule

Finish C1 implementation and tests on the bounded branch, obtain exact-head Backend/Frontend CI and independent review, then STOP for explicit Owner merge decision.

C1 merge does not authorize R5 or any provider call. A future execution identity requires a separate Owner gate after C1 closure and billing evidence disposition.
