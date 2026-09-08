# P4-WP020-LIVE R2 — No-Paid Preflight Gate

**Status:** PREPARED / NO-PAID / OWNER MERGE GATE REQUIRED  
**Prepared from canonical main:** `6d4cfad3c87d17eddc2af459828610720a477875`  
**Purpose:** re-establish LIVE readiness after the consumed R1 execution stopped fail-closed at OpenAI HTTP 429.

## 1. R1 is immutable historical evidence

R1 execution ID `LIVE-20260908-B023-R1` is permanently consumed.

Issue #63 contains:
- `EXECUTION_STARTED: LIVE-20260908-B023-R1`;
- `LIVE_EXECUTION_STOPPED: LIVE-20260908-B023-R1`;
- phase `LIVE-01-OPENAI-STORY`;
- conservative chargeable-call accounting `1/6`;
- recorded UAT cost `USD 0.0000`;
- stop reason `OpenAI rate limit exceeded (HTTP 429)`.

PR #69 is closed without merge. Its branch and evidence are retained for audit and must not be rerun.

## 2. Owner-side billing change

The Owner subsequently showed OpenAI API Billing with:
- Pay as you go enabled;
- API credit balance `USD 5.00`;
- auto-reload OFF.

This is external account readiness evidence only. The repository preflight deliberately does not query OpenAI billing or make a provider request, so it cannot independently prove the remaining provider-side credit balance.

## 3. This R2 preflight is strictly zero-paid

Files:
- `.github/scripts/wp020_live_r2_preflight.py`
- `.github/workflows/wp020-live-r2-preflight.yml`

The workflow:
- is `workflow_dispatch` only;
- has `contents: read` permission only;
- can be dispatched only on canonical `main` by an explicit runtime guard;
- requires the post-manual-corrective main baseline `6d4cfad3c87d17eddc2af459828610720a477875` to be an ancestor;
- uses ephemeral PostgreSQL 16 and MinIO;
- applies `alembic upgrade head`;
- checks presence only for the five required GitHub Actions credential/config entries;
- checks production provider/model routing without generation;
- enforces `OPENAI_MAX_RETRIES=0` for the future bounded LIVE proof;
- validates runtime pricing estimates for OpenAI/Gemini/Vidu/ElevenLabs;
- creates an isolated local UAT project with `USD 1.00` hard budget and zero ledger/job state;
- performs object-storage write/read/delete only against ephemeral MinIO;
- contains no provider-generation invocation;
- has no issue-write permission and cannot create an `EXECUTION_STARTED` marker.

Expected paid provider calls: **0**.  
Expected provider spend: **USD 0.00**.

## 4. PASS gate

R2 no-paid preflight PASS requires:
1. canonical main ancestry guard PASS;
2. PostgreSQL 16 startup PASS;
3. `alembic upgrade head` PASS;
4. MinIO health and object read/write/delete PASS;
5. all five credential/config names present, with no values logged;
6. OpenAI/Gemini/Vidu/ElevenLabs production adapter configuration PASS;
7. OpenAI retry count exactly zero;
8. pricing status known and within the existing LIVE contract reservations;
9. isolated UAT project hard budget exactly USD 1.00 / threshold 80%;
10. zero UsageLedger and zero GenerationJob starting state;
11. explicit evidence that no provider-generation entrypoint was invoked;
12. no new S0/S1 finding.

Any failure => STOP at no-paid stage. Do not proceed to LIVE R2 execution.

## 5. What this does NOT authorize

This preflight does **not** authorize:
- any OpenAI/Gemini/Vidu/ElevenLabs provider request;
- any new LIVE execution ID;
- any `EXECUTION_STARTED` marker;
- reuse of R1 authorization or R1 fence;
- paid retry of the R1 OpenAI request;
- production deployment, release tag, or Core V1 release declaration.

## 6. Gate after preflight PASS

After this tooling is reviewed, Owner-approved for merge, merged to `main`, and manually dispatched with PASS evidence:

1. fresh-fetch the then-current canonical main SHA;
2. define a **new** R2 execution ID bound to that main truth;
3. prepare the paid execution workflow with `workflow_dispatch` only — never `push`;
4. require an exact new Issue #63 execution fence marker for R2;
5. preserve the existing PR #62 provider/cost/STOP contract unless the Owner explicitly changes it;
6. obtain **fresh Owner paid/live authorization** before the first chargeable provider call.

No paid execution may occur merely because this preflight passes.
