# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.
>
> Canonical base `main` is at `46cd9e85d68b58e9d276673e6834c81167218de9` following merge of R5-PRE1 tooling (PR #89) and successful run `34351326791`. This specification governs `P4-WP020-LIVE-R5-PRE1-CLOSE`.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-PRE1-CLOSE
ACTIVE_STATUS = AUTHORIZED / CONTROL-DOC-ONLY
CANONICAL_BASE_MAIN = 46cd9e85d68b58e9d276673e6834c81167218de9
ACTIVE_BRANCH = ai/p4-wp020-live-r5-pre1-close
CLOSURE_AUTH_COMMENT = 5601980565
NEXT_GATE = CHATGPT_REVIEW_AND_OWNER_MERGE_DECISION

PRE1_COMPLETED_GATE = P4-WP020-LIVE-R5-PRE1
PRE1_STATUS = PASS / COMPLETED / NO-PAID
PRE1_RUN = 34351326791
PRE1_EXECUTION_MAIN = 46cd9e85d68b58e9d276673e6834c81167218de9
READINESS_IDENTITY = WP020-LIVE-R5-PRE1

POSTGRES_RUNTIME_BOOTSTRAP = PASS
EPHEMERAL_OBJECT_STORAGE = PASS
CREDENTIALS_CONFIG_PRESENT = TRUE
PROVIDER_ROUTING_CONFIG = PASS
PRICING_BUDGET_READINESS = PASS

PROVIDER_GENERATION_CALLS = 0
PAID_PROVIDER_CALLS = 0
VIDU_CREDITS_CONSUMED = 0
PAID_FENCE_WRITTEN = FALSE
PAID_LIVE_DISPATCH = FALSE

R5_PAID_IDENTITY = NONE / NOT AUTHORIZED
R5_PAID_EXECUTION = NOT AUTHORIZED

P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
R4_STATUS = STOPPED / CONSUMED / NEVER RERUN

AFTER_CLOSURE_MERGE:
ACTIVE_WORK_PACKAGE = NONE
NEXT_GATE = OWNER DECISION REQUIRED
```

---

## P4-WP020-LIVE-R5-PRE1 Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-PRE1 — NO-PAID Readiness / Preflight` in Issue #63 (comment `5600206595`) under execution contract comment `5600227540`. Tooling PR #89 merged to canonical `main` at `46cd9e85d68b58e9d276673e6834c81167218de9`.

The dedicated readiness workflow was executed on canonical `main`:
- Run ID: `34351326791`;
- Workflow: `WP020 LIVE R5 Readiness & Preflight (NO-PAID)`;
- Execution Main SHA: `46cd9e85d68b58e9d276673e6834c81167218de9`;
- Conclusion: `SUCCESS` / `PASS` / `NO-PAID`.

Accepted preflight evidence:
- PostgreSQL 16 migrations + clean starting database state (0 usage ledger rows, 0 generation jobs) verified;
- Ephemeral MinIO object storage write/read/delete verified;
- Required credentials and adapter configurations present for OpenAI, Gemini, Vidu, ElevenLabs;
- Adapter constructors and config validation verified without making any provider generation calls;
- Local pricing estimator verified for all 6 sequential provider targets within USD 1.00 reservation ceiling;
- Owner-provided balance of 2,000 Vidu credits documented as readiness evidence only (not converted to USD);
- Verification metrics:
  ```text
  provider_generation_calls = 0
  paid_provider_calls = 0
  vidu_credits_consumed = 0
  paid_fence_written = false
  paid_live_dispatch = false
  ```

Closure authorization: Issue #63 comment `5601980565`.

---

## BILL1 Evidence Accepted

`P4-WP020-LIVE-R4-BILL1 — Vidu Provider-Side Billing Evidence Disposition (EVIDENCE-ONLY / NO-PAID)` is complete at the evidence-disposition level.

Accepted evidence:
- Owner-provided Vidu Usage view with `UTC0` date range shown as `2026-08-09 - 2026-09-09`;
- `All Keys` selected;
- Type, Model Version, Resolution, Template and Generate Mode filters set to `ALL`;
- the Usage History area shows `No data to export` / no usage rows for the displayed range;
- the displayed range includes the R4 interval around `2026-09-09T05:45:42Z` through `2026-09-09T05:47:19Z`, so no provider-recorded usage entry is shown for that interval.

Controlled disposition:

```text
BILL1 = PASS / EVIDENCE ACCEPTED
FAILED R4 VIDU TASK EXTERNAL BILLING = NOT CHARGED
VIDU INTERNAL JOB ESTIMATE = USD 0.15 / ESTIMATED ONLY
R4 LAST KNOWN COMMITTED/ACTUAL ORBIS UAT COST = USD 0.0738
BILL1 PROVIDER CALLS = 0
BILL1 SPEND ADDED = USD 0.00
```

No credits-to-USD conversion is authorized or inferred.

The Owner subsequently provided Vidu Credit Balance evidence showing `2,000 credits` after top-up. Treat this only as readiness evidence for a possible future gate. It does not alter historical R4 billing evidence and does not authorize any provider request.

---

## Immutable R4 Execution Truth

```text
Execution ID: LIVE-20260909-DE17-R4
Workflow run: 34316188814
Execution main: b1538f655bf526384845c1e8c536ad6fddc66ca7
Conclusion: FAILURE / STOP
Fence comment: 5596464603
STOP comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative paid calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Provider sequence reached:
- OpenAI STORY: SUCCESS;
- Gemini IMAGE: SUCCESS;
- Vidu VIDEO: terminal `FAILED`;
- ElevenLabs TTS / Music / Ambience: NOT CALLED.

`LIVE-20260909-DE17-R4` is consumed and MUST NEVER be rerun.

---

## Post-R5-PRE1-CLOSE Rule

Once this closure record is on canonical `main`:
- `ACTIVE_WORK_PACKAGE = NONE`;
- `NEXT_GATE = OWNER DECISION REQUIRED`.

A future bounded Vidu credit-generation probe is NOT authorized by R5-PRE1-CLOSE and must receive separate explicit Owner authorization.

Do not create an R5 paid execution identity, call any external provider, write a paid authorization marker, create or consume an execution fence, dispatch a paid/live workflow, adjust billing, convert credits to USD, release, tag, or deploy without separate explicit Owner authorization.
