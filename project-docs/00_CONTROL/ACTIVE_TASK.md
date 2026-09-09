# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-PF1-CLOSE
ACTIVE_TITLE = R4 PF1 Closure / Control-Document Sync
ACTIVE_TYPE = CONTROL-DOC ONLY
OWNER_AUTHORIZED = YES
CANONICAL_MAIN = 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
ACTIVE_BRANCH = ai/p4-wp020-live-r4-pf1-close

LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R4-TOOL1-CLOSE-R1
LAST_CLOSED_STATUS = PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-PF1 = PASS / COMPLETED / NO-PAID
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED

R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_EXECUTION_ID = LIVE-20260909-DE17-R4
R4_PF1_AUTHORIZED_MAIN = 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
R4_PF1_RUN = 34313038252
R4_PF1_STATUS = PASS / COMPLETED / NO-PAID
R4_PAID_AUTHORIZATION = NOT AUTHORIZED
R4_EXECUTION_FENCE = NONE
R4_PAID_EXECUTION = NOT AUTHORIZED

PF1_PROVIDER_GENERATION_CALLS = 0
PF1_PAID_PROVIDER_CALLS = 0
PF1_SPEND_ADDED = USD 0.00
NEXT_GATE = EXACT-HEAD CI + INDEPENDENT REVIEW -> OWNER MERGE DECISION
```

---

## Canonical R4-PF1 Evidence

`P4-WP020-LIVE-R4-PF1 — Fresh Exact-Main NO-PAID Preflight`

```text
Owner-authorized exact main: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
Run: 34313038252
Workflow: WP020 LIVE R4 No-Paid Preflight
Event: workflow_dispatch
Conclusion: SUCCESS
status: PREFLIGHT_PASS
Execution ID: LIVE-20260909-DE17-R4
required_credentials_present: true
generation_request_sent: false
paid_provider_calls: 0
execution_fence_written: false
budget_cap_usd: 1.0
max_paid_calls: 6
estimated_total_reservation: USD 0.2739
spend_added: USD 0.00
Issue #63 result comment: 5596078866
```

Verified:
- manual canonical-main guard PASS;
- exact authorized SHA PASS;
- fresh PostgreSQL 16 migrations PASS through Alembic head;
- ephemeral MinIO health PASS;
- required credentials/config presence PASS without exposing secret values;
- provider routing/pricing/budget reservation PASS;
- no provider generation;
- no paid call;
- no paid authorization marker;
- no execution fence consumption.

---

## Historical PF1 Governance-Reconciliation Evidence

Run `34306778867` on `de08c98f2644ed9e56983aad265a82b32d91e462` remains historical technical NO-PAID evidence only. It was dispatched before a separately recorded Owner PF1 authorization gate and is not retroactively authorized.

Fresh run `34313038252` is now the canonical Owner-authorized R4-PF1 completion evidence.

---

## R4 Tooling Contract

R4 tooling remains:
- execution ID `LIVE-20260909-DE17-R4`;
- tooling base `de17a125dcd3b8066a546369d03aba813a7b5641`;
- hard cap USD 1.00;
- max 6 chargeable provider requests;
- sequential only;
- OpenAI retries 0;
- exact provider sequence OpenAI Story -> Gemini Image -> Vidu Video -> ElevenLabs TTS -> Music -> Ambience.

A future exact-SHA paid authorization marker, if separately Owner-authorized, is:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact main sha>
```

A future one-shot execution fence, if later separately authorized to RUN, is:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Neither exists during PF1-CLOSE.

---

## Stop Rule

This work package is documentation-only.

Do not dispatch any R4 paid workflow, do not create `FRESH_OWNER_AUTHORIZED_R4`, do not consume `EXECUTION_STARTED`, and do not send any provider-generation request.

After this closure merges, a separate exact-SHA Owner paid-authorization gate may be considered. A later explicit Owner RUN authorization remains a distinct gate.

No gate auto-authorizes the next one.
