# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: R3 PRE1 PASS / COMPLETED / WAITING NEXT OWNER GATE

ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: WAITING OWNER AUTHORIZATION FOR R3 EXECUTION-TOOLING PREPARATION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED
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
Status: PASS / MERGED / CLOSED
PR: #74
Reviewed implementation HEAD: 6c66650312ebbd2433e5b00c7864c086ea37e28e
Merge commit: d706acacd1f51224c955fb9c8d0d9eab3deda186
Provider calls during C1: 0
Paid spend during C1: USD 0.00
```

C1 made future Gemini non-2xx evidence durable using sanitized metadata only: provider, model, HTTP status, error code, retryable, and submission-uncertain. Provider error bodies, headers, credentials, API keys and reference bytes remain excluded.

---

## R3-PRE1 Closure

`P4-WP020-LIVE-R3-PRE1 — Gemini Access Probe + Resume Contract + Control-Truth Sync`

```text
Status: PASS / COMPLETED
PR: #75
Reviewed PRE1 HEAD: 28f8095d581556b27feed67e27f82c004ea07bbc
Merge commit: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Metadata probe run: 34291500281
Probe main SHA: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Probe result: ACCESS_PROBE_PASS
HTTP status: 200
Model: gemini-3.1-flash-image
generation_request_sent: false
paid_generation_calls: 0
PRE1 paid spend: USD 0.00
```

PRE1 proves the configured Gemini credential can authenticate to current model metadata and that `gemini-3.1-flash-image` is visible through the metadata endpoint. It does **not** prove that an image-generation submission will succeed and it does not reconstruct the exact historical R2 Gemini failure status.

No R3 paid authorization or R3 execution fence exists from PRE1.

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

R3 execution ID and exact binding main SHA are intentionally NOT assigned. They may be assigned only inside separately authorized R3 execution tooling, followed by fresh Owner paid/live authorization tied to the exact post-merge main.

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

Core V1 modes: `STORY / SHORT / LOOP / SCENE`.
Later architecture only: `PRODUCT / EXPLAINER / PRESENTER / MONTAGE`.

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

No next work package is auto-authorized.

The next proposed gate is **R3 execution-tooling preparation only**. Before any implementation, ChatGPT must fresh-review canonical `main` and present a bounded tooling contract to the Owner.

Until that separate Owner authorization exists:

- do not create or dispatch R3 paid execution;
- do not write a R3 execution fence;
- do not record a R3 paid authorization marker;
- do not rerun R1 or R2;
- do not declare Core V1 released.
