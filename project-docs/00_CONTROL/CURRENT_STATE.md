# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN: de08c98f2644ed9e56983aad265a82b32d91e462

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020-LIVE-R4-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PRE1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1-CLOSE-R1: OWNER AUTHORIZED / CONTROL-DOC + PF1 GOVERNANCE RECONCILIATION

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R4-TOOL1-CLOSE-R1
ACTIVE_BRANCH: ai/p4-wp020-live-r4-tool1-close-r1
CURRENT_GATE: CONTROL-DOC SYNC + PF1 GOVERNANCE RECONCILIATION -> EXACT-HEAD CI -> INDEPENDENT REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

R3_EXECUTION_ID: LIVE-20260909-363F-R3
R3_EXECUTION_FENCE: CONSUMED / NEVER RERUN
R4_EXECUTION_ID: LIVE-20260909-DE17-R4
R4_TOOLING_BASE_SHA: de17a125dcd3b8066a546369d03aba813a7b5641
R4_PAID_AUTHORIZATION: NOT AUTHORIZED
R4_EXECUTION_FENCE: NONE
R4_PAID_EXECUTION: NOT AUTHORIZED

RECONCILIATION_PROVIDER_GENERATION_CALLS: 0
RECONCILIATION_SPEND_ADDED: USD 0.00
```

---

## R4-TOOL1 Closure Truth

R4 tooling was merged by PR #82.

```text
Reviewed PR HEAD: 7fe35f3c51d248435ab1c90355b29cd1ade66f67
Merge commit / current main: de08c98f2644ed9e56983aad265a82b32d91e462
Execution ID: LIVE-20260909-DE17-R4
Issue record: #63
Hard cap: USD 1.00
Maximum chargeable requests: 6
Sequential only
OpenAI retries: 0
```

Exact future paid-call sequence remains:

1. OpenAI Story — `gpt-4o`
2. Gemini Image — `gemini-3.1-flash-image` / `1K`
3. Vidu Video — `viduq2` / text2video / 4s / 720p
4. ElevenLabs TTS — Thai / <=150 chars
5. ElevenLabs Music — <=10s
6. ElevenLabs Ambience — <=3s

Future authorization marker:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact authorized main SHA>
```

Future fence:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Neither exists for R4 at this gate.

---

## PF1 Governance Reconciliation

A post-TOOL1 R4 no-paid preflight was dispatched before a separate Owner PF1 authorization gate was recorded.

Observed run:

```text
Run: 34306778867
Workflow: WP020 LIVE R4 No-Paid Preflight
Head SHA: de08c98f2644ed9e56983aad265a82b32d91e462
Conclusion: SUCCESS
Technical status: PREFLIGHT_PASS
required_credentials_present: true
generation_request_sent: false
paid_provider_calls: 0
execution_fence_written: false
estimated_total_reservation: USD 0.2739
```

Governance classification:
- technically valid NO-PAID evidence;
- dispatched outside a separately recorded Owner PF1 gate;
- NOT adopted as Owner-authorized R4 PF1 completion;
- no retroactive authorization is inferred;
- no paid authorization marker was created;
- no R4 execution fence was consumed;
- no provider generation was authorized or executed by this run.

Issue #63 reconciliation record: comment `5595805718`.

---

## Closed R4-PRE1 Evidence

```text
Full runtime preflight run: 34302711166 = SUCCESS
Gemini metadata-only probe: 34302730786 = SUCCESS / HTTP 200 / ACCESS_PROBE_PASS
Exact main: 170e82d19315e80cc7393922d7daa1b1c7f2093b
Generation calls: 0
Paid provider/generation calls: 0
Fence written: false
Spend added: USD 0.00
```

Owner-supplied Google AI Studio evidence confirmed `Orbis-Video-Production` Tier 1 / Prepay and Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K.

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
Conservative calls: 2/6
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
```

R3 MUST NEVER BE RERUN.

---

## Next Gate

Finish this reconciliation PR, exact-head CI, and independent review, then STOP for explicit Owner merge decision.

After merge, do not auto-start paid/live execution. The next Owner decision must explicitly choose one of:

```text
A) adopt run 34306778867 as PF1 evidence through a fresh governance gate; or
B) authorize a fresh R4 PF1 NO-PAID run on the then-current exact main.
```

Only after an Owner-authorized PF1 state may the project proceed to a separate exact-SHA R4 paid authorization, followed by a distinct Owner RUN authorization.

No gate auto-authorizes the next one.
