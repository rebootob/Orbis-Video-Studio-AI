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
ACTIVE_WORK_PACKAGE = NONE
```

---

## Current Canonical Truth

```text
Canonical main:
dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b

R2-C1:
PASS / MERGED / CLOSED
PR #74
Merge: d706acacd1f51224c955fb9c8d0d9eab3deda186

R3-PRE1:
PASS / COMPLETED
PR #75
Reviewed HEAD: 28f8095d581556b27feed67e27f82c004ea07bbc
Merge: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Metadata probe run: 34291500281
Probe: ACCESS_PROBE_PASS / HTTP 200
Model: gemini-3.1-flash-image
generation_request_sent: false
paid_generation_calls: 0
PRE1 spend: USD 0.00

R3 paid/live execution: NOT AUTHORIZED
R3 execution tooling: NOT AUTHORIZED
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

## R3 PRE1 Accepted Evidence

PRE1 was Owner-authorized as NO-PAID only and is now complete.

Accepted post-merge probe evidence:

```text
Workflow: WP020 LIVE R3 PRE1 Gemini Access Probe (No-Paid)
Run: 34291500281
Main: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Conclusion: success
ACCESS_PROBE_PASS
HTTP 200
gemini-3.1-flash-image
generation_request_sent=false
paid_generation_calls=0
```

Interpretation:
- configured Gemini credential can authenticate to current model metadata;
- target model is visible through metadata access;
- no image-generation submission was made;
- this does not prove the generation path itself will succeed;
- no R3 paid authorization or execution fence exists.

Detailed PRE1 contract:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`

---

## Proposed R3 Direction — Not Authorized

R2 used ephemeral PostgreSQL and MinIO. Retained R2 evidence is historical proof, not reusable canonical project state. A future coherent end-to-end LIVE PASS is therefore proposed as a new isolated UAT project and one bounded chain:

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

R3 execution ID and exact binding main SHA remain unassigned.

Draft:
`project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`

---

## Next Gate

No next work package is auto-authorized.

The next proposed gate is **R3 paid one-shot execution-tooling preparation only**. Before any implementation:

1. fresh-fetch canonical `main`;
2. review current control docs, Issue #63, and latest workflow history;
3. present a bounded tooling-only contract to the Owner;
4. obtain explicit Owner authorization;
5. implement only that tooling scope;
6. STOP again for review/merge before any paid authorization or execution.

PRE1 PASS by itself does not authorize tooling, paid provider calls, a R3 fence, release tagging, deployment, or Core V1 release.

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
   - `project-docs/40_DELIVERY/WORK_PACKAGES.md`
   - `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`
   - `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`
3. Inspect Issue #63 and recent workflow evidence for any live decision.
4. Never reuse R1 or R2 execution identities.
5. Never infer paid authorization from PRE1 PASS, a merge, metadata probe success, or generic approval outside the exact presented gate.
6. Never auto-start R3 or declare Core V1 released.
