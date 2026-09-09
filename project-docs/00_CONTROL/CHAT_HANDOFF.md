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
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-C1
ACTIVE_TYPE = NO-PAID CORRECTIVE
OWNER_AUTHORIZED = YES
```

---

## Canonical Main / R4 Truth

```text
Canonical main at R4-C1 start:
b1538f655bf526384845c1e8c536ad6fddc66ca7

R4 execution identity:
LIVE-20260909-DE17-R4

R4 paid run:
34316188814

R4 execution main:
b1538f655bf526384845c1e8c536ad6fddc66ca7

R4 execution fence:
CONSUMED / NEVER RERUN

R4 terminal status:
STOPPED at LIVE-03-VIDU-VIDEO

Conservative paid calls:
3 / 6

Last known committed/actual Orbis UAT cost at STOP:
USD 0.0738
```

Issue #63 audit records:
- R4 exact paid authorization marker comment: `5596379504`;
- R4 RUN authorization audit comment: `5596415646`;
- R4 execution fence comment: `5596464603`;
- R4 STOP evidence comment: `5596467391`.

`LIVE-20260909-DE17-R4` is permanently consumed. Do not rerun its workflow or any failed job under this identity.

---

## R4 Provider Sequence Truth

The bounded run reached:

```text
1. OpenAI Story = SUCCESS
2. Gemini Image = SUCCESS
3. Vidu Video = FAILED
4. ElevenLabs TTS = NOT CALLED
5. ElevenLabs Music = NOT CALLED
6. ElevenLabs Ambience = NOT CALLED
```

The R4 artifact retained a Vidu GenerationJob estimate of USD 0.15. Repository code confirms this originates from dispatch-time pricing estimation; it is not proof of provider billing.

Controlled billing state:

```text
Vidu internal estimate = USD 0.15 / ESTIMATED
Vidu external billing for failed task = UNKNOWN
Last known committed/actual Orbis UAT cost at STOP = USD 0.0738
```

Do not state that the failed Vidu call was free or charged USD 0.15 unless provider-side usage/billing evidence proves it.

---

## Active R4-C1 Scope

Owner authorized:

```text
P4-WP020-LIVE-R4-C1 — Vidu Failure Evidence & Billing Reconciliation (NO-PAID)
```

Branch:
`ai/p4-wp020-live-r4-c1`

Allowed:
- preserve sanitized Vidu task identity on terminal failure;
- preserve safe typed provider status/error-code/credits metadata;
- keep raw response bodies, headers, prompts and secrets excluded;
- make durable failure evidence label job cost as estimated;
- keep failed-task external billing at `UNKNOWN` pending provider-side evidence;
- mocked regression tests;
- control/delivery doc synchronization.

Forbidden:
- provider API calls;
- R4 rerun;
- R5 creation;
- new fence consumption;
- paid workflow dispatch;
- release/tag/deploy;
- retrospective billing adjustment without evidence.

C1 provider calls = 0. C1 spend added = USD 0.00.

---

## Billing Reconciliation Evidence Still Needed

Provider-side Vidu Usage/Billing evidence should be matched to the R4 execution interval:

```text
Run start: 2026-09-09T05:45:42Z
STOP record: 2026-09-09T05:47:19Z
```

Until that evidence is accepted, external billing remains `UNKNOWN` and must not be guessed.

---

## Prior R4 Gates

```text
R4-PRE1 = PASS / COMPLETED / NO-PAID
R4-PRE1-CLOSE = PASS / MERGED / COMPLETE
R4-TOOL1 = PASS / MERGED / COMPLETE via PR #82
R4-TOOL1-CLOSE-R1 = PASS / MERGED / COMPLETE via PR #83
R4-PF1 = PASS / COMPLETED / NO-PAID, run 34313038252
R4-PF1-CLOSE = PASS / MERGED / COMPLETE via PR #84
R4-AUTH1 = PASS / AUTHORIZED
R4-RUN1 = STOPPED / CONSUMED / NEVER RERUN
```

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run: 34297314995
Status: STOPPED / CONSUMED
OpenAI STORY: SUCCESS
Gemini IMAGE: HTTP 429
Conservative calls: 2 / 6
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
R3 rerun: FORBIDDEN
```

---

## Current Gate / Next Gate

Current gate:

```text
P4-WP020-LIVE-R4-C1
NO-PAID corrective implementation
-> exact-head Backend/Frontend CI
-> independent review
-> STOP for Owner merge decision
```

C1 merge will not authorize R5 or any external provider call. Any future execution identity and any provider-side billing disposition remain separate Owner gates.

No gate auto-authorizes the next one.

---

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with separate provider boundaries: `CreativeProvider`, `ImageProvider`, `VideoProvider`, `AudioProvider`.

Core V1 modes: `STORY / SHORT / LOOP / SCENE`.
Cloud AI required; local AI disallowed; vendor lock-in disallowed; approval-gated automation required.
