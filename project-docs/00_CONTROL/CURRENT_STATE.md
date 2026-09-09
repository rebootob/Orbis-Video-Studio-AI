# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_TOOL1_START: de17a125dcd3b8066a546369d03aba813a7b5641

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: R3 STOPPED / CONSUMED / NEVER RERUN
P4-WP020-LIVE-R3-C1: PASS / MERGED / CLOSED
P4-WP020-LIVE-R3-C1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PRE1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1: OWNER AUTHORIZED / NO-PAID IMPLEMENTATION

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R4-TOOL1
ACTIVE_BRANCH: ai/p4-wp020-live-r4-tool1
CURRENT_GATE: TOOL1 IMPLEMENTATION -> EXACT-HEAD CI -> INDEPENDENT REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: NOT REQUIRED FOR THIS CONTROL-PLANE TOOLING RUN
CODEX: STOP
CLAUDE_CODE: STOP

R4_EXECUTION_ID: LIVE-20260909-DE17-R4
R4_TOOLING_BASE_SHA: de17a125dcd3b8066a546369d03aba813a7b5641
R4_PAID_AUTHORIZATION: NOT AUTHORIZED
R4_EXECUTION_FENCE: NONE
R4_PAID_EXECUTION: NOT AUTHORIZED
TOOL1_PROVIDER_GENERATION_CALLS: 0
TOOL1_SPEND_AUTHORIZATION: USD 0.00
```

---

## R4-TOOL1 Contract

Owner authorized `P4-WP020-LIVE-R4-TOOL1 — NO-PAID Bounded One-Shot Tooling Preparation` on canonical main `de17a125dcd3b8066a546369d03aba813a7b5641`.

Immutable R4 identity and paid-chain ceiling:

```text
Execution ID: LIVE-20260909-DE17-R4
Issue record: #63
Hard cap: USD 1.00
Maximum chargeable requests: 6
Sequential only
OpenAI retries: 0
```

Exact future paid-call sequence:

1. OpenAI Story — `gpt-4o`
2. Gemini Image — `gemini-3.1-flash-image` / `1K`
3. Vidu Video — `viduq2` / text2video / 4s / 720p
4. ElevenLabs TTS — Thai / <=150 chars
5. ElevenLabs Music — <=10s
6. ElevenLabs Ambience — <=3s

Future authorization marker:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact post-merge main SHA>
```

Future fence:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Neither marker may be written during TOOL1.

Detailed contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R4_TOOL1.md`.

---

## Tooling Safety Model

R4 TOOL1 adds dedicated R4 contract, fence, preflight, runner adapter, STOP exporter, workflows and tests.

The R4 runner adapter reuses the exact reviewed R3 runner implementation only if its Git blob SHA remains:

```text
24150cdece623004443e03ceecea10490955822b
```

There is no dynamic source rewrite. Blob drift fails closed before provider execution. The R4 adapter rebinds only immutable contract globals and explicitly preserves sanitized STOP evidence handling.

The R4 preflight is manual/canonical-main only and MUST NOT invoke Creative/Image/Video/Audio generation. It must finish with:

```text
generation_request_sent=false
paid_provider_calls=0
execution_fence_written=false
```

The R4 paid workflow is prepared but inert until later exact Owner authorization and separate run authorization.

---

## R4-PRE1 Closed Evidence

```text
Full runtime preflight:
  run: 34302711166
  conclusion: SUCCESS
  head SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
  generation_request_sent: false
  paid_provider_calls: 0
  execution_fence_written: false

Gemini metadata-only access probe:
  run: 34302730786
  conclusion: SUCCESS
  head SHA: 170e82d19315e80cc7393922d7daa1b1c7f2093b
  model: gemini-3.1-flash-image
  HTTP status: 200
  status: ACCESS_PROBE_PASS
  generation_request_sent: false
  paid_generation_calls: 0
```

R4-PRE1 spend added = USD 0.00.

Owner-supplied Google AI Studio evidence confirmed:
- project `Orbis-Video-Production`;
- Tier 1 / Prepay;
- observed credit USD 5.00;
- Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K;
- prior Free-tier image quota was 0 / 0 / 0.

---

## Immutable LIVE History

R1 and R2 remain consumed and must never be rerun.

R3:

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

Complete R4-TOOL1 implementation, exact-head backend/frontend/migration CI, and independent review. Then STOP for explicit Owner merge decision.

A TOOL1 merge does NOT authorize R4 preflight dispatch, paid authorization, fence consumption, or paid execution.

Required later sequence remains:

```text
R4-TOOL1 merge
-> fresh R4 PF1 NO-PAID on exact post-merge main
-> fresh exact-SHA Owner R4 paid authorization
-> separate explicit Owner RUN authorization
-> only then R4 paid workflow may execute
```

No gate auto-authorizes the next one.
