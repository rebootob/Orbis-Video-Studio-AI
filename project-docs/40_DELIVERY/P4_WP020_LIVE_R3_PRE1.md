# P4-WP020-LIVE-R3-PRE1 — Gemini Access Probe + Resume Contract + Control-Truth Sync

**Status:** OWNER AUTHORIZED / NO-PAID PRE1 IN PROGRESS  
**Base main:** `d706acacd1f51224c955fb9c8d0d9eab3deda186`  
**Working branch:** `ai/p4-wp020-live-r3-pre1`  
**Provider generation calls authorized:** `0`  
**Paid spend authorized:** `USD 0.00`

## Purpose

Close the remaining pre-R3 configuration uncertainty without generating content or consuming a paid one-shot execution identity.

R2 stopped after OpenAI STORY succeeded and the subsequent Gemini image request returned a non-success HTTP outcome. C1 made future Gemini HTTP status evidence durable, but it cannot reconstruct the exact R2 status retroactively.

PRE1 therefore performs only a metadata-level Gemini access check, synchronizes control truth after C1 merge, and defines the proposed R3 resume contract.

## Authorized PRE1 scope

1. Add a manual-only GitHub Actions workflow for a Gemini metadata access probe.
2. The probe may perform exactly one authenticated `GET` to:
   `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image`.
3. Authentication uses the configured `GEMINI_API_KEY` in the `x-goog-api-key` header.
4. The probe must never:
   - call `/interactions`;
   - call `generateContent`;
   - submit a prompt or image payload;
   - create an image or any other generated media;
   - write an execution fence;
   - write Issue #63;
   - expose API key, provider response body, or headers in evidence.
5. Persist/log only sanitized probe evidence:
   - status;
   - provider;
   - model;
   - HTTP status when known;
   - sanitized error classification;
   - `generation_request_sent=false`;
   - `paid_generation_calls=0`.
6. Add zero-network unit tests for success/failure classification and secret/body non-leakage.
7. Synchronize control documents to current C1-merged/PRE1-active truth.
8. Draft the R3 resume contract without authorizing paid execution.

## Probe outcomes

`ACCESS_PROBE_PASS` requires HTTP 200 and metadata identity `models/gemini-3.1-flash-image`.

Sanitized STOP classifications include:

- 400 -> `BAD_REQUEST`
- 401 -> `AUTHENTICATION_FAILED`
- 403 -> `AUTHORIZATION_FAILED`
- 404 -> `MODEL_NOT_VISIBLE`
- 429 -> `RATE_LIMITED`
- 5xx -> `PROVIDER_UNAVAILABLE`
- network failure -> `TRANSPORT_ERROR`

Any non-PASS result blocks preparation of R3 paid execution tooling until reviewed.

## Why R3 cannot simply continue from the R2 Story record

R2 ran on ephemeral PostgreSQL and MinIO services. The durable workflow artifact retained sanitized evidence, including Story identity and OpenAI usage/cost evidence, but not the reusable Story/project database state itself. The ephemeral database was destroyed at job completion.

Therefore a later full end-to-end LIVE PASS cannot truthfully claim to resume the exact R2 project state. The proposed R3 contract must create a new isolated UAT project and rerun the bounded provider chain from the beginning unless a separately reviewed durable-state recovery mechanism exists.

This does not invalidate the accepted R2 OpenAI success evidence; it only means that evidence is historical proof rather than reusable project state.

## Explicitly forbidden in PRE1

- no OpenAI request;
- no Gemini generation request;
- no Vidu request;
- no ElevenLabs request;
- no paid workflow dispatch;
- no R1/R2 rerun;
- no R3 execution fence;
- no R3 paid authorization marker;
- no release tag;
- no production deployment;
- no Core V1 release declaration.

## Merge-readiness evidence

Before merge proposal:

- targeted PRE1 tests PASS;
- full backend CI PASS;
- migration checks PASS;
- frontend CI PASS if repository policy triggers it;
- exact diff remains PRE1-only;
- workflow is `workflow_dispatch` only;
- workflow permissions are `contents: read` only;
- static no-generation guard PASS;
- no paid/live workflow is dispatched during PRE1 implementation;
- independent exact-head review PASS.

After merge, the metadata probe may be manually dispatched on canonical `main` under this already authorized NO-PAID PRE1 scope. A probe PASS still does not authorize R3 paid execution.

## Next gate

After PRE1 code/docs are merged and the metadata probe returns PASS:

1. prepare bounded R3 paid one-shot tooling against then-current exact `main`;
2. independently review exact tooling HEAD and CI;
3. merge only with Owner authorization;
4. record a fresh Owner paid/live authorization tied to the exact post-merge `main`;
5. execute only after a separate explicit run gate.
