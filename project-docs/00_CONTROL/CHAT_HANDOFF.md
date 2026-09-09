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
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R3-C1
```

---

## Current Canonical Truth

```text
Canonical main at C1 start:
82ce42116e3f866227dd598814cf79c0b9c640c4

R3:
Execution ID: LIVE-20260909-363F-R3
Run: 34297314995
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

Issue #63 evidence:
- Owner run authorization recorded before execution;
- execution fence comment `5594141834`;
- STOP evidence comment `5594143482`.

The failed Gemini request is counted conservatively as chargeable request #2. The repository does not prove whether Google externally billed that failed request.

---

## Active Corrective

`P4-WP020-LIVE-R3-C1 — Gemini 429 Quota/Rate-Limit Evidence Corrective`

Owner authorization:
- NO-PAID only;
- provider calls = 0;
- spend authorization = USD 0.00;
- branch `ai/p4-wp020-live-r3-c1-gemini-429-evidence`;
- base main `82ce42116e3f866227dd598814cf79c0b9c640c4`.

C1 purpose:
- retain a strict allowlist of structured Google 429 metadata;
- classify observable quota/rate categories without persisting message/body/headers/secrets;
- prove behavior with simulated tests;
- sync control truth.

C1 does NOT authorize R4, provider calls, paid execution, model/endpoint changes, release or deploy.

---

## Immutable Earlier History

- R1 consumed / HTTP 429 / never rerun.
- R2 consumed / OpenAI PASS / Gemini generic HTTP_ERROR / 2/6 / USD 0.0072 known cost / never rerun.
- R2-C1 merged PR #74, adding durable sanitized HTTP status evidence.
- R3-PRE1 metadata probe run `34291500281` PASS / HTTP 200 / zero generation calls.
- R3 TOOL1 merged PR #77.
- R3 PF1 run `34296382370` PASS / zero provider calls / reservation USD 0.2739.

---

## Next Gate

C1 implementation -> exact-head CI -> independent review -> Owner merge decision.

Do not auto-start R4. After C1 merge, fresh-review evidence and determine whether the remaining problem is account/quota configuration or requires any additional no-paid tooling before proposing another paid attempt.

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
