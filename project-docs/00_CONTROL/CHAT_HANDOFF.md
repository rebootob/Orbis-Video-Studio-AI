# Chat Session Handoff

> Canonical location: `project-docs/00_CONTROL/CHAT_HANDOFF.md`
>
> Repository truth newer than this handoff is authoritative.

Repository: `rebootob/Orbis-Video-Studio-AI`  
Canonical branch: `main`

---

## Delivery Baseline

```text
P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
Completed planned Core V1 work packages = 19 / 20
P4-WP020 = ACTIVE / NOT CLOSED
Core V1 release = NOT DECLARED
```

---

## Current Canonical Truth

```text
Canonical main at C1 start:
570acda49245ecae7ae48e1e66ed8839e4bfc2e2

Current active corrective:
P4-WP020-LIVE-R2-C1
Gemini HTTP Evidence + Control-Truth Corrective

Working branch:
ai/p4-wp020-live-r2-c1-gemini-evidence

Paid/live provider execution during C1:
NOT AUTHORIZED
Provider calls allowed: 0
Spend allowed: USD 0.00
```

---

## P4-WP020 LIVE History That Must Not Be Lost

### R1

- R1 live execution identity is consumed and immutable.
- The bounded OpenAI call returned HTTP 429.
- STOP was enforced.
- Do not rerun R1.

### R2

```text
Execution ID: LIVE-20260909-BB75-R2
GitHub Actions run ID: 34287696335
Canonical main: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
No-paid preflight: PASS before execution
EXECUTION_STARTED fence: WRITTEN / CONSUMED
```

Observed R2 sequence:

1. OpenAI STORY succeeded.
2. OpenAI usage = 544 prompt tokens / 585 completion tokens.
3. Last known confirmed/committed UAT cost at STOP = USD 0.0072.
4. Gemini IMAGE request reached provider and returned non-success HTTP.
5. Orbis surfaced `HTTP_ERROR`; exact HTTP status was not retained in durable evidence.
6. Chargeable requests conservatively consumed = 2/6.
7. STOP was enforced immediately.
8. Vidu was not executed.
9. ElevenLabs was not executed.
10. Assembly/subtitle/QC/approval/render/multi-output/archive live downstream proof was not executed.

R2 must never be rerun.

---

## Active Corrective Contract

Owner authorized `P4-WP020-LIVE-R2-C1` as **NO-PAID / CODE + TEST + CONTROL-DOC** only.

Allowed:

- persist sanitized Gemini HTTP failure metadata through existing `GenerationJob.result`;
- retain only provider/model/http status/error code/retryable/submission-uncertain;
- add tests for 400/401/403/429/503;
- verify deterministic vs reconciliation-required semantics;
- synchronize control docs;
- run normal CI and migration checks.

Forbidden:

- real provider request;
- paid workflow dispatch;
- R1/R2 rerun;
- new paid execution identity;
- Gemini model/endpoint change;
- pricing or retry-policy change;
- schema migration;
- release tag or production deployment.

Detailed contract:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R2_C1.md`

---

## Expected C1 Evidence

Before proposing merge, verify:

```text
Targeted Gemini tests = PASS
Full backend CI = PASS
Fresh PostgreSQL migration path = PASS
Frontend CI = PASS if triggered
Secret/provider-body leakage = 0
Paid workflow dispatch during C1 = 0
Exact branch diff = authorized scope only
```

After exact-head independent review, STOP for Owner merge decision.

---

## What Comes After C1

Do **not** auto-start a new live run.

If C1 is merged and the evidence is PASS, the next possible planning gate is a fresh R3 resume contract. A later paid attempt must use:

1. new execution identity;
2. then-current exact `main`;
3. fresh no-paid preflight;
4. bounded provider/cost scope;
5. fresh Owner paid/live authorization;
6. new one-shot execution fence.

The R3 design should avoid repeating already-proven OpenAI work unless there is a specific evidence reason to do so.

---

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with provider-neutral boundaries:

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

## Mandatory Resume Procedure

1. Fresh-fetch current `main`.
2. Read in order:
   - `project-docs/00_CONTROL/START_HERE.md`
   - `project-docs/00_CONTROL/CURRENT_STATE.md`
   - `project-docs/00_CONTROL/ACTIVE_TASK.md`
   - `project-docs/00_CONTROL/DOCUMENT_INDEX.md`
   - `project-docs/00_CONTROL/CHAT_HANDOFF.md`
   - `project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md`
   - relevant P4-WP020 delivery contract(s)
3. Treat newer repository/Issue #63/workflow evidence as authoritative.
4. Never reuse R1 or R2 execution identity.
5. Never infer paid authorization from a merge or generic approval outside the exact presented gate.
6. Never auto-start R3 or declare Core V1 released.
