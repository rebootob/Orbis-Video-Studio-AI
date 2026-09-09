# P4-WP020-LIVE-R3-TOOL1 — Bounded One-Shot Execution Tooling Preparation

**Owner authorization:** APPROVED  
**Task type:** NO-PAID / CODE + TEST + CONTROL-DOC  
**Tooling base main:** `363ffe6a0bd325c7c557b80daa665ee3575df6f8`  
**Branch:** `ai/p4-wp020-live-r3-tool1`  
**R3 execution identity:** `LIVE-20260909-363F-R3`  
**Paid/live execution:** NOT AUTHORIZED  
**Provider generation calls in TOOL1:** 0  
**TOOL1 spend authorization:** USD 0.00

## Purpose

Prepare independently reviewable, manual-only R3 execution tooling after PRE1 completed. TOOL1 does not authorize any provider generation request, R3 execution fence, paid workflow dispatch, release tag, or production deployment.

## Authorized implementation

1. Pure R3 contract guards for exact execution identity, Owner authorization marker, one-shot fence marker, paid-call order, six-call ceiling, USD 1.00 hard cap, provider terminal-state fail-closed behavior, and sanitized evidence allowlists.
2. Manual-only R3 no-paid preflight workflow and script.
3. Manual-only R3 paid one-shot workflow that remains inert until a later exact Owner paid authorization exists for the post-merge `main` SHA.
4. New R3 full-chain runner for one isolated UAT project:
   - OpenAI STORY x1;
   - Gemini IMAGE x1;
   - Vidu VIDEO x1;
   - ElevenLabs AUDIO x3;
   - zero-provider-paid downstream assembly/subtitle/QC/approval/render/multi-output/archive proof.
5. Durable sanitized failure evidence copied into workflow artifacts before ephemeral DB/storage teardown. Raw provider bodies, response headers, prompts/payloads, credentials, API keys, and reference media bytes are excluded.
6. Tests for exact SHA binding, missing fence, out-of-order/extra calls, budget/unknown-cost STOP, non-success provider STOP, secret/body/header exclusion, manual-only workflows, preflight-before-fence ordering, and no dynamic R1 snapshot patching.
7. Control-truth synchronization only within P4-WP020 LIVE governance.

## Locked R3 provider/cost boundary

```text
1. OPENAI_CREATIVE_STORY:gpt-4o
2. GEMINI_IMAGE:gemini-3.1-flash-image:1K
3. VIDU_VIDEO:viduq2:text2video:4s:720p
4. ELEVENLABS_TTS:Thai:<=150chars
5. ELEVENLABS_MUSIC:<=10s
6. ELEVENLABS_AMBIENCE:<=3s

Maximum chargeable requests: 6
Hard cap: USD 1.00
Sequential only
OpenAI retries: 0
```

## Execution gates after TOOL1

TOOL1 implementation and merge do not authorize paid execution. Required later gates remain:

1. exact-head TOOL1 CI and independent review PASS;
2. Owner merge approval;
3. fresh R3 no-paid runtime preflight on the post-merge canonical `main`;
4. fresh Owner paid/live authorization marker exactly matching:
   `FRESH_OWNER_AUTHORIZED_R3: LIVE-20260909-363F-R3 @ <EXACT_POST_MERGE_MAIN_SHA>`;
5. separate explicit Owner run authorization;
6. paid workflow consumes `EXECUTION_STARTED: LIVE-20260909-363F-R3` only after its immediate no-paid preflight passes and immediately before the runner.

Any STOP after fence consumption permanently consumes this R3 identity. No automatic rerun is allowed.

## Explicit non-scope

- no provider generation request during TOOL1;
- no workflow dispatch during TOOL1;
- no R3 paid authorization marker during TOOL1;
- no R3 execution fence during TOOL1;
- no R1/R2 rerun or marker mutation;
- no release/tag/deployment;
- no Post-Core-V1 feature expansion.
