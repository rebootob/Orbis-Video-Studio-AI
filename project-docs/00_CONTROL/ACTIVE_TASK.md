# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.
>
> This specification records canonical state effective for P4-WP020-LIVE-R5-VIDU1-C1 on canonical `main` `5a818b9dbf642b1e456dba51c9a80745d966919e`.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
ACTIVE_STATUS = WAITING FOR EXPLICIT OWNER NEXT GATE
VIDU1_C1_BASE_MAIN = 5a818b9dbf642b1e456dba51c9a80745d966919e
NEXT_GATE = OWNER DECISION REQUIRED

LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-C1
LAST_COMPLETED_STATUS = PASS / MERGED / COMPLETE
VIDU1_C1_AUTH_COMMENT = 5611111664
VIDU1_C1_MERGE_PR = #94

PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-COR1
PREV_COMPLETED_STATUS = PASS / MERGED / COMPLETE
VIDU1_COR1_AUTH_COMMENT = 5604486823
VIDU1_COR1_MERGE_PR = #93

PREV2_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-PREP
PREV2_COMPLETED_STATUS = PASS / MERGED / COMPLETE
VIDU1_PREP_AUTH_COMMENT = 5602834080
VIDU1_PREP_MERGE_PR = #92

VIDU1_READINESS_IDENTITY = WP020-LIVE-R5-VIDU1-PREP
VIDU1_PAID_IDENTITY = NONE / NOT AUTHORIZED
VIDU1_PAID_EXECUTION = NOT AUTHORIZED

VIDU1_PREP_PROVIDER_GENERATION_CALLS = 0
VIDU1_PREP_PAID_PROVIDER_CALLS = 0
VIDU1_PREP_VIDU_GENERATION_POSTS = 0
VIDU1_PREP_VIDU_CREDITS_CONSUMED = 0
VIDU1_PREP_PAID_FENCE_WRITTEN = FALSE
VIDU1_PREP_PAID_LIVE_DISPATCH = FALSE

PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-PRE1-CLOSE-R1
PREV_COMPLETED_STATUS = PASS / MERGED / COMPLETE
PREV_AUTH_COMMENT = 5602341968
PREV_MERGE_PR = #91

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
```

---

## P4-WP020-LIVE-R5-VIDU1-C1 Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-VIDU1-C1 — NO-PAID HTTP Failure Evidence & Request Contract Diagnostic Corrective` in Issue #63 (comment `5611111664`) on canonical main `5a818b9dbf642b1e456dba51c9a80745d966919e`.

Immutable Consumed Live Execution Truth (Run 34423580310):
- Execution ID: `LIVE-20260909-VIDU1-R5` on canonical `main` (`42d789efdb49725b1dd45b312ce39cb71ac02d1e`)
- Fence comment: `5611052822`
- Terminal STOP comment: `5611054713`
- Status: `STOPPED / CONSUMED / NEVER RERUN`
- Generation POSTs = 1
- Provider error code: `HTTP_ERROR`
- Provider job ID: `null`
- Poll attempts = 0
- OpenAI calls = 0, Gemini calls = 0, ElevenLabs calls = 0
- Historical HTTP status: `UNKNOWN` (not preserved in sanitized evidence of run 34423580310)
- Vidu credits consumed: `UNKNOWN / NOT CONFIRMED` (zero credits are NOT claimed)
- `LIVE-20260909-VIDU1-R5` is permanently consumed and MUST NOT be rerun.

Delivered Diagnostic Corrective:
- Added safe HTTP status evidence (`provider_http_status`: typed integer 100–599) and typed `failure_classification` (`HTTP_CLIENT_ERROR`, `HTTP_RATE_LIMITED`, `HTTP_SERVER_ERROR`) to `.github/scripts/wp020_live_r5_vidu1.py`;
- Updated workflow canonical base SHA to `5a818b9dbf642b1e456dba51c9a80745d966919e`;
- Verified outbound Vidu request contract (POST `/text2video`, headers `Authorization: Token <API_KEY>`, `Content-Type: application/json`, payload `model=viduq2`, `duration=4`, `aspect_ratio=16:9`, `resolution=720P`) in `backend/tests/test_wp020_live_r5_vidu1_contract.py`;
- Added automated mock tests for HTTP 400, 401, 403, 429, and 500 failure responses;
- Verified evidence sanitization excludes raw response bodies, headers, and secrets;
- Verified `MAX_GENERATION_POSTS = 1` and zero calls to other providers;
- C1 gate itself caused: `provider_generation_calls = 0`, `paid_provider_calls = 0`, `vidu_generation_posts = 0`, `vidu_credits_consumed = 0 by C1 itself`, `paid_fence_written = false`, `paid_live_dispatch = false`.

Post-Merge Rule:
- Consumed run `34423580310` / execution identity `LIVE-20260909-VIDU1-R5` MUST NEVER BE RERUN.
- Any future probe requires a fresh dedicated execution identity, fresh explicit Owner authorization, and fresh exact marker bound to the post-merge canonical main SHA.

---

## P4-WP020-LIVE-R5-VIDU1-COR1 Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-VIDU1-COR1 — NO-PAID Workflow Guard Compatibility Corrective` in Issue #63 (comment `5604486823`) on canonical main `42d789efdb49725b1dd45b312ce39cb71ac02d1e`.

Failed Live Run Evidence:
- Run ID: `34368643536` on canonical `main` (`42d789efdb49725b1dd45b312ce39cb71ac02d1e`)
- Failed closed at workflow step `Check Owner authorization & fence if live` with error: `specify only one of --comments or --json`
- Failed closed before fence consumption (`EXECUTION_STARTED: LIVE-20260909-VIDU1-R5` was not posted)
- Provider generation calls: 0, paid provider calls: 0, Vidu generation POSTs: 0, Vidu credits consumed: 0

Delivered Corrective Changes:
- `.github/workflows/wp020-live-r5-vidu1.yml`: replaced incompatible `gh issue view` invocation with `gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments" --jq '.[].body'` and fail-closed check on empty comments;
- `backend/tests/test_wp020_live_r5_vidu1_contract.py`: added automated tests A through H;
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_COR1.md`: delivery specification.

Fresh Authorization Requirement:
- **COR1 NO-PAID Owner authorization:** Issue #63 comment `5604486823` — authorizes only this NO-PAID corrective work package.
- **Prior paid VIDU1 authorization marker:** Issue #63 comment `5603798466` — contains `FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ 42d789efdb49725b1dd45b312ce39cb71ac02d1e`, bound to SHA `42d789efdb49725b1dd45b312ce39cb71ac02d1e`.
- The prior paid marker at comment `5603798466` was bound to old canonical main SHA `42d789efdb49725b1dd45b312ce39cb71ac02d1e` and MUST NOT be reused after PR #93 merges to `main`.
- Any future paid probe requires a fresh explicit Owner authorization with a fresh exact marker bound to the new post-merge canonical main SHA.

---

## P4-WP020-LIVE-R5-VIDU1-PREP Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-VIDU1-PREP — NO-PAID Dedicated Vidu 1-Call Probe Tooling` in Issue #63 (comment `5602834080`) on canonical main `5107e3e9ef7702c8403fe74146062ab68e8e50b9`.

Tooling Delivered:
- `.github/scripts/wp020_live_r5_vidu1.py`: dedicated probe runner with independent runner-side live permit guard (`validate_live_execution_permit`), hard 1-POST cap, exact `720P` resolution lock, safe credit semantics (`provider_credits_reported` preserved, `vidu_credits_consumed = null / UNKNOWN`), fail-closed handling of ambiguous transport outcomes, GET-only polling, and sanitized evidence export;
- `.github/workflows/wp020-live-r5-vidu1.yml`: dedicated manual `workflow_dispatch` workflow exporting confirmed live permit to runner upon fence consumption;
- `backend/tests/test_wp020_live_r5_vidu1_contract.py`: contract test suite validating safety guards, behavioral tests A through E, single POST cap, and evidence sanitization;
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_PREP.md`: delivery specification.

PREP Safety Invariants:
```text
provider_generation_calls = 0
paid_provider_calls = 0
vidu_generation_posts = 0
vidu_credits_consumed = 0
paid_fence_written = false
paid_live_dispatch = false
```

Post-merge status leaves `ACTIVE_WORK_PACKAGE = NONE` and `NEXT_GATE = OWNER DECISION REQUIRED`. A future paid probe (`P4-WP020-LIVE-R5-VIDU1`) requires separate explicit Owner authorization.

---

## P4-WP020-LIVE-R5-PRE1 Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-PRE1 — NO-PAID Readiness / Preflight` in Issue #63 (comment `5600206595`) under execution contract comment `5600227540`. Tooling PR #89 merged to canonical `main` at `46cd9e85d68b58e9d276673e6834c81167218de9`.

The dedicated readiness workflow was executed on canonical `main`:
- Run ID: `34351326791`;
- Workflow: `WP020 LIVE R5 No-Paid Preflight`;
- Execution Main SHA: `46cd9e85d68b58e9d276673e6834c81167218de9`;
- Conclusion: `SUCCESS` / `PASS` / `NO-PAID`.

Accepted preflight evidence:
- PostgreSQL 16 migrations + clean starting database state (0 usage ledger rows, 0 generation jobs) verified;
- Ephemeral MinIO object storage write/read/delete verified;
- Required credentials and adapter configurations present for OpenAI, Gemini, Vidu, ElevenLabs;
- Adapter constructors and config validation verified without making any provider generation calls;
- Local pricing estimator verified for all 6 sequential chargeable request targets across OpenAI, Gemini, Vidu, and ElevenLabs within USD 1.00 reservation ceiling;
- Owner-provided balance of 2,000 Vidu credits documented as readiness evidence only (not converted to USD);
- Verification metrics:
  ```text
  provider_generation_calls = 0
  paid_provider_calls = 0
  vidu_credits_consumed = 0
  paid_fence_written = false
  paid_live_dispatch = false
  ```

Closure authorization: Issue #63 comment `5601980565` (merged to main in PR #90 commit `817539b619c4b28f22273ff01df733c612a2a386`).

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

## Post-R5-VIDU1-PREP Rule

With P4-WP020-LIVE-R5-VIDU1-PREP merged to canonical `main`:
- `ACTIVE_WORK_PACKAGE = NONE`;
- `NEXT_GATE = OWNER DECISION REQUIRED`.

A future bounded Vidu credit-generation probe (`P4-WP020-LIVE-R5-VIDU1`) is NOT authorized by PREP tooling and must receive separate explicit Owner authorization.

Do not create an R5 paid execution identity, call any external provider, write a paid authorization marker, create or consume an execution fence, dispatch a paid/live workflow, adjust billing, convert credits to USD, release, tag, or deploy without separate explicit Owner authorization.
