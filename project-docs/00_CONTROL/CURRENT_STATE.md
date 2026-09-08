# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_AT_PRE1_START: d706acacd1f51224c955fb9c8d0d9eab3deda186

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: STOPPED AFTER CONSUMED R2 / PREPARING R3 PRE1

ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R3-PRE1
ACTIVE_TITLE: Gemini Access Probe + Resume Contract + Control-Truth Sync
IMPLEMENTATION_AUTHORIZED: NO-PAID PRE1 ONLY
CURRENT_GATE: PRE1 IMPLEMENTATION / CI / INDEPENDENT REVIEW

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED BY PRE1
```

---

## P4-WP020 LIVE History

### R1

- consumed and immutable;
- first bounded OpenAI request returned HTTP 429;
- STOP enforced;
- never rerun R1.

### R2

```text
Execution ID: LIVE-20260909-BB75-R2
Run ID: 34287696335
Main SHA: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
No-paid preflight: PASS
Execution fence: CONSUMED
```

Accepted R2 evidence:

1. OpenAI STORY = SUCCESS.
2. OpenAI usage = 544 prompt tokens / 585 completion tokens.
3. Last known confirmed/committed UAT cost at STOP = USD 0.0072.
4. Gemini IMAGE reached provider and returned a non-success HTTP result surfaced as `HTTP_ERROR`.
5. Exact R2 Gemini HTTP status was not durably retained.
6. Chargeable requests conservatively consumed = 2/6.
7. Vidu = NOT EXECUTED.
8. ElevenLabs = NOT EXECUTED.
9. Downstream live proof = NOT EXECUTED.
10. R2 must never be rerun.

---

## R2-C1 Corrective

`P4-WP020-LIVE-R2-C1 — Gemini HTTP Evidence + Control-Truth Corrective`

```text
Status: PASS / MERGED
PR: #74
Reviewed implementation HEAD: 6c66650312ebbd2433e5b00c7864c086ea37e28e
Merge commit: d706acacd1f51224c955fb9c8d0d9eab3deda186
Provider calls during C1: 0
Paid spend during C1: USD 0.00
```

C1 made future Gemini non-2xx evidence durable using sanitized metadata only: provider, model, HTTP status, error code, retryable, and submission-uncertain. Provider error bodies, headers, credentials, API keys and reference bytes remain excluded.

---

## Active PRE1 — P4-WP020-LIVE-R3-PRE1

Owner authorized PRE1 as **NO-PAID / metadata-probe + tests + docs only**.

```text
Base main: d706acacd1f51224c955fb9c8d0d9eab3deda186
Working branch: ai/p4-wp020-live-r3-pre1
Provider generation calls allowed: 0
Paid spend allowed: USD 0.00
```

Authorized PRE1 work:

- add a manual-only Gemini metadata access probe using exactly one authenticated `GET /v1beta/models/gemini-3.1-flash-image` after merge;
- no `/interactions`, no `generateContent`, no prompt/image payload and no generated media;
- log only sanitized status/model/http-status/error classification;
- tests for 200/400/401/403/404/429/5xx and secret/body non-leakage;
- synchronize control truth;
- draft R3 full-chain resume contract without paid authorization.

The PRE1 metadata probe itself may run only after PRE1 tooling is merged to canonical `main`. A probe PASS does not authorize paid execution.

Detailed PRE1 contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`.

---

## Proposed R3 Direction — Not Authorized

R2 used ephemeral PostgreSQL/MinIO. Its retained artifact is historical evidence, not reusable canonical Story/project state. Therefore a truthful later full LIVE PASS must create a new isolated UAT project and execute a coherent full provider chain.

Proposed R3 bounds:

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

R3 execution ID and exact binding main SHA are intentionally NOT assigned yet. They must be created only after R3 execution tooling is merged and fresh Owner paid/live authorization is given.

Draft contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`.

---

## Locked Product Direction

Orbis Video Studio AI remains a cloud-first, provider-independent AI Video Production Orchestrator / Production Control Plane.

Provider boundaries:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Later architecture only:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Product locks:

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION_CORE_V1 = REQUIRED
PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
VENDOR_LOCK_IN = DISALLOWED
```

---

## Next Allowed Action

During PRE1:

1. complete only authorized metadata-probe tooling/tests/docs;
2. run CI and migration checks;
3. verify no paid/live workflow dispatch occurred;
4. independently review exact PRE1 branch HEAD and diff;
5. STOP for Owner merge decision.

After merge, run the metadata-only PRE1 probe on canonical `main`. Do not auto-start R3 paid execution and do not declare Core V1 released.
