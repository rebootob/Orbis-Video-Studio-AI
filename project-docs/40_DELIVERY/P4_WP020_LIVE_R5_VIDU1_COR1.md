# P4-WP020-LIVE-R5-VIDU1-COR1 — NO-PAID Workflow Guard Compatibility Corrective

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU1-COR1
TYPE: NO-PAID / WORKFLOW-GUARD-COMPATIBILITY-CORRECTIVE
OWNER_AUTHORIZED: YES (Issue #63 comment 5604486823)
CANONICAL_BASE_MAIN: 42d789efdb49725b1dd45b312ce39cb71ac02d1e
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu1-cor1
FAILED_LIVE_RUN: 34368643536
PROVIDER_GENERATION_CALLS: 0
PAID_PROVIDER_CALLS: 0
VIDU_GENERATION_POSTS: 0
VIDU_CREDITS_CONSUMED: 0
PAID_FENCE_WRITTEN: false
PAID_LIVE_DISPATCH: false
CORE_V1_RELEASE: NOT DECLARED
```

## Purpose

Correct the GitHub Actions workflow comments retrieval syntax in `.github/workflows/wp020-live-r5-vidu1.yml` after hosted GitHub CLI failed closed during live run `34368643536`.

THIS CORRECTIVE WORK PACKAGE IS STRICTLY TOOLING-ONLY (NO-PAID). ZERO PROVIDER CALLS AND ZERO CREDIT CONSUMPTION.

## Root Cause Analysis (Run 34368643536)

During execution of run `34368643536` on canonical `main` (`42d789efdb49725b1dd45b312ce39cb71ac02d1e`), the step `Check Owner authorization & fence if live` failed closed with:
```text
specify only one of --comments or --json
```

The syntax `gh issue view "${ISSUE_NUMBER}" --comments --json comments --jq '.comments[].body'` is rejected by hosted GitHub CLI v2.x because `--comments` (human-formatted output) and `--json` (structured JSON output) are mutually exclusive flags.

### Fail-Closed Confirmation
- The workflow failed before writing the execution fence (`EXECUTION_STARTED: LIVE-20260909-VIDU1-R5`);
- The workflow failed before invoking `.github/scripts/wp020_live_r5_vidu1.py`;
- Zero provider generation calls were executed;
- Zero Vidu generation POSTs occurred;
- Zero credits were consumed.

## Corrective Changes

1. **Workflow Tooling Compatibility (`.github/workflows/wp020-live-r5-vidu1.yml`)**:
   - Replaced incompatible `gh issue view` invocation with:
     ```bash
     COMMENTS="$(gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments" --jq '.[].body')"
     if [ -z "${COMMENTS}" ]; then
       echo "STOP: failed to retrieve Issue #${ISSUE_NUMBER} comments or comment list is empty" >&2
       exit 1
     fi
     ```
   - Maintained full pagination (`--paginate`) across all Issue #63 comments.
   - Enforced fail-closed behavior on empty or failed API response (`[ -z "${COMMENTS}" ]`).
   - Updated `CANONICAL_BASE_SHA` to `42d789efdb49725b1dd45b312ce39cb71ac02d1e`.

2. **Automated Verification Contract (`backend/tests/test_wp020_live_r5_vidu1_contract.py`)**:
   - Added tests A through H verifying:
     - Incompatible flags (`--comments --json`) are absent;
     - Standard `gh api --paginate` endpoint is used;
     - Comment pagination is preserved;
     - Exact Owner authorization marker is required;
     - Consumed fence marker fails closed;
     - Existing terminal PASS/STOP markers fail closed;
     - Empty comment retrieval fails closed;
     - Preserves all safety invariants (max generation POST = 1, dedicated execution identity `LIVE-20260909-VIDU1-R5`, SHA binding, branch guard, no automatic generation retry, ambiguous POST => STOP).

## Post-Merge Authorization Requirement

The authorization marker provided in Issue #63 comment 5604486823:
`FRESH_OWNER_AUTHORIZED_VIDU1: LIVE-20260909-VIDU1-R5 @ 42d789efdb49725b1dd45b312ce39cb71ac02d1e`
was strictly bound to SHA `42d789efdb49725b1dd45b312ce39cb71ac02d1e`.

When PR #93 is merged into `main`, canonical `main` HEAD SHA will advance. The previous marker will no longer match the canonical `main` HEAD SHA.

Therefore, a **fresh Owner authorization marker** bound to the new post-merge canonical `main` HEAD SHA will be mandatory before any paid live probe may be dispatched.

## Safety Invariants Confirmation

```text
provider_generation_calls = 0
paid_provider_calls = 0
vidu_generation_posts = 0
vidu_credits_consumed = 0
paid_fence_written = false
paid_live_dispatch = false
```
