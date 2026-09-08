# P4-WP020-LIVE-R3-PRE1 — Gemini Access Probe + Resume Contract + Control-Truth Sync

**Status:** PASS / COMPLETED  
**Base main:** `d706acacd1f51224c955fb9c8d0d9eab3deda186`  
**Reviewed PRE1 HEAD:** `28f8095d581556b27feed67e27f82c004ea07bbc`  
**PR:** `#75`  
**Merge commit:** `dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b`  
**Provider generation calls during PRE1:** `0`  
**Paid spend during PRE1:** `USD 0.00`

## Purpose

Close the remaining pre-R3 configuration uncertainty without generating content or consuming a paid one-shot execution identity.

R2 stopped after OpenAI STORY succeeded and the subsequent Gemini image request returned a non-success HTTP outcome. C1 made future Gemini HTTP status evidence durable, but it cannot reconstruct the exact R2 status retroactively.

PRE1 therefore implemented and verified a metadata-level Gemini access check, synchronized control truth, and drafted the proposed R3 resume contract without paid authorization.

## Delivered PRE1 scope

1. Added a manual-only GitHub Actions workflow for a Gemini metadata access probe.
2. The probe performs only one authenticated metadata `GET` to:
   `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image`.
3. Authentication uses the configured `GEMINI_API_KEY` through the `x-goog-api-key` header.
4. Static guards prevent generation-capable paths such as `/interactions`, `generateContent`, and POST-based generation calls.
5. Probe evidence is sanitized to provider/model/status/http/error classification plus explicit no-generation counters.
6. Zero-network tests cover 200/400/401/403/404/429/5xx behavior, invalid model handling, and secret/provider-body non-leakage.
7. Control documents were synchronized.
8. The R3 full-chain resume contract remains draft/proposed only.

## Merge and CI evidence

PR #75 exact reviewed HEAD:
`28f8095d581556b27feed67e27f82c004ea07bbc`

Accepted CI evidence before merge:

```text
Backend: 479 passed, 2 skipped
PostgreSQL fresh-head migration: PASS
PostgreSQL from-revision-010 migration: PASS
Frontend workflow: PASS
Lint / typecheck / build / frontend tests: PASS
```

PR #75 merged to canonical main as:
`dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b`.

## Post-merge metadata probe evidence

```text
Workflow: WP020 LIVE R3 PRE1 Gemini Access Probe (No-Paid)
Run ID: 34291500281
Run main SHA: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Conclusion: success
Probe status: ACCESS_PROBE_PASS
HTTP status: 200
Provider: gemini_image
Model: gemini-3.1-flash-image
generation_request_sent: false
paid_generation_calls: 0
```

The static no-generation guard passed before the metadata request. Workflow permissions remained read-only and no R3 execution fence or paid authorization marker was written.

## Interpretation

PRE1 proves that the configured Gemini credential can authenticate to the metadata endpoint and that `gemini-3.1-flash-image` is visible there at the tested canonical main.

PRE1 does **not** prove that an image-generation submission will succeed. It also does not reconstruct the exact historical HTTP status from R2.

## Why R3 cannot simply continue from the R2 Story record

R2 ran on ephemeral PostgreSQL and MinIO services. The durable workflow artifact retained sanitized evidence, including Story identity and OpenAI usage/cost evidence, but not reusable Story/project database state. The ephemeral database was destroyed at job completion.

Therefore a later full end-to-end LIVE PASS cannot truthfully claim to resume the exact R2 project state. The proposed R3 contract must create a new isolated UAT project and rerun the bounded provider chain from the beginning unless a separately reviewed durable-state recovery mechanism exists.

This does not invalidate the accepted R2 OpenAI success evidence; it remains historical proof rather than reusable project state.

## Closure safety state

- no OpenAI generation request occurred in PRE1;
- no Gemini generation request occurred in PRE1;
- no Vidu request occurred in PRE1;
- no ElevenLabs request occurred in PRE1;
- PRE1 paid generation calls = 0;
- PRE1 paid spend = USD 0.00;
- no R1/R2 rerun;
- no R3 execution fence;
- no R3 paid authorization marker;
- no release tag;
- no production deployment;
- no Core V1 release declaration.

## Next gate — Not Authorized

PRE1 is closed. No next work package is auto-authorized.

The next proposed gate is **R3 paid one-shot execution-tooling preparation only**. ChatGPT must fresh-review canonical `main` and present a bounded tooling contract for explicit Owner authorization before implementation.

A later paid R3 execution still requires:

1. reviewed and merged R3 execution tooling;
2. a fresh execution identity;
3. exact binding to then-current canonical main;
4. fresh no-paid preflight;
5. fresh Owner paid/live authorization;
6. a new one-shot execution fence immediately before the first chargeable request.
