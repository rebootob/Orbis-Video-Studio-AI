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
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-TOOL1
ACTIVE_TYPE = NO-PAID / CODE + TEST + CONTROL-DOC
OWNER_AUTHORIZED = YES
R4_PAID_EXECUTION = NOT AUTHORIZED
```

---

## Current Canonical / Tooling Truth

```text
Canonical main at R4 TOOL1 start:
de17a125dcd3b8066a546369d03aba813a7b5641

R4 TOOL1 branch:
ai/p4-wp020-live-r4-tool1

R4 execution identity:
LIVE-20260909-DE17-R4

R4 paid authorization: NOT AUTHORIZED
R4 execution fence: NONE
TOOL1 provider generation calls: 0
TOOL1 spend authorization: USD 0.00
```

R4-TOOL1 is tooling preparation only. It may add R4-specific contract/fence/preflight/runner/workflow/tests/control docs but may not dispatch provider generation, write the R4 paid authorization marker, consume the R4 fence, or dispatch the paid workflow.

Detailed contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R4_TOOL1.md`.

---

## R4 Tooling Design

Immutable future paid chain:

```text
1. OPENAI_CREATIVE_STORY:gpt-4o
2. GEMINI_IMAGE:gemini-3.1-flash-image:1K
3. VIDU_VIDEO:viduq2:text2video:4s:720p
4. ELEVENLABS_TTS:Thai:<=150chars
5. ELEVENLABS_MUSIC:<=10s
6. ELEVENLABS_AMBIENCE:<=3s
Hard cap: USD 1.00
Max chargeable requests: 6
Sequential only
OpenAI retries: 0
```

Future R4 Owner marker:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact post-merge main SHA>
```

Future R4 one-shot fence:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

The R4 runner adapter reuses only the exact independently reviewed R3 runner Git blob `24150cdece623004443e03ceecea10490955822b`. It does not dynamically rewrite source and must fail closed on blob drift.

---

## Closed R4-PRE1 Evidence

```text
Full runtime preflight run: 34302711166 = SUCCESS
Gemini metadata-only access probe: 34302730786 = SUCCESS / HTTP 200 / ACCESS_PROBE_PASS
Exact main: 170e82d19315e80cc7393922d7daa1b1c7f2093b
Generation calls: 0
Paid provider/generation calls: 0
Execution fence: false
Spend added: USD 0.00
```

Owner-provided Google AI Studio evidence:

```text
Project: Orbis-Video-Production
Billing tier: Tier 1 / Prepay
Observed credit: USD 5.00
Nano Banana 2 / Gemini 3.1 Flash Image:
  RPM 100
  TPM 200K
  RPD 1K
Prior Free-tier quota: 0 / 0 / 0
```

R4-PRE1-CLOSE merged as PR #81 and advanced canonical main to `de17a125dcd3b8066a546369d03aba813a7b5641`.

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run: 34297314995
Execution main: 82ce42116e3f866227dd598814cf79c0b9c640c4
Status: STOPPED / CONSUMED
STOP phase: LIVE-02-GEMINI-IMAGE
OpenAI STORY: SUCCESS
OpenAI usage: 546 prompt / 513 completion
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
Gemini IMAGE: HTTP 429
Gemini retryable: true
Gemini submission_uncertain: false
Conservative calls: 2/6
Vidu: NOT CALLED
ElevenLabs: NOT CALLED
Downstream: NOT STARTED
R3 rerun: FORBIDDEN
```

---

## Next Gate

Finish R4 TOOL1 implementation first.

Required sequence:

```text
R4 TOOL1 exact-head CI
-> independent review
-> Owner merge decision
-> fresh R4 PF1 NO-PAID on exact post-merge main
-> fresh exact-SHA Owner R4 paid authorization
-> separate explicit Owner RUN authorization
-> only then R4 paid workflow
```

No gate auto-authorizes the next one.

---

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with separate provider boundaries:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Core V1 modes: `STORY / SHORT / LOOP / SCENE`.
Later architecture only: `PRODUCT / EXPLAINER / PRESENTER / MONTAGE`.

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION_CORE_V1 = REQUIRED
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
VENDOR_LOCK_IN = DISALLOWED
```
