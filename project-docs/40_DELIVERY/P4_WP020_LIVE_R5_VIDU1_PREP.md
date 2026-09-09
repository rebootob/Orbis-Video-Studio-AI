# P4-WP020-LIVE-R5-VIDU1-PREP — NO-PAID Dedicated Vidu 1-Call Probe Tooling Preparation

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU1-PREP
TYPE: NO-PAID / TOOLING-PREPARATION-ONLY
OWNER_AUTHORIZED: YES (Issue #63 comment 5602834080)
CANONICAL_BASE_MAIN: 5107e3e9ef7702c8403fe74146062ab68e8e50b9
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu1-prep
PROVIDER_GENERATION_CALLS: 0
PAID_PROVIDER_CALLS: 0
VIDU_GENERATION_POSTS: 0
VIDU_CREDITS_CONSUMED: 0
PAID_FENCE_WRITTEN: false
PAID_LIVE_DISPATCH: false
CORE_V1_RELEASE: NOT DECLARED
```

## Purpose

Prepare a dedicated, reviewable, one-shot Vidu probe path that can later be separately authorized for exactly one real Vidu generation POST.

THIS PREP GATE MUST NOT CALL VIDU OR CONSUME CREDITS.

## Required Tooling Contract & Invariants

- Dedicated workflow and runner script for Vidu-only probe;
- Manual `workflow_dispatch` only;
- Default provider/model: Vidu / `viduq2`;
- Target operation: `text-to-video` (4 seconds, 720P);
- OpenAI calls = 0, Gemini calls = 0, ElevenLabs calls = 0;
- Vidu generation POST during PREP = 0;
- Future live execution generation POST maximum = 1;
- Status GET polling supported after confirmed submission (GET only, zero additional POSTs);
- NO automatic generation retry; ambiguous POST/transport outcome must STOP immediately and must never blind-retry;
- Separate one-time execution identity and fence for future VIDU1 paid probe (`LIVE-20260909-VIDU1-R5`); MUST NOT reuse or rerun R4 / R3 / R2 / R1 identities;
- Sanitized evidence schema: task/provider job ID, status, safe provider error code, provider credits field if returned, bounded timing/attempt metadata;
- Never expose secrets or raw provider response bodies;
- No credits-to-USD conversion;
- No full R5 E2E execution;
- No release, tag, or deploy.

## Delivered Artifacts

1. `.github/scripts/wp020_live_r5_vidu1.py`
   - Dedicated 1-call probe runner implementing `Vidu1ProbeRunner`;
   - Enforces hard single POST cap (`generation_post_count < 1`);
   - Rejects consumed execution identities (`LIVE-20260909-DE17-R4`, `LIVE-20260909-363F-R3`, etc.);
   - Supports dry-run / preflight mode with 0 POST calls and 0 credit consumption;
   - Supports GET-only polling with bounded intervals and max poll timeout;
   - Fails closed immediately on ambiguous transport/POST failure (`submission_uncertain = True`) without retry;
   - Generates sanitized evidence JSON without raw bodies, secrets, or credits-to-USD conversion.

2. `.github/workflows/wp020-live-r5-vidu1.yml`
   - Dedicated workflow triggered exclusively via `workflow_dispatch`;
   - Scoped strictly to canonical `main` with ancestry checks;
   - Concurrency group `wp020-live-r5-vidu1-probe`;
   - If mode is `live`, validates Owner authorization marker `FRESH_OWNER_AUTHORIZED_VIDU1: ...` and consumes fence `EXECUTION_STARTED: ...` on Issue #63;
   - Uploads sanitized evidence artifact;
   - Tooling only: NOT DISPATCHED during PREP.

3. `backend/tests/test_wp020_live_r5_vidu1_contract.py`
   - AST validation that forbidden provider generation methods are absent;
   - Workflow trigger and structure assertions;
   - Identity validator assertions rejecting historical runs;
   - AsyncMock unit tests verifying 1 POST + GET polling, 2nd POST blocking, and fail-closed handling of ambiguous POST transport errors;
   - Evidence sanitizer validation verifying absence of secrets and raw response fields.

## Safety Invariants Confirmation

```text
provider_generation_calls = 0
paid_provider_calls = 0
vidu_generation_posts = 0
vidu_credits_consumed = 0
paid_fence_written = false
paid_live_dispatch = false
```

## Next Gate Rule

This authorization covers tooling and preparation only. A future paid probe (`P4-WP020-LIVE-R5-VIDU1`) requires separate explicit Owner authorization after this PR is reviewed and merged.
