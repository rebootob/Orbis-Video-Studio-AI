# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_C1_START: b1538f655bf526384845c1e8c536ad6fddc66ca7

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020-LIVE-R4-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PRE1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1-CLOSE-R1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-PF1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PF1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-AUTH1: PASS / AUTHORIZED
P4-WP020-LIVE-R4-RUN1: STOPPED / CONSUMED / NEVER RERUN
P4-WP020-LIVE-R4-C1: OWNER AUTHORIZED / NO-PAID CORRECTIVE

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R4-C1
ACTIVE_BRANCH: ai/p4-wp020-live-r4-c1
CURRENT_GATE: C1 IMPLEMENTATION -> EXACT-HEAD CI -> INDEPENDENT REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

R3_EXECUTION_ID: LIVE-20260909-363F-R3
R3_EXECUTION_FENCE: CONSUMED / NEVER RERUN
R4_EXECUTION_ID: LIVE-20260909-DE17-R4
R4_EXECUTION_RUN: 34316188814
R4_EXECUTION_MAIN: b1538f655bf526384845c1e8c536ad6fddc66ca7
R4_EXECUTION_FENCE: CONSUMED / NEVER RERUN
R4_PAID_EXECUTION: STOPPED
R4_STOP_PHASE: LIVE-03-VIDU-VIDEO
R4_CONSERVATIVE_PAID_CALLS: 3 / 6
R4_LAST_KNOWN_COMMITTED_ACTUAL_UAT_COST: USD 0.0738
R4_VIDU_JOB_ESTIMATE: USD 0.15
R4_VIDU_EXTERNAL_BILLING: UNKNOWN / RECONCILIATION REQUIRED

C1_PROVIDER_CALLS: 0
C1_SPEND_ADDED: USD 0.00
```

---

## Immutable R4 RUN1 Evidence

Owner authorized the exact-main paid marker and then separately authorized one-shot RUN1. The paid workflow was manually dispatched once.

```text
Execution ID: LIVE-20260909-DE17-R4
Run: 34316188814
Workflow: WP020 LIVE R4 Paid One-Shot Execution
Event: workflow_dispatch
Head SHA: b1538f655bf526384845c1e8c536ad6fddc66ca7
Conclusion: FAILURE
Execution fence: CONSUMED
Fence comment: 5596464603
STOP comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative chargeable calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Reached provider sequence:
1. OpenAI Story — SUCCESS;
2. Gemini Image — SUCCESS with durable keyframe lineage/evidence;
3. Vidu Video — terminal `FAILED`;
4. ElevenLabs TTS — NOT CALLED;
5. ElevenLabs Music — NOT CALLED;
6. ElevenLabs Ambience — NOT CALLED.

R4 STOP is final for this identity. `LIVE-20260909-DE17-R4` MUST NEVER BE RERUN.

---

## Vidu Failure / Billing Truth

The sanitized R4 artifact captured the failed Vidu generation job with an internal `cost_usd` value of USD 0.15. Source inspection shows `GenerationJob.cost_usd` is initialized from `ProviderPricingService.estimate_cost()` when a generation job is created. It is therefore an estimate/commitment signal, not direct provider billing evidence.

The ledger confirms actual cost only on paths where actual usage is known. The failed Vidu terminal path did not establish provider-side actual billing.

Current controlled interpretation:

```text
Vidu internal job estimate: USD 0.15 / ESTIMATED
Failed Vidu external billing: UNKNOWN
R4 last known committed/actual Orbis UAT cost at STOP: USD 0.0738
Provider-side charge/free conclusion: NOT YET PROVEN
```

No retrospective cost adjustment is authorized without provider-side evidence.

---

## R4-C1 Authorized Corrective

C1 is a NO-PAID evidence-quality corrective. It is allowed to:
- retain sanitized Vidu `task_id`/provider-job identity on terminal failure when supplied;
- retain safe typed provider state, provider error code and provider credits;
- keep raw provider bodies, headers, prompts and credentials excluded;
- persist the typed safe fields through the durable queue evidence boundary;
- relabel Vidu job cost in R4 durable failure evidence as `estimated_cost_usd` / `ESTIMATED`;
- mark failed Vidu external billing `UNKNOWN` pending provider usage/billing evidence;
- add mocked regression tests;
- sync control/delivery documents.

C1 does not authorize external provider I/O, R5, a new fence, release/tag/deploy, or any spend.

---

## Billing Reconciliation Requirement

To determine whether the failed R4 Vidu request caused an external charge, use provider-side Vidu Usage/Billing evidence for the execution interval around:

```text
Run start: 2026-09-09T05:45:42Z
STOP record: 2026-09-09T05:47:19Z
```

Until such evidence is accepted, preserve `R4_VIDU_EXTERNAL_BILLING = UNKNOWN`.

---

## Prior PF1 Evidence

Canonical Owner-authorized R4 PF1 remains run `34313038252` on exact main `7de0d3344cd32a1a016f0ee1f4d6121861c57a43`, with `PREFLIGHT_PASS`, zero generation calls, zero paid calls, no fence and USD 0.00 spend added.

Earlier run `34306778867` remains historical technical NO-PAID evidence only because it was dispatched before a separately recorded Owner PF1 authorization gate.

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Execution Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence: CONSUMED
Status: STOPPED
Phase: LIVE-02-GEMINI-IMAGE
OpenAI STORY: SUCCESS
Gemini IMAGE: HTTP 429
Conservative calls: 2 / 6
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
```

R3 MUST NEVER BE RERUN.

---

## Next Gate

Finish `P4-WP020-LIVE-R4-C1`, obtain exact-head Backend/Frontend CI and independent review, then STOP for explicit Owner merge decision.

Do not create R5 or call any provider as part of C1. After C1 merge, the external billing evidence disposition and any future execution identity remain separately Owner-gated.
