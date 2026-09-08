# P4-WP020-LIVE-R3 — Proposed Full-Chain Resume Contract

**Status:** PROPOSED / NOT PAID-AUTHORIZED / NOT EXECUTED  
**Execution identity:** NOT YET ASSIGNED  
**Binding main SHA:** NOT YET ASSIGNED  
**Purpose:** define the next bounded full-chain LIVE attempt after PRE1 only.

This document does not authorize any paid provider request. The immutable R3 execution ID and exact authorized `main` SHA must be assigned only after R3 execution tooling is merged and fresh repository truth is reviewed.

## Why R3 is a full chain

R2 proved that the bounded OpenAI STORY request can succeed, but R2 used ephemeral PostgreSQL and MinIO services. The retained workflow artifact preserved sanitized evidence rather than reusable project/database state. The R2 Story record therefore cannot be reused as canonical input for a later end-to-end LIVE PASS.

R3 must create a new isolated UAT project and execute the bounded chain from the beginning so all successful provider assets and downstream evidence belong to one coherent project lineage.

## Proposed R3 provider boundary

Maximum chargeable provider requests: **6 total**.

1. OpenAI CreativeProvider — **1 request maximum**
   - model `gpt-4o`
   - one STORY generation only
   - profile `FAST`
   - `OPENAI_MAX_RETRIES=0`

2. Gemini ImageProvider — **1 request maximum**
   - provider `gemini_image`
   - model `gemini-3.1-flash-image`
   - 1K output only
   - one keyframe only

3. Vidu VideoProvider — **1 request maximum**
   - provider `vidu`
   - model `viduq2`
   - text-to-video only
   - exactly 4 seconds
   - 720P
   - one idempotency key

4. ElevenLabs AudioProvider — **3 requests maximum**
   - one bounded Thai VO/TTS request
   - one BGM request <= 10 seconds
   - one ambience/SFX request <= 3 seconds
   - no voice cloning

No other paid provider, model, regeneration, quality retry, batch operation, or additional media generation is in the proposed R3 scope.

## Proposed hard budget

```text
Dedicated UAT hard cap: USD 1.00
Maximum chargeable requests: 6
Execution order: sequential only
OpenAI automatic retries: 0
```

The cap is a maximum authorization ceiling, not a target spend. Every provider dispatch must pass current pricing validation before the call.

## Required preconditions before R3 paid authorization

All must be true:

1. PRE1 merged into canonical `main`.
2. Gemini metadata access probe returns `ACCESS_PROBE_PASS` on then-current `main`.
3. PRE1 probe evidence confirms:
   - HTTP 200;
   - exact model metadata identity;
   - generation request sent = false;
   - paid generation calls = 0.
4. R3 execution tooling is manual-only and separately reviewed.
5. Full backend/frontend/migration CI for the exact tooling HEAD is PASS.
6. A fresh no-paid runtime preflight validates:
   - current exact `main`;
   - credential presence only;
   - current pricing configuration;
   - provider routing;
   - USD 1.00 budget cap;
   - OpenAI retries = 0;
   - no pre-existing R3 execution fence.
7. Owner provides fresh paid/live authorization tied to exact post-tooling-merge `main` and immutable R3 execution ID.
8. Actual run requires a separate explicit run gate after authorization is recorded.

## Proposed execution sequence

`LIVE-01 OpenAI STORY`
-> deterministic zero-billing storyboard/shot bridge
-> `LIVE-02 Gemini IMAGE`
-> `LIVE-03 Vidu VIDEO`
-> `LIVE-04 ElevenLabs VO/BGM/AMBIENCE`
-> zero-provider-paid downstream proof:
`Assembly -> Subtitle/SRT -> QC -> Human Approval -> Render -> 16:9/9:16/1:1 -> .orbis export/validate/CLONE`

## Mandatory STOP conditions

STOP immediately, with no retry/rerun under the same execution identity, if any occurs after the one-shot fence is consumed:

- unknown or invalid pricing before a paid dispatch;
- provider outcome uncertainty or `RECONCILIATION_REQUIRED`;
- non-success deterministic provider response;
- idempotency or duplicate active-job conflict;
- durable asset materialization failure;
- cost/UsageLedger truth cannot be represented reliably;
- budget would exceed USD 1.00;
- credential or secret leakage;
- project isolation/history/approval failure;
- S0/S1 release blocker.

Any STOP after fence consumption requires a new execution identity and fresh Owner authorization before another paid attempt.

## Explicit exclusions

- no production deployment;
- no release tag;
- no batch live generation;
- no second shot;
- no quality-driven regeneration;
- no provider expansion;
- no Post-Core-V1 feature work;
- no R1/R2 identity reuse.

## PASS criteria

R3 can support a P4-WP020 LIVE PASS recommendation only if the full authorized chain completes within bounds and every successful provider result becomes durable Orbis truth with correct lineage, cost evidence, downstream assembly/QC/approval/render/multi-output/archive proof, and no S0/S1 blocker.

After a full R3 PASS, STOP for P4-WP020 closure / Core V1 release review and Owner release decision. No release is automatic.
