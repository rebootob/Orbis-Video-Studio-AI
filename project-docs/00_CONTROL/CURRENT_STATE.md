# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.
>
> The closure state below becomes effective when this BILL1-CLOSE record is merged to canonical `main`. While the PR is open, live PR truth governs the merge gate.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_BILL1_CLOSE_START: da381bbd2cc407393e7326e9824bef68ea356e6b

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
P4-WP020-LIVE-R4-C1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-C1-CLOSE-R1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-BILL1: PASS / EVIDENCE ACCEPTED / NOT CHARGED
P4-WP020-LIVE-R4-BILL1-CLOSE: CLOSURE RECORD / EFFECTIVE ON MERGE TO MAIN

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
R4_VIDU_EXTERNAL_BILLING: NOT CHARGED / PROVIDER-SIDE EVIDENCE ACCEPTED

BILL1_AUTH_COMMENT: 5598882289
BILL1_DISPOSITION_COMMENT: 5598962073
BILL1_PROVIDER_CALLS: 0
BILL1_SPEND_ADDED: USD 0.00
VIDU_BALANCE_READINESS_EVIDENCE: 2000 CREDITS / OWNER-PROVIDED SCREENSHOT / NOT USD BILLING EVIDENCE

R5_IDENTITY: NONE / NOT AUTHORIZED
```

---

## BILL1 Provider-Side Billing Disposition

Owner authorized `P4-WP020-LIVE-R4-BILL1 — Vidu Provider-Side Billing Evidence Disposition (EVIDENCE-ONLY / NO-PAID)` on canonical main `da381bbd2cc407393e7326e9824bef68ea356e6b`.

Issue #63 audit trail:
- BILL1 authorization comment: `5598882289`;
- BILL1 accepted disposition comment: `5598962073`.

Accepted provider-side evidence was the Owner-provided Vidu Usage view for `2026-09-09` in `UTC0`, with `All Keys` and all task/model filters set to `ALL`, showing no Usage History records for the full date and therefore none for the R4 interval around `2026-09-09T05:45:42Z` through `2026-09-09T05:47:19Z`.

Controlled disposition:

```text
BILL1 = PASS / EVIDENCE ACCEPTED
R4 failed Vidu external billing = NOT CHARGED
Vidu internal job estimate = USD 0.15 / ESTIMATED ONLY
R4 last known committed/actual Orbis UAT cost at STOP = USD 0.0738
BILL1 provider calls = 0
BILL1 spend added = USD 0.00
```

No credits-to-USD conversion was inferred. The accepted disposition closes only the failed R4 Vidu task billing question; it does not retroactively change immutable R4 execution history.

The Owner later provided Vidu Credit Balance evidence showing `2,000 credits` after top-up. This is readiness evidence only. It is not proof of historical R4 billing and is not converted to USD in control records.

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

## C1 Closure Truth

```text
C1 PR #85 = PASS / MERGED / COMPLETE
C1 exact reviewed HEAD = c6f02fe56d4248011b0ef0cb96910d6997195e60
C1 merge commit = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
C1-CLOSE PR #86 = PASS / MERGED / COMPLETE
C1-CLOSE merge commit = 37bc4584eaa14bcf1d01243364548b2a3c39bcbb
C1-CLOSE-R1 PR #87 = PASS / MERGED / COMPLETE
C1-CLOSE-R1 merge commit = da381bbd2cc407393e7326e9824bef68ea356e6b
C1 provider calls = 0
C1 spend added = USD 0.00
```

C1 preserves sanitized Vidu terminal task/provider metadata for future evidence, keeps unsafe/raw provider content excluded, and distinguishes internal estimated job cost from provider-side billing truth.

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

## Post-BILL1-CLOSE Rule

Once this closure record is on canonical `main`, no active work package exists. A possible R5 NO-PAID readiness/preflight gate requires a separate explicit Owner authorization.

Do not create R5, call any provider, write a paid authorization marker, create/consume a new execution fence, dispatch a paid/live workflow, adjust billing, convert credits to USD, release, tag or deploy without a separate explicit Owner authorization.
