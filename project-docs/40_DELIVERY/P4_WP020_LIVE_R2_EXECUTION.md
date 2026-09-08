# P4-WP020-LIVE R2 — Paid One-Shot Execution Gate

**Status:** PREPARED / NOT AUTHORIZED / NOT EXECUTED  
**Execution ID:** `LIVE-20260909-BB75-R2`  
**Prepared from canonical main:** `bb75c8087428cb14a57a3557b9013f5472f976bf`  
**R2 no-paid preflight evidence:** GitHub Actions run `34286302660` — PASS  

## 1. Purpose

Prepare a fresh paid LIVE proof after R1 `LIVE-20260908-B023-R1` stopped fail-closed at the first OpenAI request with HTTP 429 and after the later R2 no-paid preflight passed on canonical main.

This preparation does not authorize or execute any provider request.

## 2. R1 remains immutable

R1 is permanently consumed historical evidence. Its Issue #63 execution marker and STOP evidence must not be removed, reset, or reused.

The reviewed R1 runner source is retained byte-for-byte as:

- `.github/scripts/wp020_live_uat_r1_snapshot.py`

Expected Git blob SHA:

`7a34b21b8e72c4d8ef49efc56a23feef4476d82c`

R2 uses `.github/scripts/wp020_live_uat_r2.py` only as a fenced launcher. The launcher verifies the immutable snapshot Git blob, requires the new R2 execution ID, requires `AUTHORIZED_MAIN_SHA == GITHUB_SHA`, and changes only the historical R1 identity guards in memory before executing the reviewed runner logic.

## 3. R2 paid-provider bounds

The PR #62 contract remains unchanged:

- OpenAI Creative: maximum 1 story request, `gpt-4o`, automatic retries disabled;
- Gemini Image: maximum 1 image request, `gemini-3.1-flash-image`, 1K;
- Vidu Video: maximum 1 submit, `viduq2`, 4 seconds, 720p;
- ElevenLabs Audio: maximum 3 calls — bounded Thai TTS, BGM <= 10 seconds, ambience <= 3 seconds;
- total maximum chargeable provider calls: 6;
- sequential execution only;
- dedicated UAT project hard budget: USD 1.00;
- STOP on UNKNOWN pricing/cost, credential/config failure, `RECONCILIATION_REQUIRED`, duplicate/idempotency conflict, ambiguous provider outcome, durable materialization failure, ledger truth failure, secret leak, unexpected call count, or any new S0/S1;
- no automatic paid retry after a failure or uncertain outcome;
- no release tag, production deployment, batch expansion, or regeneration-for-quality.

## 4. Workflow safety

Workflow:

- `.github/workflows/wp020-live-execution-r2.yml`

Safety properties:

1. `workflow_dispatch` only — no `push` and no `pull_request` trigger;
2. minimal permissions: `contents: read`, `issues: write`;
3. serialized by one concurrency group with `cancel-in-progress: false`;
4. runtime guard requires canonical `main`;
5. runtime main must contain the R2 preflight base `bb75c8087428cb14a57a3557b9013f5472f976bf`;
6. exact fresh Owner paid authorization must already exist in Issue #63 for the current runtime main SHA;
7. the R2 `EXECUTION_STARTED` fence must be absent;
8. PostgreSQL 16, migrations, MinIO, credential presence, provider routing, retry policy, pricing and USD 1.00 budget checks are rerun through the zero-provider R2 preflight before the fence is consumed;
9. authorization and fence absence are rechecked immediately before writing the fence;
10. only after the exact fence is written may the R2 launcher run;
11. evidence is posted/uploaded even when the runner stops.

## 5. Exact Owner authorization marker

After this tooling is reviewed and Owner-approved for merge, and after it is merged to `main`, fresh-fetch the then-current exact canonical main SHA.

Paid execution remains STOPPED until the Owner explicitly authorizes the R2 paid/live run. That authorization is then recorded in Issue #63 as exactly one line:

`FRESH_OWNER_AUTHORIZED_R2: LIVE-20260909-BB75-R2 @ <exact-current-main-sha>`

The workflow refuses to proceed unless that exact marker matches its own `GITHUB_SHA`.

This authorization marker does not consume the one-shot paid fence.

## 6. Fence consumption

Immediately before the first chargeable provider request, and only after all no-paid runtime guards PASS, the workflow writes:

`EXECUTION_STARTED: LIVE-20260909-BB75-R2`

Once this marker exists, the R2 authorization is consumed permanently. Any failure, uncertain outcome, cancellation after fence consumption, or STOP condition means no rerun and no paid retry under R2.

## 7. Current gate

Current state is preparation only:

- R2 tooling branch may be reviewed and tested;
- standard CI may run because it contains no paid provider dispatch;
- merging the PR cannot automatically start R2 because the paid workflow is manual-only;
- no Owner paid authorization marker has been written for R2;
- no R2 `EXECUTION_STARTED` marker has been written;
- paid provider calls in this preparation: 0;
- provider spend from this preparation: USD 0.00.

Next decision after exact-head review and green CI is an **Owner merge decision only**. Paid execution requires a separate fresh Owner authorization after merge.
