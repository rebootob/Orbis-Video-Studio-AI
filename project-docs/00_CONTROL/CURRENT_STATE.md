# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_R3: 82ce42116e3f866227dd598814cf79c0b9c640c4

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: R3 STOPPED / CONSUMED / GEMINI HTTP 429

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R3-C1
CURRENT_GATE: NO-PAID 429 EVIDENCE CORRECTIVE -> CI -> INDEPENDENT REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED
R4: NOT AUTHORIZED
```

---

## Immutable LIVE History

### R1
- consumed and immutable;
- bounded OpenAI request returned HTTP 429;
- never rerun R1.

### R2
```text
Execution ID: LIVE-20260909-BB75-R2
Run ID: 34287696335
Main SHA: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
Execution fence: CONSUMED
```
- OpenAI STORY = SUCCESS;
- Gemini IMAGE = non-success surfaced as `HTTP_ERROR`;
- exact historical Gemini HTTP status unavailable;
- conservative chargeable requests = 2/6;
- last known confirmed/committed UAT cost = USD 0.0072;
- Vidu / ElevenLabs / downstream = NOT EXECUTED;
- never rerun R2.

### R2-C1
- PR #74 merged at `d706acacd1f51224c955fb9c8d0d9eab3deda186`;
- future Gemini non-2xx status/classification became durable;
- provider calls 0 / spend USD 0.00.

### R3-PRE1
- PR #75 merged;
- metadata probe run `34291500281` = PASS / HTTP 200;
- model `gemini-3.1-flash-image` visible;
- generation calls 0 / spend USD 0.00.

### R3 TOOL1 / PF1
- TOOL1 merged via PR #77;
- canonical paid tooling main = `82ce42116e3f866227dd598814cf79c0b9c640c4`;
- PF1 run `34296382370` = `PREFLIGHT_PASS`;
- estimated reservation USD 0.2739 < USD 1.00;
- PF1 generation calls 0 / fence false.

### R3 LIVE
```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence comment: 5594141834
STOP evidence comment: 5594143482
Execution fence: CONSUMED
Status: STOPPED
Phase: LIVE-02-GEMINI-IMAGE
```

Observed:
- immediate pre-fence no-paid preflight = PASS;
- OpenAI STORY = SUCCESS;
- OpenAI usage = 546 prompt / 513 completion tokens;
- last known committed/actual Orbis UAT cost at STOP = USD 0.0065;
- Gemini IMAGE = HTTP 429;
- Gemini classification = retryable true / submission_uncertain false;
- conservative calls = 2/6;
- Vidu / ElevenLabs / downstream = NOT EXECUTED;
- R3 MUST NEVER BE RERUN.

USD 0.0065 is known Orbis UAT cost evidence only; failed Gemini external billing is not proven either way.

---

## Active Gate — R3-C1

`P4-WP020-LIVE-R3-C1 — Gemini 429 Quota/Rate-Limit Evidence Corrective`

Owner-authorized NO-PAID corrective only. It may improve sanitized structured 429 evidence and simulated tests. It must not change provider routing/model/endpoint/pricing/retry policy and must not send provider requests.

Goal: if a future separately authorized execution receives HTTP 429, durable evidence can distinguish safe observable classes such as quota-zero, daily quota, minute rate limit, other quota exhaustion, or generic `RESOURCE_EXHAUSTED` without storing provider message/body/headers/secrets.

R4 remains NOT AUTHORIZED.

---

## Required Next Gate

1. C1 exact-head backend/frontend/migration CI PASS.
2. Independent review PASS.
3. Owner merge decision.
4. Only after C1 merge and fresh review may an R4 corrective/execution plan be proposed.
5. Any future paid execution requires a new identity, fresh exact-main authorization, fresh no-paid preflight, new one-shot fence, and separate Owner run authorization.

No gate auto-authorizes the next one.
