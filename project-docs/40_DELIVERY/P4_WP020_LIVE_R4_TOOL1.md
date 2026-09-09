# P4-WP020-LIVE-R4-TOOL1 — Bounded One-Shot Execution Tooling Preparation

## Status

```text
TYPE: NO-PAID / CODE + TEST + CONTROL-DOC
OWNER_AUTHORIZED: YES
TOOLING_BASE_MAIN: de17a125dcd3b8066a546369d03aba813a7b5641
BRANCH: ai/p4-wp020-live-r4-tool1
R4_EXECUTION_ID: LIVE-20260909-DE17-R4
PROVIDER_GENERATION_AUTHORIZED: NO
SPEND_AUTHORIZED: USD 0.00
R4_PAID_EXECUTION_AUTHORIZED: NO
R4_EXECUTION_FENCE: NONE
```

## Purpose

Prepare a fresh immutable one-shot R4 execution toolchain after R3 was consumed and stopped at Gemini HTTP 429, and after the account-side Gemini quota/billing blocker was remediated and verified by R4-PRE1.

This work package prepares tooling only. It MUST NOT dispatch provider generation, create the R4 Owner paid-authorization marker, consume the R4 one-shot fence, or start R4 paid execution.

## Immutable R4 Contract

```text
Execution ID: LIVE-20260909-DE17-R4
Tooling base main: de17a125dcd3b8066a546369d03aba813a7b5641
Issue record: #63
Hard cap: USD 1.00
Maximum chargeable provider requests: 6
Execution: sequential only
OpenAI automatic retries: 0
```

Exact paid-call sequence:

1. `OPENAI_CREATIVE_STORY:gpt-4o`
2. `GEMINI_IMAGE:gemini-3.1-flash-image:1K`
3. `VIDU_VIDEO:viduq2:text2video:4s:720p`
4. `ELEVENLABS_TTS:Thai:<=150chars`
5. `ELEVENLABS_MUSIC:<=10s`
6. `ELEVENLABS_AMBIENCE:<=3s`

Any order drift, seventh call, unknown cost, cost over hard cap, uncertain provider submission, `RECONCILIATION_REQUIRED`, credential/config failure, secret leak, duplicate/used identity, durable materialization failure, ledger inconsistency, or new S0/S1 MUST STOP.

## Owner Authorization / Fence Model

Future paid authorization marker, only after a separately authorized gate:

```text
FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact 40-char canonical main SHA>
```

Future one-shot fence, consumed only inside the paid workflow after fresh no-paid preflight succeeds:

```text
EXECUTION_STARTED: LIVE-20260909-DE17-R4
```

Terminal evidence markers:

```text
LIVE_EXECUTION_PASS: LIVE-20260909-DE17-R4
LIVE_EXECUTION_STOPPED: LIVE-20260909-DE17-R4
```

If a fence or terminal marker already exists for this identity, the workflow MUST refuse to start.

## Tooling Design

R4 adds dedicated:

- `.github/scripts/wp020_live_r4_contract.py`
- `.github/scripts/wp020_live_r4_fence.sh`
- `.github/scripts/wp020_live_r4_preflight.py`
- `.github/scripts/wp020_live_uat_r4.py`
- `.github/scripts/wp020_live_r4_failure_export.py`
- `.github/workflows/wp020-live-r4-preflight.yml`
- `.github/workflows/wp020-live-execution-r4.yml`
- `backend/tests/test_wp020_live_r4_tooling.py`

The R4 UAT runner adapter reuses only the exact frozen, independently reviewed R3 runner implementation with Git blob SHA:

```text
24150cdece623004443e03ceecea10490955822b
```

It does not rewrite source dynamically. It fails closed if that inherited implementation blob drifts, then rebinds only the execution contract globals to the R4 contract. R4 STOP evidence handling is explicitly preserved because an imported R3 module does not execute its historical `__main__` exception block.

## NO-PAID Preflight

The R4 preflight is manual `workflow_dispatch` on canonical `main` only and may validate:

- exact main checkout / tooling-base ancestry;
- required credential presence without revealing values;
- OpenAI/Gemini/Vidu/ElevenLabs adapter configuration;
- routing/model settings;
- pricing estimates and USD 1.00 reservation guard;
- PostgreSQL migrations;
- ephemeral S3-compatible object storage read/write/delete;
- empty usage ledger / no generation jobs.

It MUST report:

```text
generation_request_sent=false
paid_provider_calls=0
execution_fence_written=false
```

It MUST NOT call any generation method.

## Paid Workflow — Prepared but Inert

`wp020-live-execution-r4.yml` is manual-only and remains inert until later gates are separately completed.

Required runtime order:

1. canonical-main/manual/ancestry guard;
2. exact fresh R4 Owner authorization marker + unused identity check;
3. runtime bootstrap;
4. fresh R4 no-paid preflight;
5. recheck and consume R4 one-shot fence;
6. bounded R4 runner;
7. sanitized STOP enrichment if failure;
8. sanitized Issue #63 evidence + artifact upload.

No current TOOL1 authorization permits step 5 or step 6 to occur.

## Prior Evidence Carried Forward

R4-PRE1 already proved, without generation, on main `170e82d19315e80cc7393922d7daa1b1c7f2093b`:

- full no-paid runtime preflight run `34302711166` = SUCCESS;
- Gemini metadata-only probe run `34302730786` = SUCCESS / HTTP 200 / `ACCESS_PROBE_PASS`;
- current GitHub Actions Gemini credential authenticated;
- `gemini-3.1-flash-image` visible;
- provider generation calls = 0;
- spend added = USD 0.00;
- no execution fence.

Owner-supplied Google AI Studio evidence also showed `Orbis-Video-Production` at Tier 1 / Prepay with Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K.

## Exit / Review Gate

TOOL1 may reach `PASS / READY FOR OWNER MERGE DECISION` only when:

- scope diff contains only authorized R4 tooling/tests/control docs;
- R4 identity/call/budget/fence guards are exact;
- static tests prove no-paid preflight has no generation invocation;
- inherited R3 runner blob guard is exact;
- R4 STOP evidence remains durable and sanitized;
- backend/frontend/migration CI passes at exact PR head;
- independent review passes;
- provider generation calls during TOOL1 = 0;
- spend during TOOL1 = USD 0.00.

Owner merge approval does NOT authorize R4 preflight dispatch, paid authorization, fence consumption, or paid execution. Every later gate remains separate.
