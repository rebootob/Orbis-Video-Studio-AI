# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-TOOL1-CLOSE-R1
ACTIVE_TITLE = R4 TOOL1 Closure + PF1 Governance Reconciliation
ACTIVE_TYPE = CONTROL-DOC + GOVERNANCE RECONCILIATION
OWNER_AUTHORIZED = YES
CANONICAL_MAIN = de08c98f2644ed9e56983aad265a82b32d91e462
ACTIVE_BRANCH = ai/p4-wp020-live-r4-tool1-close-r1

LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R4-TOOL1
LAST_CLOSED_STATUS = PASS / MERGED / COMPLETE
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED

R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_EXECUTION_ID = LIVE-20260909-DE17-R4
R4_PAID_AUTHORIZATION = NOT AUTHORIZED
R4_EXECUTION_FENCE = NONE
R4_PAID_EXECUTION = NOT AUTHORIZED

RECONCILIATION_PROVIDER_GENERATION_CALLS = 0
RECONCILIATION_SPEND_ADDED = USD 0.00
NEXT_GATE = EXACT-HEAD CI + INDEPENDENT REVIEW -> OWNER MERGE DECISION
```

---

## Closed R4-TOOL1 Evidence

`P4-WP020-LIVE-R4-TOOL1 — NO-PAID Bounded One-Shot Tooling Preparation`

```text
PR: #82
Reviewed HEAD: 7fe35f3c51d248435ab1c90355b29cd1ade66f67
Merge commit: de08c98f2644ed9e56983aad265a82b32d91e462
Backend CI: 34305801438 = SUCCESS
Backend tests: 533 passed / 2 skipped / 3 warnings
Frontend CI: 34305801517 = SUCCESS
Independent review: PASS / READY FOR OWNER MERGE DECISION
Provider generation during TOOL1: 0
TOOL1 spend: USD 0.00
```

R4 tooling contract remains:
- execution ID `LIVE-20260909-DE17-R4`;
- tooling base `de17a125dcd3b8066a546369d03aba813a7b5641`;
- hard cap USD 1.00;
- max 6 chargeable provider requests;
- sequential only;
- OpenAI retries 0;
- exact provider sequence OpenAI Story -> Gemini Image -> Vidu Video -> ElevenLabs TTS -> Music -> Ambience;
- exact future Owner marker `FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact main sha>`;
- one-shot fence `EXECUTION_STARTED: LIVE-20260909-DE17-R4`.

No R4 paid authorization or fence exists yet.

---

## PF1 Governance Reconciliation

Post-merge run `34306778867` executed the prepared R4 no-paid preflight on exact main `de08c98f2644ed9e56983aad265a82b32d91e462`.

Observed technical evidence:

```text
Conclusion: SUCCESS
status: PREFLIGHT_PASS
required_credentials_present: true
generation_request_sent: false
paid_provider_calls: 0
execution_fence_written: false
estimated_total_reservation: USD 0.2739
```

Governance status:
- the run occurred without a separately recorded Owner PF1 authorization gate;
- retain it as technical NO-PAID evidence only;
- do NOT classify it as Owner-authorized PF1 completion;
- do NOT infer retroactive authorization;
- it does not authorize or consume the R4 paid fence;
- it does not authorize provider generation or the paid workflow.

Issue #63 reconciliation comment: `5595805718`.

---

## Closed R4-PRE1 Evidence

```text
Run 34302711166 = SUCCESS full runtime no-paid preflight
Run 34302730786 = SUCCESS Gemini metadata-only probe / HTTP 200 / ACCESS_PROBE_PASS
Exact SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
Generation calls: 0
Paid calls: 0
Fence: false
Spend added: USD 0.00
```

Owner-provided account evidence confirmed `Orbis-Video-Production` Tier 1 / Prepay and Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K.

---

## Stop Rule

This work package is documentation/governance reconciliation only.

Do not dispatch any R4 paid workflow, do not create `FRESH_OWNER_AUTHORIZED_R4`, and do not consume `EXECUTION_STARTED`.

After this closure merges, the next gate requires a fresh Owner decision to either adopt run `34306778867` as PF1 evidence or authorize a new R4 PF1 NO-PAID run on the then-current exact main. Paid authorization and RUN authorization remain later, separate gates.

No gate auto-authorizes the next one.
