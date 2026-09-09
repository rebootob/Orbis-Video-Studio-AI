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
R4 = STOPPED / CONSUMED / NEVER RERUN
R4 BILL1 = PASS / EVIDENCE ACCEPTED / NOT CHARGED
R5 identity = NONE / NOT AUTHORIZED
```

Canonical main at BILL1-CLOSE start:
`da381bbd2cc407393e7326e9824bef68ea356e6b`

Always fresh-fetch `main` before any status, merge, authorization or execution decision.

---

## BILL1 Provider-Side Billing Truth

Owner authorized `P4-WP020-LIVE-R4-BILL1 — Vidu Provider-Side Billing Evidence Disposition (EVIDENCE-ONLY / NO-PAID)`.

Issue #63 audit records:
- BILL1 authorization: `5598882289`;
- BILL1 disposition: `5598962073`.

Accepted evidence was the Owner-provided Vidu Usage view with `UTC0` date range shown as `2026-08-09 - 2026-09-09`, with `All Keys` selected and Type / Model Version / Resolution / Template / Generate Mode filters at `ALL`. The Usage History area showed `No data to export` / no usage rows for the displayed range. That displayed range includes the R4 interval around `2026-09-09T05:45:42Z` through `2026-09-09T05:47:19Z`, so no provider-recorded usage entry was shown for that interval.

Controlled result:

```text
BILL1 = PASS / EVIDENCE ACCEPTED
R4 failed Vidu external billing = NOT CHARGED
Vidu internal job estimate = USD 0.15 / ESTIMATED ONLY
Last known committed/actual Orbis UAT cost at R4 STOP = USD 0.0738
BILL1 provider calls = 0
BILL1 spend added = USD 0.00
```

No credits-to-USD conversion was inferred.

Owner later provided Vidu Credit Balance evidence showing `2,000 credits` after top-up. This is readiness evidence only; it is not historical R4 billing evidence and does not authorize any provider request.

---

## R4-C1 / Closure History

```text
R4-C1 PR #85 = PASS / MERGED / COMPLETE
R4-C1 exact reviewed HEAD = c6f02fe56d4248011b0ef0cb96910d6997195e60
R4-C1 merge commit = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
R4-C1-CLOSE PR #86 = PASS / MERGED / COMPLETE
R4-C1-CLOSE merge commit = 37bc4584eaa14bcf1d01243364548b2a3c39bcbb
R4-C1-CLOSE-R1 PR #87 = PASS / MERGED / COMPLETE
R4-C1-CLOSE-R1 merge commit = da381bbd2cc407393e7326e9824bef68ea356e6b
C1 provider calls = 0
C1 spend added = USD 0.00
```

C1 preserves sanitized Vidu terminal task/provider metadata through durable evidence and makes the R4 failed Vidu job amount explicitly estimated rather than confirmed provider billing.

---

## Immutable R4 Truth

```text
Execution identity: LIVE-20260909-DE17-R4
Paid run: 34316188814
Execution main: b1538f655bf526384845c1e8c536ad6fddc66ca7
Execution fence: CONSUMED / NEVER RERUN
Terminal status: STOPPED / FAILURE
STOP phase: LIVE-03-VIDU-VIDEO
Conservative paid calls: 3 / 6
Last known committed/actual Orbis UAT cost at STOP: USD 0.0738
```

Issue #63 audit records:
- exact R4 paid authorization marker: `5596379504`;
- Owner RUN authorization: `5596415646`;
- execution fence: `5596464603`;
- STOP evidence: `5596467391`.

Provider sequence reached:

```text
1. OpenAI Story = SUCCESS
2. Gemini Image = SUCCESS
3. Vidu Video = FAILED
4. ElevenLabs TTS = NOT CALLED
5. ElevenLabs Music = NOT CALLED
6. ElevenLabs Ambience = NOT CALLED
```

`LIVE-20260909-DE17-R4` is permanently consumed. Never rerun R4 or any paid job under that identity.

---

## BILL1-CLOSE Gate

`P4-WP020-LIVE-R4-BILL1-CLOSE` is CONTROL-DOC ONLY. It exists only to synchronize accepted BILL1 evidence into repository control truth.

Hard exclusions:
- no source/test/workflow/provider implementation change;
- no Vidu API call;
- no provider generation call;
- no R4 rerun;
- no R5 identity;
- no paid authorization marker;
- no execution fence;
- no paid/live workflow dispatch;
- no billing adjustment;
- no credits-to-USD conversion;
- no release/tag/deploy.

After BILL1-CLOSE is merged, the project returns to `ACTIVE_WORK_PACKAGE = NONE` and waits for a separate explicit Owner next gate. A possible R5 readiness/preflight is not auto-authorized.

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

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with separate provider boundaries: `CreativeProvider`, `ImageProvider`, `VideoProvider`, `AudioProvider`.

Core V1 modes: `STORY / SHORT / LOOP / SCENE`.
Cloud AI required; local AI disallowed; vendor lock-in disallowed; approval-gated automation required.
