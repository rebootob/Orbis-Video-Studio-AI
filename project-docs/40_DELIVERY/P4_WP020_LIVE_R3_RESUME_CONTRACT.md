# P4-WP020-LIVE-R3 — Proposed Full-Chain Resume Contract

**Status:** TOOLING PREPARATION OWNER-AUTHORIZED / NOT PAID-AUTHORIZED / NOT EXECUTED  
**Execution identity:** `LIVE-20260909-363F-R3`  
**Tooling base main:** `363ffe6a0bd325c7c557b80daa665ee3575df6f8`  
**Binding paid main SHA:** NOT YET ASSIGNED — must equal the exact post-TOOL1-merge canonical `main` at fresh Owner paid authorization  
**PRE1 prerequisite:** PASS / COMPLETED

TOOL1 authorization permits implementation/testing/review of manual-only R3 tooling. It does not authorize a provider generation request, workflow dispatch, execution fence, release, or deployment.

## Accepted prerequisite evidence

```text
R3 PRE1: PASS / COMPLETED
PR #75 merge: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Metadata probe run: 34291500281
Probe: ACCESS_PROBE_PASS / HTTP 200
Model: gemini-3.1-flash-image
generation_request_sent: false
paid_generation_calls: 0
PRE1 spend: USD 0.00

PRE1-CLOSE PR #76 merge: 363ffe6a0bd325c7c557b80daa665ee3575df6f8
```

PRE1 proves metadata-level credential/model visibility only. It does not prove image-generation submission success.

## Why R3 is a fresh full chain

R2 used ephemeral PostgreSQL and MinIO. Its retained artifact is historical evidence rather than reusable project/database state. A truthful full LIVE PASS therefore requires a new isolated UAT project whose provider assets, approvals, cost evidence, render outputs and archive lineage all belong to one coherent run.

## Locked R3 paid boundary

Maximum chargeable provider requests: **6 total**.

1. OpenAI CreativeProvider — one STORY request maximum
   - `gpt-4o`
   - profile `FAST`
   - `OPENAI_MAX_RETRIES=0`
2. Gemini ImageProvider — one keyframe maximum
   - `gemini_image`
   - `gemini-3.1-flash-image`
   - 1K only
3. Vidu VideoProvider — one video maximum
   - `vidu`
   - `viduq2`
   - text-to-video
   - exactly 4 seconds / 720P
   - one idempotency key
4. ElevenLabs AudioProvider — three requests maximum
   - one bounded Thai VO/TTS request;
   - one BGM <= 10 seconds;
   - one ambience <= 3 seconds;
   - no voice cloning.

Exact paid sequence:

```text
OPENAI_CREATIVE_STORY:gpt-4o
GEMINI_IMAGE:gemini-3.1-flash-image:1K
VIDU_VIDEO:viduq2:text2video:4s:720p
ELEVENLABS_TTS:Thai:<=150chars
ELEVENLABS_MUSIC:<=10s
ELEVENLABS_AMBIENCE:<=3s
```

No other paid provider, model, regeneration, quality retry, batch generation, second shot, or additional media generation is in R3 scope.

## Hard budget and execution controls

```text
Dedicated UAT hard cap: USD 1.00
Maximum chargeable requests: 6
Execution order: sequential only
OpenAI automatic retries: 0
Workflow trigger: workflow_dispatch only
Canonical branch: main only
```

The cap is an authorization ceiling, not a spend target. Unknown/invalid cost evidence or projected hard-cap breach is a STOP.

## TOOL1 controls

TOOL1 prepares:

- pure contract guards for identity/SHA/fence/call sequence/budget/provider status;
- manual-only no-paid preflight;
- manual-only paid one-shot workflow;
- full-chain R3 runner;
- durable sanitized failure evidence copied to the workflow artifact before ephemeral runtime teardown;
- tests proving no dynamic R1 snapshot patching and no secret/raw-body/header evidence leakage.

Sanitized failure evidence may retain only operational metadata such as provider/model, HTTP status when already durably available, error code, retryable/submission-uncertain classification, job/clip identifiers, terminal status and cost. Raw provider bodies, response headers, prompts/payloads, credentials, API keys and media bytes are excluded.

## Required gates before any R3 paid request

1. TOOL1 implementation complete.
2. Full backend/frontend/migration CI for exact TOOL1 HEAD = PASS.
3. Independent review = PASS.
4. Owner explicitly approves TOOL1 merge.
5. TOOL1 merged to canonical `main`.
6. Fresh manual R3 no-paid preflight on exact post-merge `main` = PASS.
7. Owner provides fresh paid/live authorization exactly matching:
   `FRESH_OWNER_AUTHORIZED_R3: LIVE-20260909-363F-R3 @ <EXACT_POST_MERGE_MAIN_SHA>`.
8. Owner separately authorizes the actual paid run.
9. Paid workflow re-runs the no-paid preflight, rechecks the exact authorization/unused identity, then writes:
   `EXECUTION_STARTED: LIVE-20260909-363F-R3`
   immediately before invoking the runner.

No gate auto-authorizes the next gate.

## Execution sequence after all later gates

`LIVE-01 OpenAI STORY`
-> deterministic zero-billing storyboard/shot bridge
-> `LIVE-02 Gemini IMAGE`
-> `LIVE-03 Vidu VIDEO`
-> `LIVE-04 ElevenLabs VO/BGM/AMBIENCE`
-> zero-provider-paid downstream proof:
`Assembly -> Subtitle/SRT -> QC -> Human Approval -> Render -> 16:9/9:16/1:1 -> .orbis export/validate/CLONE`.

## Mandatory STOP conditions

After fence consumption, STOP immediately and never retry under the same execution identity if any of the following occurs:

- unknown/invalid pricing or cost truth;
- deterministic provider non-success;
- provider outcome uncertainty or `RECONCILIATION_REQUIRED`;
- call order/count drift;
- duplicate active job/idempotency conflict;
- durable asset materialization failure;
- USD 1.00 hard-cap breach;
- credential/secret leakage;
- project isolation/history/approval failure;
- S0/S1 release blocker.

Any STOP after `EXECUTION_STARTED` permanently consumes `LIVE-20260909-363F-R3`. Another paid attempt would require a new execution identity and fresh Owner authorization.

## Explicit exclusions

- no production deployment;
- no release tag;
- no R1/R2 identity reuse or marker mutation;
- no batch live generation;
- no second shot;
- no quality-driven regeneration;
- no provider expansion;
- no Post-Core-V1 feature work.

## PASS criteria

R3 can support a P4-WP020 LIVE PASS recommendation only if the complete authorized chain finishes within all bounds and successful provider results become durable Orbis truth with correct lineage, trustworthy cost evidence, downstream assembly/QC/approval/render/multi-output/archive proof and no S0/S1 blocker.

A full R3 PASS still stops for separate P4-WP020 closure / Core V1 release review. Release is never automatic.
