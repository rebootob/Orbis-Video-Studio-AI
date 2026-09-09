# Chat Session Handoff

> Canonical location: `project-docs/00_CONTROL/CHAT_HANDOFF.md`
>
> Repository/workflow/Issue #63 truth newer than this file is authoritative.

Repository: `rebootob/Orbis-Video-Studio-AI`
Canonical branch: `main`

---

## Delivery Baseline

```text
P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
Completed planned Core V1 work packages = 19 / 20
P4-WP020 = ACTIVE / NOT CLOSED
Core V1 release = NOT DECLARED
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-PF1-CLOSE
ACTIVE_TYPE = CONTROL-DOC ONLY
OWNER_AUTHORIZED = YES
R4_PAID_EXECUTION = NOT AUTHORIZED
```

---

## Canonical Main / R4 Truth

```text
Current canonical main:
7de0d3344cd32a1a016f0ee1f4d6121861c57a43

R4-TOOL1:
PASS / MERGED / COMPLETE via PR #82
Reviewed HEAD: 7fe35f3c51d248435ab1c90355b29cd1ade66f67
Merge commit: de08c98f2644ed9e56983aad265a82b32d91e462

R4-TOOL1-CLOSE-R1:
PASS / MERGED / COMPLETE via PR #83
Reviewed HEAD: 978d85518450e1eaa0d3026ce2abc90295567f97
Merge commit: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43

R4 execution identity:
LIVE-20260909-DE17-R4

R4 paid authorization: NOT AUTHORIZED
R4 execution fence: NONE
R4 paid execution: NOT AUTHORIZED
```

R4 contract remains hard cap USD 1.00, maximum 6 sequential chargeable requests, OpenAI retries 0, exact provider order OpenAI Story -> Gemini Image -> Vidu Video -> ElevenLabs TTS -> Music -> Ambience.

Future paid authorization marker, only after a separate Owner gate:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact authorized main SHA>
```

Future one-shot fence, only after a later separate Owner RUN authorization reaches execution:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Neither exists now.

---

## Fresh Owner-Authorized R4-PF1

Owner explicitly authorized `P4-WP020-LIVE-R4-PF1 — Fresh Exact-Main NO-PAID Preflight` on exact main `7de0d3344cd32a1a016f0ee1f4d6121861c57a43`.

Canonical PF1 evidence:

```text
Run: 34313038252
Workflow: WP020 LIVE R4 No-Paid Preflight
Run number: 2
Event: workflow_dispatch
Head SHA: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
Conclusion: SUCCESS
status: PREFLIGHT_PASS
required_credentials_present: true
generation_request_sent: false
paid_provider_calls: 0
execution_fence_written: false
budget cap: USD 1.00
max paid calls: 6
estimated total reservation: USD 0.2739
PF1 spend added: USD 0.00
```

Verified runtime readiness:
- manual canonical-main guard PASS;
- exact authorized SHA PASS;
- fresh PostgreSQL 16 migration to Alembic head PASS;
- ephemeral MinIO health PASS;
- required credential/config presence PASS without exposing secret values;
- provider routing/pricing/budget reservation PASS;
- no provider-generation request;
- no paid call;
- no paid authorization marker;
- no execution-fence consumption.

Issue #63 PF1 result comment: `5596078866`.

---

## Prior PF1 Governance Reconciliation

Earlier run `34306778867` on main `de08c98f2644ed9e56983aad265a82b32d91e462` remains historical technical NO-PAID evidence only. It was not Owner-authorized as PF1 at dispatch time and is not retroactively authorized.

The fresh run `34313038252` is the canonical Owner-authorized PF1 completion evidence.

---

## Closed R4-PRE1 Evidence

```text
Run 34302711166 = SUCCESS full runtime no-paid preflight
Run 34302730786 = SUCCESS Gemini metadata GET / HTTP 200 / ACCESS_PROBE_PASS
Exact SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
Generation calls: 0
Spend added: USD 0.00
Fence: false
```

Owner-provided Google AI Studio evidence confirmed `Orbis-Video-Production` Tier 1 / Prepay and Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K.

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run: 34297314995
Execution main: 82ce42116e3f866227dd598814cf79c0b9c640c4
Status: STOPPED / CONSUMED
OpenAI STORY: SUCCESS
Gemini IMAGE: HTTP 429
Conservative calls: 2/6
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
R3 rerun: FORBIDDEN
```

---

## Current Gate / Next Gate

Current authorized gate:

```text
P4-WP020-LIVE-R4-PF1-CLOSE — CONTROL-DOC ONLY
```

Finish control-doc sync, exact-head CI, independent review, then STOP for Owner merge decision.

After PF1-CLOSE merges:
- do NOT auto-start paid execution;
- a separate exact-SHA Owner R4 paid-authorization gate may be considered;
- the paid authorization must still be separate from a later explicit Owner RUN authorization;
- no marker, fence, or provider generation exists until those later gates are explicitly approved.

No gate auto-authorizes the next one.

---

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with separate provider boundaries: `CreativeProvider`, `ImageProvider`, `VideoProvider`, `AudioProvider`.

Core V1 modes: `STORY / SHORT / LOOP / SCENE`.
Cloud AI required; local AI disallowed; vendor lock-in disallowed; approval-gated automation required.
