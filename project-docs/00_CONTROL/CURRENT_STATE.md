# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_TOOL1_START: 363ffe6a0bd325c7c557b80daa665ee3575df6f8

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: R3 TOOL1 AUTHORIZED / IMPLEMENTATION IN PROGRESS / NO-PAID

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R3-TOOL1
CURRENT_GATE: TOOLING IMPLEMENTATION -> CI -> INDEPENDENT REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED
```

---

## Immutable LIVE History

### R1
- consumed and immutable;
- bounded OpenAI request returned HTTP 429;
- never rerun R1.

### R2
```text
Execution ID: LIVE-20260909-BB75-R2
Run ID: 34287696335
Main SHA: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
Execution fence: CONSUMED
```
- OpenAI STORY = SUCCESS;
- Gemini IMAGE = non-success surfaced as `HTTP_ERROR`;
- exact historical Gemini HTTP status unavailable;
- conservative chargeable requests consumed = 2/6;
- last known confirmed/committed UAT cost = USD 0.0072;
- Vidu / ElevenLabs / downstream live proof = NOT EXECUTED;
- never rerun R2.

### R2-C1
- PR #74 = PASS / MERGED / CLOSED;
- merge `d706acacd1f51224c955fb9c8d0d9eab3deda186`;
- future Gemini non-2xx failures retain sanitized HTTP status/classification in durable job evidence;
- provider calls = 0; spend = USD 0.00.

### R3-PRE1
- PR #75 = PASS / MERGED / COMPLETED;
- merge `dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b`;
- metadata probe run `34291500281` = `ACCESS_PROBE_PASS` / HTTP 200;
- model `gemini-3.1-flash-image` visible;
- `generation_request_sent=false`;
- `paid_generation_calls=0`;
- spend = USD 0.00.

PRE1 proves metadata-level authentication/model visibility only, not image-generation success.

---

## Active Gate — R3 TOOL1

`P4-WP020-LIVE-R3-TOOL1 — Bounded One-Shot Execution Tooling Preparation`

```text
Owner authorization: APPROVED
Type: NO-PAID / CODE + TEST + CONTROL-DOC
Branch: ai/p4-wp020-live-r3-tool1
Base main: 363ffe6a0bd325c7c557b80daa665ee3575df6f8
R3 execution identity: LIVE-20260909-363F-R3
R3 paid/live authorization: NOT AUTHORIZED
R3 execution fence: NOT WRITTEN
TOOL1 provider generation calls: 0
TOOL1 spend authorization: USD 0.00
```

TOOL1 is authorized to prepare manual-only no-paid preflight and one-shot execution tooling, fail-closed call/budget/identity guards, durable sanitized failure evidence, tests, and control docs. It does not authorize dispatching either workflow.

Locked future R3 paid boundary:

```text
OpenAI STORY x1
Gemini IMAGE x1
Vidu VIDEO x1
ElevenLabs AUDIO x3
Maximum chargeable requests: 6
Hard cap: USD 1.00
Sequential only
OpenAI retries: 0
```

Detailed TOOL1 contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_TOOL1.md`.
Draft R3 paid contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`.

---

## Required Gates After TOOL1

1. TOOL1 exact-head backend/frontend/migration CI PASS.
2. Independent review PASS.
3. Owner merge approval.
4. Fresh no-paid R3 preflight on exact post-merge `main`.
5. Fresh Owner paid/live authorization tied to exact post-merge main and immutable execution identity.
6. Separate explicit Owner run authorization.
7. Only then may the paid workflow consume the R3 one-shot fence immediately before first possible chargeable request.

No gate auto-authorizes the next one.

---

## Explicitly Forbidden During TOOL1

- no OpenAI/Gemini/Vidu/ElevenLabs generation request;
- no R3 workflow dispatch;
- no R3 execution fence;
- no R3 paid authorization marker;
- no R1/R2 rerun or marker mutation;
- no release tag;
- no production deployment;
- no Core V1 release declaration.
