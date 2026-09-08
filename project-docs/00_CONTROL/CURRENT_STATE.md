# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository truth overrides stale text. This file was resynchronized during `P4-WP020-LIVE-R2-C1` after the consumed R2 live run.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN_HEAD_AT_C1_START: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2

P0-WP001: PASS / CLOSED / MERGED
P1-WP002: PASS / CLOSED / MERGED
P1-WP003: PASS / CLOSED / MERGED
P1-WP004: PASS / CLOSED / MERGED
P1-WP005: PASS / CLOSED / MERGED
P2-WP006: PASS / CLOSED / MERGED
P2-WP007: PASS / CLOSED / MERGED
P2-WP008: PASS / CLOSED / MERGED
P2-WP009: PASS / CLOSED / MERGED
P2-WP010: PASS / CLOSED / MERGED
P2-WP011: PASS / CLOSED / MERGED
P2-WP012: PASS / CLOSED / MERGED
P2-WP013: PASS / CLOSED / MERGED
P3-WP014: PASS / CLOSED / MERGED
P3-WP015: PASS / CLOSED / MERGED
P3-WP016: PASS / CLOSED / MERGED
P3-WP017: PASS / CLOSED / MERGED
P4-WP018: PASS / CLOSED / MERGED
P4-WP019: PASS / CLOSED / MERGED

P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: STOPPED AFTER CONSUMED R2
ACTIVE_WORK_PACKAGE: P4-WP020-LIVE-R2-C1
IMPLEMENTATION_AUTHORIZED: NO-PAID GEMINI HTTP EVIDENCE + TEST + CONTROL-DOC CORRECTIVE
CURRENT_GATE: C1 IMPLEMENTATION / CI / INDEPENDENT REVIEW

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED BY C1
```

---

## Current P4-WP020 Truth

P4-WP020 is no longer merely proposed. It progressed through zero-billing integration work, bounded live authorization, corrective work, and two consumed live execution identities.

### R1 live execution

- R1 is consumed and immutable.
- The first OpenAI live request returned HTTP 429.
- The run stopped under the live contract.
- No automatic paid retry was authorized.

### R2 live execution

```text
Execution ID: LIVE-20260909-BB75-R2
Canonical main: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
GitHub Actions run: 34287696335
Execution fence: CONSUMED
No-paid preflight before fence: PASS
```

Observed result:

1. OpenAI STORY = SUCCESS.
2. OpenAI usage evidence = 544 prompt tokens / 585 completion tokens.
3. Last known confirmed/committed UAT cost at STOP = USD 0.0072.
4. Gemini IMAGE request reached the provider and returned a non-success HTTP outcome surfaced as `HTTP_ERROR`.
5. Exact Gemini HTTP status was not durably retained in the R2 evidence path.
6. Chargeable requests conservatively consumed in R2 = 2/6.
7. Vidu = NOT EXECUTED.
8. ElevenLabs = NOT EXECUTED.
9. Assembly / subtitle / QC / approval / render / multi-output / `.orbis` live downstream proof = NOT EXECUTED.
10. R2 must never be rerun.

The correct state is therefore **STOPPED, not failed-open**. No additional paid generation is authorized until a later fresh Owner gate.

---

## Active Corrective — P4-WP020-LIVE-R2-C1

Owner authorized a no-paid corrective to close the Gemini evidence gap and synchronize control truth.

```text
Task: P4-WP020-LIVE-R2-C1
Title: Gemini HTTP Evidence + Control-Truth Corrective
Base main: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
Working branch: ai/p4-wp020-live-r2-c1-gemini-evidence
Provider calls allowed: 0
Paid spend allowed: USD 0.00
```

Authorized scope:

- persist sanitized Gemini non-2xx metadata through the existing `GenerationJob.result` boundary;
- retain provider/model/http status/error classification/retryable/uncertain flags only;
- do not persist provider error bodies, headers, API keys or secrets;
- cover HTTP 400/401/403/429/503 with tests;
- verify deterministic vs reconciliation-required behavior;
- synchronize current control documents.

Explicitly not authorized:

- real provider call;
- paid workflow dispatch;
- R1/R2 rerun;
- R3 execution identity or paid execution;
- model/endpoint/pricing/retry-policy change;
- release tag or Core V1 release declaration.

Detailed contract: `project-docs/40_DELIVERY/P4_WP020_LIVE_R2_C1.md`.

---

## Locked Product Direction

Orbis Video Studio AI remains a cloud-first, provider-independent **AI Video Production Orchestrator / Production Control Plane**.

Provider boundaries remain:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Core V1 modes remain:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready later only:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Product locks remain:

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

During C1:

1. complete only the authorized no-paid code/tests/docs;
2. run repository CI / migration checks;
3. verify no paid workflow dispatch occurred;
4. independently review exact branch HEAD and diff;
5. STOP for Owner merge decision.

After any C1 merge, a later R3 live attempt requires a new execution identity, a new bounded resume contract, a fresh no-paid preflight, and fresh Owner paid/live authorization tied to then-current exact `main`.

Do not auto-start R3 and do not declare Core V1 released.
