# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020-LIVE-R4-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PRE1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1-CLOSE-R1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-PF1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PF1-CLOSE: OWNER AUTHORIZED / CONTROL-DOC ONLY

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R4-PF1-CLOSE
ACTIVE_BRANCH: ai/p4-wp020-live-r4-pf1-close
CURRENT_GATE: PF1 CONTROL-DOC SYNC -> EXACT-HEAD CI -> INDEPENDENT REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

R3_EXECUTION_ID: LIVE-20260909-363F-R3
R3_EXECUTION_FENCE: CONSUMED / NEVER RERUN
R4_EXECUTION_ID: LIVE-20260909-DE17-R4
R4_TOOLING_BASE_SHA: de17a125dcd3b8066a546369d03aba813a7b5641
R4_PF1_AUTHORIZED_MAIN: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
R4_PF1_RUN: 34313038252
R4_PF1_STATUS: PASS / COMPLETED / NO-PAID
R4_PAID_AUTHORIZATION: NOT AUTHORIZED
R4_EXECUTION_FENCE: NONE
R4_PAID_EXECUTION: NOT AUTHORIZED

PF1_PROVIDER_GENERATION_CALLS: 0
PF1_PAID_PROVIDER_CALLS: 0
PF1_SPEND_ADDED: USD 0.00
```

---

## Fresh Owner-Authorized R4-PF1 Evidence

Owner authorized a fresh exact-main no-paid preflight on canonical main `7de0d3344cd32a1a016f0ee1f4d6121861c57a43`.

```text
Run: 34313038252
Workflow: WP020 LIVE R4 No-Paid Preflight
Run number: 2
Event: workflow_dispatch
Head SHA: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
Conclusion: SUCCESS
Technical status: PREFLIGHT_PASS
Execution ID: LIVE-20260909-DE17-R4
required_credentials_present: true
generation_request_sent: false
paid_provider_calls: 0
execution_fence_written: false
budget_cap_usd: 1.0
max_paid_calls: 6
estimated_total_reservation: USD 0.2739
spend_added: USD 0.00
```

Verified runtime readiness:
- manual canonical-main guard PASS;
- exact authorized SHA guard PASS;
- fresh PostgreSQL 16 migration to Alembic head PASS;
- ephemeral MinIO health PASS;
- required credential/config presence PASS without exposing secret values;
- provider routing PASS;
- pricing/budget reservation PASS;
- no provider-generation request sent;
- no R4 paid authorization marker created;
- no R4 execution fence consumed.

Issue #63 PF1 result record: comment `5596078866`.

This PF1 PASS authorizes no paid call by itself.

---

## Prior PF1 Governance-Reconciliation Evidence

Earlier run `34306778867` on main `de08c98f2644ed9e56983aad265a82b32d91e462` remains retained as historical technical NO-PAID evidence only because it was dispatched before a separately recorded Owner PF1 authorization gate.

It is not retroactively authorized and is not the canonical Owner-authorized PF1 completion.

The fresh Owner-authorized run `34313038252` above is the canonical R4-PF1 evidence for the current gate.

---

## R4-TOOL1 Closure Truth

R4 tooling was merged by PR #82 and governance reconciliation was closed by PR #83.

```text
TOOL1 reviewed PR HEAD: 7fe35f3c51d248435ab1c90355b29cd1ade66f67
TOOL1 merge commit: de08c98f2644ed9e56983aad265a82b32d91e462
TOOL1-CLOSE-R1 reviewed HEAD: 978d85518450e1eaa0d3026ce2abc90295567f97
TOOL1-CLOSE-R1 merge commit / PF1 authorized main: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
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

Future paid authorization marker, if separately Owner-authorized:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact authorized main SHA>
```

Future one-shot fence, if a later separate RUN authorization reaches the first chargeable request:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Neither exists at PF1-CLOSE.

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

Finish `P4-WP020-LIVE-R4-PF1-CLOSE` as CONTROL-DOC ONLY, run exact-head CI, obtain independent review, then STOP for explicit Owner merge decision.

After this closure merges, do not auto-start paid/live execution.

The next Owner gate may consider an exact-SHA R4 paid authorization for `LIVE-20260909-DE17-R4`. That paid authorization must be separate from a later explicit Owner RUN authorization.

PF1 PASS does not create the paid authorization marker, does not consume the execution fence, and does not authorize provider generation.

No gate auto-authorizes the next one.
