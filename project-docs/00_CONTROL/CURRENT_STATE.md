# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_C1_CLOSE_SYNC_START: 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5

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
P4-WP020-LIVE-R4-C1: PASS / MERGED / COMPLETE

ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: WAITING_FOR_EXPLICIT_OWNER_NEXT_GATE

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
R4_VIDU_JOB_ESTIMATE: USD 0.15 / ESTIMATED
R4_VIDU_EXTERNAL_BILLING: UNKNOWN / RECONCILIATION REQUIRED

C1_PR: 85
C1_REVIEWED_HEAD: c6f02fe56d4248011b0ef0cb96910d6997195e60
C1_MERGE_COMMIT: 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
C1_PROVIDER_CALLS: 0
C1_SPEND_ADDED: USD 0.00
R5_IDENTITY: NONE / NOT AUTHORIZED
```

---

## C1 Closure Truth

`P4-WP020-LIVE-R4-C1 — Vidu Failure Evidence & Billing Reconciliation (NO-PAID)` completed its bounded corrective and was merged through PR #85.

Exact reviewed C1 HEAD:
`c6f02fe56d4248011b0ef0cb96910d6997195e60`

Merge commit / canonical main at closure-sync start:
`4ff697c9cd0698406ce248e95ec4a69df8cd2fc5`

Exact-head evidence before merge:
- Backend CI `34323625029` = SUCCESS;
- backend suite = 538 passed / 2 skipped / 3 warnings;
- fresh PostgreSQL migrations `fresh-head` = SUCCESS;
- fresh PostgreSQL migrations `from-revision-010` = SUCCESS;
- Frontend CI `34323625048` = SUCCESS;
- independent review = PASS / READY FOR OWNER MERGE DECISION;
- C1 provider calls = 0;
- C1 spend added = USD 0.00.

C1 preserves sanitized Vidu terminal task/provider metadata for future evidence, keeps unsafe/raw provider content excluded, and distinguishes internal estimated job cost from provider-side billing truth.

---

## Immutable R4 RUN1 Evidence

```text
Execution ID: LIVE-20260909-DE17-R4
Run: 34316188814
Workflow: WP020 LIVE R4 Paid One-Shot Execution
Execution Head SHA: b1538f655bf526384845c1e8c536ad6fddc66ca7
Conclusion: FAILURE / STOP
Execution fence: CONSUMED / NEVER RERUN
Fence comment: 5596464603
STOP comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative chargeable calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Reached provider sequence:
1. OpenAI Story — SUCCESS;
2. Gemini Image — SUCCESS;
3. Vidu Video — terminal `FAILED`;
4. ElevenLabs TTS — NOT CALLED;
5. ElevenLabs Music — NOT CALLED;
6. ElevenLabs Ambience — NOT CALLED.

R4 STOP is final for this identity. `LIVE-20260909-DE17-R4` MUST NEVER BE RERUN.

---

## Vidu Failure / Billing Truth

Controlled interpretation after C1:

```text
Vidu internal job estimate: USD 0.15 / ESTIMATED
Failed Vidu external billing: UNKNOWN
R4 last known committed/actual Orbis UAT cost at STOP: USD 0.0738
Provider-side charge/free conclusion: NOT YET PROVEN
```

The USD 0.15 value originates from dispatch-time pricing estimation and is not direct provider billing evidence. No retrospective provider billing adjustment is authorized without provider-side evidence.

Provider-side Vidu Usage/Billing evidence should be matched to the R4 interval around:

```text
Run start: 2026-09-09T05:45:42Z
STOP record: 2026-09-09T05:47:19Z
```

Until accepted evidence exists, preserve `R4_VIDU_EXTERNAL_BILLING = UNKNOWN`.

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Execution Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence: CONSUMED / NEVER RERUN
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

No work package is auto-started after C1 closure.

The Owner must separately choose and authorize the next gate. Valid controlled directions include provider-side Vidu billing evidence disposition and, only after any required readiness work, consideration of a new R5 execution identity.

Do not create R5, write a new paid authorization marker, consume a new fence, dispatch a paid/live workflow, call a provider, release, tag or deploy without a separate explicit Owner authorization.
