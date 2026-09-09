# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
ACTIVE_STATUS = WAITING FOR EXPLICIT OWNER NEXT GATE
CANONICAL_MAIN_AT_C1_CLOSE_SYNC_START = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5

LAST_COMPLETED_WORK_PACKAGE = P4-WP020-LIVE-R4-C1
LAST_COMPLETED_STATUS = PASS / MERGED / COMPLETE
LAST_COMPLETED_PR = 85
LAST_COMPLETED_REVIEWED_HEAD = c6f02fe56d4248011b0ef0cb96910d6997195e60
LAST_COMPLETED_MERGE_COMMIT = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5

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
R4_VIDU_JOB_ESTIMATE = USD 0.15 / ESTIMATED
R4_VIDU_EXTERNAL_BILLING = UNKNOWN / RECONCILIATION REQUIRED

C1_PROVIDER_CALLS = 0
C1_SPEND_ADDED = USD 0.00
R5_IDENTITY = NONE / NOT AUTHORIZED
NEXT_GATE = OWNER DECISION REQUIRED
```

---

## C1 Completion Evidence

`P4-WP020-LIVE-R4-C1 — Vidu Failure Evidence & Billing Reconciliation (NO-PAID)` is complete and merged through PR #85.

```text
Exact reviewed HEAD: c6f02fe56d4248011b0ef0cb96910d6997195e60
Merge commit: 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
Backend CI: 34323625029 = SUCCESS
Backend suite: 538 passed / 2 skipped / 3 warnings
Fresh-head migrations: SUCCESS
From-revision-010 migrations: SUCCESS
Frontend CI: 34323625048 = SUCCESS
Independent review: PASS
Provider calls from C1: 0
Spend added by C1: USD 0.00
```

C1 hardened the evidence path so safe typed Vidu failure metadata can survive durable persistence, while raw provider bodies, headers, prompts, credentials and provider error text remain excluded.

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

## Billing State After C1

```text
USD 0.15 = INTERNAL VIDU JOB ESTIMATE / ESTIMATED
USD 0.0738 = LAST KNOWN COMMITTED/ACTUAL ORBIS UAT COST AT STOP
FAILED VIDU TASK EXTERNAL BILLING = UNKNOWN
```

Do not claim the failed Vidu task was free or charged USD 0.15 without provider-side Usage/Billing evidence. The relevant execution interval is approximately `2026-09-09T05:45:42Z` through `2026-09-09T05:47:19Z`.

---

## Stop Rule

There is no active implementation or LIVE execution gate after C1 closure.

Do not create R5, call any provider, write a paid authorization marker, create/consume a new execution fence, dispatch a paid/live workflow, adjust external billing, release, tag or deploy unless the Owner explicitly authorizes that exact next gate.
