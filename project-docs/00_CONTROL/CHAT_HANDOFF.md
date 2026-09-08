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
Canonical main at PRE1 start:
d706acacd1f51224c955fb9c8d0d9eab3deda186

C1 corrective:
P4-WP020-LIVE-R2-C1 = PASS / MERGED
PR #74
Reviewed HEAD: 6c66650312ebbd2433e5b00c7864c086ea37e28e
Merge commit: d706acacd1f51224c955fb9c8d0d9eab3deda186

Current active task:
P4-WP020-LIVE-R3-PRE1
Gemini Access Probe + Resume Contract + Control-Truth Sync

Working branch:
ai/p4-wp020-live-r3-pre1

PRE1 provider generation calls allowed: 0
PRE1 paid spend allowed: USD 0.00
R3 paid/live execution: NOT AUTHORIZED
```

---

## P4-WP020 LIVE History That Must Not Be Lost

### R1

- consumed / immutable;
- bounded OpenAI request returned HTTP 429;
- STOP enforced;
- never rerun R1.

### R2

```text
Execution ID: LIVE-20260909-BB75-R2
Run ID: 34287696335
Main SHA: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
No-paid preflight: PASS
EXECUTION_STARTED fence: WRITTEN / CONSUMED
```

Observed R2 sequence:

1. OpenAI STORY succeeded.
2. OpenAI usage = 544 prompt / 585 completion tokens.
3. Last known confirmed/committed cost at STOP = USD 0.0072.
4. Gemini IMAGE reached provider and returned non-success HTTP surfaced as `HTTP_ERROR`.
5. Exact historical HTTP status was not retained.
6. Chargeable requests conservatively consumed = 2/6.
7. STOP enforced.
8. Vidu, ElevenLabs and downstream live proof were not executed.
9. Never rerun R2.

C1 made future Gemini non-2xx status/classification durable but cannot reconstruct the R2 status retroactively.

---

## Active PRE1 Contract

Owner authorized `P4-WP020-LIVE-R3-PRE1` as **NO-PAID** only.

Allowed:

- manual-only Gemini metadata access tooling;
- after merge, exactly one authenticated `GET /v1beta/models/gemini-3.1-flash-image`;
- sanitized status/provider/model/http-status/error classification only;
- zero-network tests covering 200/400/401/403/404/429/5xx;
- secret/provider-body leakage checks;
- control-truth sync;
- draft R3 contract.

Forbidden:

- OpenAI request;
- Gemini generation request or `/interactions`;
- Vidu/ElevenLabs request;
- paid workflow dispatch;
- R1/R2 rerun;
- R3 paid authorization/fence/execution;
- release tag/production deployment.

Detailed PRE1 contract:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`

---

## Proposed R3 Direction — Not Authorized

R2 used ephemeral PostgreSQL and MinIO. The retained artifact is accepted historical evidence but is not reusable canonical project state. Therefore a future end-to-end LIVE PASS must create a new isolated project and run one coherent bounded chain:

```text
OpenAI STORY x1
Gemini IMAGE x1
Vidu VIDEO x1
ElevenLabs AUDIO x3
Maximum calls: 6
Hard cap: USD 1.00
Sequential only
OpenAI retries: 0
```

R3 execution ID and binding main SHA are intentionally unassigned until later execution tooling is merged and fresh Owner paid/live authorization is recorded.

Draft:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`

---

## PRE1 Verification and Next Gate

Before merge proposal:

```text
Targeted PRE1 tests = PASS
Full backend CI = PASS
Fresh PostgreSQL migration paths = PASS
Frontend CI = PASS if triggered
Workflow = workflow_dispatch only
Permissions = contents: read only
Static no-generation guard = PASS
Secret/provider-body leakage = 0
Paid/live workflow dispatch during implementation = 0
Exact diff = PRE1 only
```

Then STOP for Owner merge decision.

After PRE1 merge, manually run the metadata-only probe on `main`. Probe PASS still does not authorize paid R3 execution.

---

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with provider-neutral boundaries:

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

## Mandatory Resume Procedure

1. Fresh-fetch current `main`.
2. Read in order:
   - `project-docs/00_CONTROL/START_HERE.md`
   - `project-docs/00_CONTROL/CURRENT_STATE.md`
   - `project-docs/00_CONTROL/ACTIVE_TASK.md`
   - `project-docs/00_CONTROL/DOCUMENT_INDEX.md`
   - `project-docs/00_CONTROL/CHAT_HANDOFF.md`
   - `project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md`
   - `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`
   - `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`
3. Inspect Issue #63 and recent workflow evidence for any live decision.
4. Never reuse R1 or R2 execution identities.
5. Never infer paid authorization from PRE1, merge, probe PASS, or generic approval outside the exact presented paid gate.
6. Never auto-start R3 or declare Core V1 released.
