# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-TOOL1
ACTIVE_TITLE = Bounded One-Shot Execution Tooling Preparation
ACTIVE_TYPE = NO-PAID / CODE + TEST + CONTROL-DOC
OWNER_AUTHORIZED = YES
TOOLING_BASE_MAIN = de17a125dcd3b8066a546369d03aba813a7b5641
ACTIVE_BRANCH = ai/p4-wp020-live-r4-tool1

LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R4-PRE1-CLOSE
LAST_CLOSED_STATUS = PASS / MERGED / COMPLETE
CANONICAL_MAIN_AT_TOOL1_START = de17a125dcd3b8066a546369d03aba813a7b5641
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED

R3_EXECUTION_ID = LIVE-20260909-363F-R3
R3_EXECUTION_FENCE = CONSUMED / NEVER RERUN
R4_EXECUTION_ID = LIVE-20260909-DE17-R4
R4_PAID_AUTHORIZATION = NOT AUTHORIZED
R4_EXECUTION_FENCE = NONE
R4_PAID_EXECUTION = NOT AUTHORIZED

TOOL1_PROVIDER_GENERATION_CALLS = 0
TOOL1_SPEND_AUTHORIZATION = USD 0.00
NEXT_GATE = EXACT-HEAD CI + INDEPENDENT REVIEW -> OWNER MERGE DECISION
```

---

## R4-TOOL1 Authorized Scope

Owner authorized `P4-WP020-LIVE-R4-TOOL1 — NO-PAID Bounded One-Shot Tooling Preparation` after R4-PRE1 closure merged.

Authorized work:
- create immutable R4 execution contract for `LIVE-20260909-DE17-R4`;
- create R4-specific one-shot authorization/fence helper;
- create R4 no-paid preflight workflow/script;
- create R4 paid one-shot workflow that remains inert without later Owner gates;
- create R4 bounded runner adapter bound to the exact reviewed R3 implementation blob;
- preserve sanitized durable STOP evidence;
- add R4 tooling tests;
- synchronize control/delivery documents.

Explicitly NOT authorized during TOOL1:
- provider generation;
- R4 Owner paid-authorization marker;
- R4 fence consumption;
- paid workflow dispatch;
- release/tag/deploy.

Detailed contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R4_TOOL1.md`.

---

## Immutable R4 Tooling Contract

```text
Execution ID: LIVE-20260909-DE17-R4
Tooling base: de17a125dcd3b8066a546369d03aba813a7b5641
Issue: #63
Hard cap: USD 1.00
Maximum chargeable provider requests: 6
Sequential only
OpenAI retries: 0
```

Exact future paid-call order:

1. `OPENAI_CREATIVE_STORY:gpt-4o`
2. `GEMINI_IMAGE:gemini-3.1-flash-image:1K`
3. `VIDU_VIDEO:viduq2:text2video:4s:720p`
4. `ELEVENLABS_TTS:Thai:<=150chars`
5. `ELEVENLABS_MUSIC:<=10s`
6. `ELEVENLABS_AMBIENCE:<=3s`

Future paid authorization marker:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact post-merge main SHA>
```

Future fence:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Neither marker is authorized to be written during TOOL1.

---

## R4 Runner Reuse Guard

R4 reuses the already independently-reviewed R3 execution implementation only through a fail-closed adapter. The adapter requires the exact inherited R3 runner Git blob SHA:

```text
24150cdece623004443e03ceecea10490955822b
```

No dynamic source rewrite is permitted. If that inherited implementation drifts, R4 must STOP and return to review before any paid execution.

---

## Closed R4-PRE1 Evidence

```text
Full runtime preflight run: 34302711166 = SUCCESS
Gemini metadata-only probe: 34302730786 = SUCCESS / HTTP 200 / ACCESS_PROBE_PASS
Exact main: 170e82d19315e80cc7393922d7daa1b1c7f2093b
Generation requests: 0
Paid generation/provider calls: 0
Fence written: false
Spend added: USD 0.00
```

Owner-provided account evidence confirmed `Orbis-Video-Production` Tier 1 / Prepay and Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K.

---

## Stop Rule

TOOL1 must stop at the Owner merge decision after exact-head CI and independent review.

A TOOL1 merge does NOT authorize R4 preflight dispatch, paid authorization, execution-fence consumption, or paid execution. Later gates remain separate and require fresh exact-main evidence/authorization.
