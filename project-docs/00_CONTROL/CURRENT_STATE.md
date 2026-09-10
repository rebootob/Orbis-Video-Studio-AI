# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.
>
> This specification records canonical state effective for P4-WP020-LIVE-R5-VIDU1-C1 on canonical `main` `5a818b9dbf642b1e456dba51c9a80745d966919e`.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
VIDU1_C1_BASE_MAIN: 5a818b9dbf642b1e456dba51c9a80745d966919e

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020-LIVE-R4-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PRE1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-TOOL1-CLOSE-R1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-PF1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R4-PF1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-AUTH1: PASS / AUTHORIZED
P4-WP020-LIVE-R4-RUN1: STOPPED / CONSUMED / NEVER RERUN
P4-WP020-LIVE-R4-C1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-C1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-C1-CLOSE-R1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R4-BILL1: PASS / EVIDENCE ACCEPTED / NOT CHARGED
P4-WP020-LIVE-R4-BILL1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R5-PRE1: PASS / COMPLETED / NO-PAID
P4-WP020-LIVE-R5-PRE1-CLOSE: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R5-PRE1-CLOSE-R1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R5-VIDU1-PREP: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R5-VIDU1-COR1: PASS / MERGED / COMPLETE
P4-WP020-LIVE-R5-VIDU1-C1: ACTIVE / IN REVIEW / NOT MERGED (PR #94)

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R5-VIDU1-C1
CURRENT_GATE: P4-WP020-LIVE-R5-VIDU1-C1
NEXT_GATE: CHATGPT_REVIEW_AND_OWNER_MERGE_DECISION
LAST_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-COR1

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

VIDU1_READINESS_IDENTITY: WP020-LIVE-R5-VIDU1-PREP
VIDU1_PAID_IDENTITY: NONE / NOT AUTHORIZED
VIDU1_PAID_EXECUTION: NOT AUTHORIZED

VIDU1_CONSUMED_EXECUTION_ID: LIVE-20260909-VIDU1-R5
VIDU1_CONSUMED_RUN: 34423580310
VIDU1_CONSUMED_STATUS: STOPPED / CONSUMED / NEVER RERUN
VIDU1_CONSUMED_GENERATION_POSTS: 1
VIDU1_CONSUMED_PROVIDER_ERROR_CODE: HTTP_ERROR
VIDU1_CONSUMED_HISTORICAL_HTTP_STATUS: UNKNOWN
VIDU1_CONSUMED_CREDITS: UNKNOWN / NOT CONFIRMED

VIDU1_C1_PROVIDER_GENERATION_CALLS: 0
VIDU1_C1_PAID_PROVIDER_CALLS: 0
VIDU1_C1_VIDU_GENERATION_POSTS: 0
VIDU1_C1_VIDU_CREDITS_CONSUMED: 0
VIDU1_C1_PAID_FENCE_WRITTEN: false
VIDU1_C1_PAID_LIVE_DISPATCH: false

R5_READINESS_IDENTITY: WP020-LIVE-R5-PRE1
R5_PRE1_RUN: 34351326791
R5_PRE1_EXECUTION_MAIN: 46cd9e85d68b58e9d276673e6834c81167218de9
R5_PAID_IDENTITY: NONE / NOT AUTHORIZED
R5_PAID_EXECUTION: NOT AUTHORIZED

R5_PRE1_PROVIDER_GENERATION_CALLS: 0
R5_PRE1_PAID_PROVIDER_CALLS: 0
R5_PRE1_VIDU_CREDITS_CONSUMED: 0
R5_PRE1_PAID_FENCE_WRITTEN: false
R5_PRE1_PAID_LIVE_DISPATCH: false

R5_PRE1_POSTGRES_BOOTSTRAP: PASS
R5_PRE1_OBJECT_STORAGE: PASS
R5_PRE1_CREDENTIALS_PRESENT: true
R5_PRE1_PROVIDER_ROUTING: PASS
R5_PRE1_PRICING_READINESS: PASS

R4_EXECUTION_ID: LIVE-20260909-DE17-R4
R4_EXECUTION_RUN: 34316188814
R4_EXECUTION_MAIN: b1538f655bf526384845c1e8c536ad6fddc66ca7
R4_EXECUTION_FENCE: CONSUMED / NEVER RERUN
R4_PAID_EXECUTION: STOPPED
R4_STOP_PHASE: LIVE-03-VIDU-VIDEO
R4_CONSERVATIVE_PAID_CALLS: 3 / 6
R4_LAST_KNOWN_COMMITTED_ACTUAL_UAT_COST: USD 0.0738
R4_VIDU_JOB_ESTIMATE: USD 0.15 / ESTIMATED
R4_VIDU_EXTERNAL_BILLING: NOT CHARGED / PROVIDER-SIDE EVIDENCE ACCEPTED

VIDU_BALANCE_READINESS_EVIDENCE: 2000 CREDITS / OWNER-PROVIDED SCREENSHOT / NOT USD BILLING EVIDENCE
```

---

## P4-WP020-LIVE-R5-VIDU1-C1 Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-VIDU1-C1 — NO-PAID HTTP Failure Evidence & Request Contract Diagnostic Corrective` in Issue #63 (comment `5611111664`) on canonical main `5a818b9dbf642b1e456dba51c9a80745d966919e`.

Immutable Consumed Live Execution Truth (Run 34423580310):
- Execution ID: `LIVE-20260909-VIDU1-R5` on canonical `main` (`5a818b9dbf642b1e456dba51c9a80745d966919e`)
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
- Verified outbound Vidu request contract (POST `/text2video`, headers `Authorization: Token <API_KEY>`, `Content-Type: application/json`, payload `model=viduq2`, `duration=4`, `aspect_ratio=16:9`, `resolution=720p` (with adapter normalization from `720P`)) in `backend/tests/test_wp020_live_r5_vidu1_contract.py`;
- Added automated mock tests for HTTP 400, 401, 403, 429, and 500 failure responses;
- Verified evidence sanitization excludes raw response bodies, headers, and secrets;
- Verified `MAX_GENERATION_POSTS = 1` and zero calls to other providers;
- C1 gate itself caused: `provider_generation_calls = 0`, `paid_provider_calls = 0`, `vidu_generation_posts = 0`, `vidu_credits_consumed = 0 by C1 itself`, `paid_fence_written = false`, `paid_live_dispatch = false`.

Post-Merge Rule:
- The consumed run `34423580310` / execution identity `LIVE-20260909-VIDU1-R5` MUST NEVER BE RERUN.
- Any future probe requires a fresh dedicated execution identity, fresh explicit Owner authorization, and fresh exact marker bound to the post-merge canonical main SHA.

---

## P4-WP020-LIVE-R5-VIDU1-COR1 Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-VIDU1-COR1 — NO-PAID Workflow Guard Compatibility Corrective` in Issue #63 (comment `5604486823`) on canonical main `42d789efdb49725b1dd45b312ce39cb71ac02d1e`.

Failed Live Run Evidence:
- Run ID: `34368643536` on canonical `main` (`42d789efdb49725b1dd45b312ce39cb71ac02d1e`)
- Failed closed at workflow step `Check Owner authorization & fence if live` with error: `specify only one of --comments or --json`
- Failed closed before fence consumption (`EXECUTION_STARTED: LIVE-20260909-VIDU1-R5` was not posted)
- Provider generation calls: 0, paid provider calls: 0, Vidu generation POSTs: 0, Vidu credits consumed: 0

Delivered Changes:
- `.github/workflows/wp020-live-r5-vidu1.yml`: replaced incompatible `gh issue view` flags with `gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments" --jq '.[].body'` and fail-closed non-empty validation;
- `backend/tests/test_wp020_live_r5_vidu1_contract.py`: added automated tests A through H validating comment pagination and safety guards;
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_COR1.md`: delivery specification.

Post-Merge Fresh Authorization Rule:
- **COR1 NO-PAID Owner authorization:** Issue #63 comment `5604486823` — authorizes only this NO-PAID corrective work package.
- **Prior paid VIDU1 authorization marker:** Issue #63 comment `5603798466` — contains `FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ 42d789efdb49725b1dd45b312ce39cb71ac02d1e`, bound to SHA `42d789efdb49725b1dd45b312ce39cb71ac02d1e`.
- The prior paid marker at comment `5603798466` was bound to old canonical main SHA `42d789efdb49725b1dd45b312ce39cb71ac02d1e` and MUST NOT be reused after PR #93 merges to `main`.
- Any future paid probe requires a fresh explicit Owner authorization with a fresh exact marker bound to the new post-merge canonical main SHA.

---

## P4-WP020-LIVE-R5-VIDU1-PREP Accepted Truth

Owner authorized `P4-WP020-LIVE-R5-VIDU1-PREP — NO-PAID Dedicated Vidu 1-Call Probe Tooling` in Issue #63 (comment `5602834080`) on canonical main `5107e3e9ef7702c8403fe74146062ab68e8e50b9`.

Delivered tooling:
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

The dedicated readiness workflow run was executed on canonical `main`:
- Run ID: `34351326791`
- Workflow: `WP020 LIVE R5 No-Paid Preflight`
- Execution Main SHA: `46cd9e85d68b58e9d276673e6834c81167218de9`
- Conclusion: `SUCCESS` / `PASS`

Accepted preflight evidence:
- Required credentials and adapter configurations present for OpenAI, Gemini, Vidu, ElevenLabs;
- Adapter constructors and config validation succeeded without making any provider generation calls;
- Local pricing estimator verified for all 6 sequential chargeable request targets across OpenAI, Gemini, Vidu, and ElevenLabs within USD 1.00 reservation ceiling;
- Ephemeral MinIO object storage write/read/delete verified;
- Ephemeral PostgreSQL 16 migrations + clean starting DB state (0 jobs, 0 ledger rows) verified;
- Vidu credit balance of 2,000 credits recorded as readiness evidence only (not converted to USD);
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

## BILL1 Provider-Side Billing Disposition

Owner authorized `P4-WP020-LIVE-R4-BILL1 — Vidu Provider-Side Billing Evidence Disposition (EVIDENCE-ONLY / NO-PAID)` on canonical main `da381bbd2cc407393e7326e9824bef68ea356e6b`.

Issue #63 audit trail:
- BILL1 authorization comment: `5598882289`;
- BILL1 accepted disposition comment: `5598962073`.

Accepted provider-side evidence was the Owner-provided Vidu Usage view with `UTC0` date range shown as `2026-08-09 - 2026-09-09`, `All Keys` selected, and Type / Model Version / Resolution / Template / Generate Mode filters set to `ALL`. The Usage History area shows `No data to export` / no usage rows for the displayed range. That displayed range includes the R4 interval around `2026-09-09T05:45:42Z` through `2026-09-09T05:47:19Z`, so no provider-recorded usage entry is shown for the R4 interval.

Controlled disposition:

```text
BILL1 = PASS / EVIDENCE ACCEPTED
R4 failed Vidu external billing = NOT CHARGED
Vidu internal job estimate = USD 0.15 / ESTIMATED ONLY
R4 last known committed/actual Orbis UAT cost at STOP = USD 0.0738
BILL1 provider calls = 0
BILL1 spend added = USD 0.00
```

No credits-to-USD conversion was inferred. The accepted disposition closes only the failed R4 Vidu task billing question; it does not retroactively change immutable R4 execution history.

The Owner later provided Vidu Credit Balance evidence showing `2,000 credits` after top-up. This is readiness evidence only. It is not proof of historical R4 billing and is not converted to USD in control records.

---

## Immutable R4 RUN1 Evidence

```text
Execution ID: LIVE-20260909-DE17-R4
Run: 34316188814
Workflow: WP020 LIVE R4 Paid One-Shot Execution
Execution Head SHA: b1538f655bf526384845c1e8c536ad6fddc66ca7
Conclusion: FAILURE / STOP
Execution fence: CONSUMED / NEVER RERUN
Fence comment: 5596464603
STOP comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative chargeable calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Reached provider sequence:
1. OpenAI Story — SUCCESS;
2. Gemini Image — SUCCESS;
3. Vidu Video — terminal `FAILED`;
4. ElevenLabs TTS — NOT CALLED;
5. ElevenLabs Music — NOT CALLED;
6. ElevenLabs Ambience — NOT CALLED.

R4 STOP is final for this identity. `LIVE-20260909-DE17-R4` MUST NEVER BE RERUN.

---

## C1 Closure Truth

```text
C1 PR #85 = PASS / MERGED / COMPLETE
C1 exact reviewed HEAD = c6f02fe56d4248011b0ef0cb96910d6997195e60
C1 merge commit = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
C1-CLOSE PR #86 = PASS / MERGED / COMPLETE
C1-CLOSE merge commit = 37bc4584eaa14bcf1d01243364548b2a3c39bcbb
C1-CLOSE-R1 PR #87 = PASS / MERGED / COMPLETE
C1-CLOSE-R1 merge commit = da381bbd2cc407393e7326e9824bef68ea356e6b
C1 provider calls = 0
C1 spend added = USD 0.00
```

C1 preserves sanitized Vidu terminal task/provider metadata for future evidence, keeps unsafe/raw provider content excluded, and distinguishes internal estimated job cost from provider-side billing truth.

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Execution Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence: CONSUMED / NEVER RERUN
Status: STOPPED
Phase: LIVE-02-GEMINI-IMAGE
OpenAI STORY: SUCCESS
Gemini IMAGE: HTTP 429
Conservative calls: 2 / 6
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
```

R3 MUST NEVER BE RERUN.

---

## Post-R5-VIDU1-COR1 Rule

With P4-WP020-LIVE-R5-VIDU1-COR1 merged to canonical `main`, no active work package exists (`ACTIVE_WORK_PACKAGE = NONE`). The next gate requires a separate explicit Owner decision (`NEXT_GATE = OWNER DECISION REQUIRED`).

A future bounded Vidu credit-generation probe (`P4-WP020-LIVE-R5-VIDU1`) is NOT authorized by PREP/COR1 tooling and must receive separate explicit Owner authorization and a fresh authorization marker bound to post-merge canonical main SHA.

Do not create an R5 paid execution identity, call any external provider, write a paid authorization marker, create or consume an execution fence, dispatch a paid/live workflow, adjust billing, convert credits to USD, release, tag, or deploy without separate explicit Owner authorization.
