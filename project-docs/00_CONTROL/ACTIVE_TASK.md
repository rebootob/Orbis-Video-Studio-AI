# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R3-PRE1
TITLE = Gemini Access Probe + Resume Contract + Control-Truth Sync
STATUS = OWNER AUTHORIZED / NO-PAID PRE1 IN PROGRESS
BASE_MAIN = d706acacd1f51224c955fb9c8d0d9eab3deda186
WORKING_BRANCH = ai/p4-wp020-live-r3-pre1
PROVIDER_GENERATION_CALLS_ALLOWED = 0
PAID_SPEND_ALLOWED = USD 0.00
```

P4-WP020 remains **ACTIVE / NOT CLOSED**. Core V1 release is not declared.

---

## Preconditions Already Satisfied

- C1 is PASS / MERGED via PR #74.
- C1 merge commit is `d706acacd1f51224c955fb9c8d0d9eab3deda186`.
- R1 and R2 execution identities are consumed and immutable.
- R2 OpenAI STORY success remains accepted historical evidence.
- R2 Gemini failure remains exact-status-unknown because C1 cannot reconstruct old evidence retroactively.

---

## Authorized PRE1 Scope

Implementation may only:

1. add a manual-only Gemini metadata access probe;
2. use exactly one authenticated metadata `GET` to `models/gemini-3.1-flash-image` after PRE1 is merged;
3. authenticate with the configured Gemini key without exposing the key;
4. persist/log only sanitized status/provider/model/http-status/error classification plus explicit no-generation counters;
5. test HTTP 200/400/401/403/404/429/5xx and transport/error handling without network calls;
6. prove provider error body and API key do not leak;
7. synchronize control docs after C1 merge;
8. draft a full-chain R3 resume contract without assigning a paid authorization.

---

## Explicitly Forbidden in PRE1

- no OpenAI request;
- no Gemini generation request;
- no `/interactions`;
- no `generateContent`;
- no prompt/image/media submission;
- no Vidu request;
- no ElevenLabs request;
- no paid/live workflow dispatch;
- no R1/R2 rerun;
- no R3 execution fence;
- no R3 paid authorization marker;
- no release tag;
- no production deployment;
- no Core V1 release declaration.

---

## Required Verification Before Merge Proposal

```text
TARGETED_PRE1_TESTS = PASS required
FULL_BACKEND_CI = PASS required
FRESH_POSTGRES_MIGRATIONS = PASS required
FRONTEND_CI = PASS if repository policy triggers it
WORKFLOW_TRIGGER = workflow_dispatch only
WORKFLOW_PERMISSIONS = contents: read only
STATIC_NO_GENERATION_GUARD = PASS required
SECRET_AND_PROVIDER_BODY_LEAKAGE = 0 required
PAID_LIVE_WORKFLOW_DISPATCH_DURING_IMPLEMENTATION = 0 required
EXACT_DIFF_SCOPE = PRE1 only
```

After independent exact-head review, STOP for Owner merge decision.

---

## Post-Merge PRE1 Probe Gate

After PRE1 tooling is merged, the already-authorized metadata-only probe may be manually dispatched on canonical `main`.

`ACCESS_PROBE_PASS` requires:

- HTTP 200;
- model metadata identity `models/gemini-3.1-flash-image`;
- `generation_request_sent=false`;
- `paid_generation_calls=0`.

Any non-PASS result blocks R3 paid tooling preparation until reviewed.

A probe PASS still does **not** authorize any paid/live generation.

---

## Proposed R3 Only — Not Authorized

The proposed R3 contract is a new coherent six-call chain because R2's ephemeral database/object-storage state is not reusable canonical project state:

```text
OpenAI x1 -> Gemini x1 -> Vidu x1 -> ElevenLabs x3
Hard cap USD 1.00
Sequential only
OpenAI retry 0
```

Execution identity and binding main SHA remain unassigned until later tooling merge and fresh Owner authorization.

---

## Roles

```text
Owner = final human authority / authorization / merge / paid-live gates
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane only when explicitly authorized
Codex = STOP
Claude Code = STOP
```

Contracts:
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`
