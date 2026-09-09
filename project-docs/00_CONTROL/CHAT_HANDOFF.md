# Chat Session Handoff

> Canonical location: `project-docs/00_CONTROL/CHAT_HANDOFF.md`
>
> Repository/workflow/Issue #63 truth newer than this file is authoritative.

Repository: `rebootob/Orbis-Video-Studio-AI`
Canonical branch: `main`

---

## Canonical Project State (Post-Merge Truth)

```text
ACTIVE_WORK_PACKAGE = NONE
CURRENT_GATE = WAITING_FOR_EXPLICIT_OWNER_NEXT_GATE
NEXT_GATE = OWNER DECISION REQUIRED

LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-PRE1-CLOSE-R1
LAST_COMPLETED_STATUS = PASS / MERGED / COMPLETE
R1_BASE_MAIN = 817539b619c4b28f22273ff01df733c612a2a386
PARENT_GATE = P4-WP020-LIVE-R5-PRE1-CLOSE (PR #90)

R5_READINESS_IDENTITY = WP020-LIVE-R5-PRE1
R5_PAID_IDENTITY = NONE / NOT AUTHORIZED
R5_PAID_EXECUTION = NOT AUTHORIZED

P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
R4 = STOPPED / CONSUMED / NEVER RERUN

PROVIDER_GENERATION_CALLS = 0
PAID_PROVIDER_CALLS = 0
VIDU_CREDITS_CONSUMED = 0
PAID_FENCE_WRITTEN = false
PAID_LIVE_DISPATCH = false
```

Next Gate Direction:
- Canonical post-merge state is `ACTIVE_WORK_PACKAGE = NONE` and `NEXT_GATE = OWNER DECISION REQUIRED`.
- A future bounded Vidu credit-generation probe is NOT authorized by R5-PRE1-CLOSE / R1 and requires a separate explicit Owner authorization.

---

## Pre-Merge PR #91 Review Routing (Historical / In-Flight Execution Note)

> [!NOTE]
> This section is an execution-flight reference for the PR #91 review/merge gate only. Once PR #91 is merged to `main`, canonical authority resides solely in the post-merge project state above.

```text
PR = #91
TITLE = docs(wp020-live): actualize post-merge control state for R5-PRE1 closure
BRANCH = ai/p4-wp020-live-r5-pre1-close-r1
BASE MAIN AT R1 START = 817539b619c4b28f22273ff01df733c612a2a386
GATE = P4-WP020-LIVE-R5-PRE1-CLOSE-R1
STATUS = AWAITING CHATGPT RE-REVIEW & OWNER MERGE APPROVAL
```

Pre-Merge Action Routing:
- Fresh-fetch canonical `main` and branch `ai/p4-wp020-live-r5-pre1-close-r1`.
- Verify exact-head CI success.
- Confirm CONTROL-DOC only scope (updating post-merge control state to be self-closing).
- Present for ChatGPT independent review.
- STOP for explicit Owner merge authorization. DO NOT merge without Owner approval.

---

## Historical Work Packages

### Historical R5-PRE1-CLOSE Gate (PR #90)
- PR #90 merged to canonical `main` at commit `817539b619c4b28f22273ff01df733c612a2a386`.
- Status: `PASS / MERGED / COMPLETE`.

### Historical R5-PRE1 Tooling Delivery (PR #89)
- Tooling PR #89 merged to canonical `main` at commit `46cd9e85d68b58e9d276673e6834c81167218de9`.
- Dedicated readiness workflow run `34351326791` executed on canonical `main` with conclusion `SUCCESS` / `NO-PAID`.
- Preserved as historical evidence.

### Historical BILL1-CLOSE Gate (PR #88)
- PR #88 merged to canonical `main` at commit `8c8eb871b6d2a0522b1764c4d5e1eeae0ea1e822`.
- Preserved as historical evidence.

---

## Delivery Baseline

```text
P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
Completed planned Core V1 work packages = 19 / 20
P4-WP020 = ACTIVE / NOT CLOSED
Core V1 release = NOT DECLARED
P4-WP020-LIVE-R5-PRE1 = PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R5-PRE1-CLOSE = PASS / MERGED / COMPLETE
P4-WP020-LIVE-R5-PRE1-CLOSE-R1 = PASS / MERGED / COMPLETE
ACTIVE_WORK_PACKAGE = NONE
NEXT_GATE = OWNER DECISION REQUIRED
R5_PRE1_RUN = 34351326791
R5_READINESS_IDENTITY = WP020-LIVE-R5-PRE1
R5_PAID_IDENTITY = NONE / NOT AUTHORIZED
R5_PAID_EXECUTION = NOT AUTHORIZED
R4 = STOPPED / CONSUMED / NEVER RERUN
R4 BILL1 = PASS / EVIDENCE ACCEPTED / NOT CHARGED
```

Canonical main at R1 start:
`817539b619c4b28f22273ff01df733c612a2a386`

Always fresh-fetch `main` before any status, merge, authorization or execution decision.

---

## Accepted R5-PRE1 Preflight Truth

Owner authorized `P4-WP020-LIVE-R5-PRE1` under Issue #63 comments `5600206595` and `5600227540`.
Workflow run `34351326791` executed on canonical `main` `46cd9e85d68b58e9d276673e6834c81167218de9`.

Verified:
- PostgreSQL 16 migrations + clean starting DB state (0 usage ledger rows, 0 generation jobs);
- Ephemeral MinIO storage write/read/delete;
- Credentials present for OpenAI, Gemini, Vidu, ElevenLabs;
- Adapter constructors and configs valid without generation calls;
- Local pricing estimator valid for all 6 sequential chargeable request targets across OpenAI, Gemini, Vidu, and ElevenLabs within USD 1.00 reservation ceiling;
- Zero provider generation calls, zero paid provider calls, zero Vidu credits consumed, zero paid fences;
- Owner-provided balance of 2,000 Vidu credits documented as readiness evidence only (not converted to USD).

Closure authorized: Issue #63 comment `5601980565` (merged to main in PR #90 commit `817539b619c4b28f22273ff01df733c612a2a386`).

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
