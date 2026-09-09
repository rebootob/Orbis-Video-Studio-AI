# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN: 170e82d19315e80cc7393922d7daa1b1c7f2093b

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: R3 STOPPED / CONSUMED / NEVER RERUN
P4-WP020-LIVE-R3-C1: PASS / MERGED / CLOSED
P4-WP020-LIVE-R3-C1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PRE1-CLOSE: CONTROL-DOC ONLY / OWNER AUTHORIZED

ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: R4-PRE1-CLOSE DOC SYNC -> EXACT-HEAD REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED
R4_PAID_EXECUTION: NOT AUTHORIZED
R4_EXECUTION_ID: NONE
R4_EXECUTION_FENCE: NONE
```

---

## R4-PRE1 Closure Evidence

Owner authorized `P4-WP020-LIVE-R4-PRE1 — NO-PAID Runtime Readiness Verification` on exact canonical main `170e82d19315e80cc7393922d7daa1b1c7f2093b`.

Observed GitHub Actions evidence:

```text
Full runtime preflight:
  workflow: wp020-live-r3-preflight.yml
  run: 34302711166
  conclusion: SUCCESS
  head SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
  status: PREFLIGHT_PASS
  required_credentials_present: true
  generation_request_sent: false
  paid_provider_calls: 0
  execution_fence_written: false

Gemini metadata-only access probe:
  workflow: wp020-live-r3-pre1-gemini-access.yml
  run: 34302730786
  conclusion: SUCCESS
  head SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
  provider: gemini_image
  model: gemini-3.1-flash-image
  HTTP status: 200
  status: ACCESS_PROBE_PASS
  generation_request_sent: false
  paid_generation_calls: 0
```

The current GitHub Actions Gemini credential successfully authenticated against the configured image model in runtime. The secret value is not readable, exposed, or persisted.

The two NO-PAID runs overlapped briefly in wall-clock time. This does not invalidate the evidence because both ran on the same exact main SHA, neither performed generation, neither consumed a paid execution fence, and neither shared paid mutable execution state.

R4-PRE1 provider generation calls = 0.
R4-PRE1 spend added = USD 0.00.
R4 paid execution remains NOT AUTHORIZED.

---

## External Gemini Billing / Quota Remediation Evidence

Owner-supplied Google AI Studio evidence confirms:

```text
Gemini project: Orbis-Video-Production
Billing tier: Tier 1 / Prepay
Credit balance observed: USD 5.00
Nano Banana 2 (Gemini 3.1 Flash Image):
  RPM: 100
  TPM: 200K
  RPD: 1K
Prior Free-tier observation for the image model: 0 / 0 / 0
```

The prior R3 Gemini HTTP 429 is therefore consistent with the old Free-tier image quota-zero condition rather than a proven Orbis code defect. The later R4-PRE1 runtime probe now also proves that the currently configured GitHub Actions Gemini credential can authenticate and see `gemini-3.1-flash-image` without generation.

This evidence does not authorize R4 paid/live execution.

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
- conservative chargeable requests = 2/6;
- last known confirmed/committed UAT cost = USD 0.0072;
- Vidu / ElevenLabs / downstream = NOT EXECUTED;
- never rerun R2.

### R3
```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Execution Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence: CONSUMED
Status: STOPPED
Phase: LIVE-02-GEMINI-IMAGE
```
- immediate no-paid preflight = PASS;
- OpenAI STORY = SUCCESS;
- OpenAI usage = 546 prompt / 513 completion tokens;
- last known committed/actual Orbis UAT cost at STOP = USD 0.0065;
- Gemini IMAGE = HTTP 429;
- retryable true / submission_uncertain false;
- conservative calls = 2/6;
- Vidu / ElevenLabs / downstream = NOT EXECUTED;
- R3 MUST NEVER BE RERUN.

USD 0.0065 is known Orbis UAT cost evidence only; failed Gemini external billing is not proven either way.

---

## Next Gate

There is no active implementation package.

After `P4-WP020-LIVE-R4-PRE1-CLOSE` merges, the next candidate is a separately Owner-authorized R4 paid execution planning/authorization gate. It must first create a new immutable R4 execution identity and bind it to the exact then-current canonical main.

Any future R4 paid execution still requires:
1. a new immutable R4 execution identity;
2. fresh exact-main Owner paid/live authorization;
3. fresh no-paid preflight immediately before fence consumption;
4. a new one-shot execution fence;
5. separate explicit Owner run authorization;
6. bounded hard-cap/call-count enforcement and STOP-on-uncertainty semantics.

No gate auto-authorizes the next one.
