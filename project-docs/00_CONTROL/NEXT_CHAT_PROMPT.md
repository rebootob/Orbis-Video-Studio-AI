# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main

ROLE MODEL
- Owner = final human authority / authorization / UAT / merge approval
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = LOW-CREDIT / BOUNDED Execution Plane only when explicitly authorized
- Codex = STOP by default
- Claude Code = STOP by default
- Repository truth is authoritative

MANDATORY STARTUP
1. Fresh-fetch current main HEAD.
2. Read in this exact order:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_AUTHORIZATION_CONTRACT.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R2_C1.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md
3. Inspect Issue #63 and recent P4-WP020 workflow evidence for any live/status decision.
4. Newer repository/workflow/Issue #63 truth overrides stale text.

CURRENT KNOWN TRUTH AT R3 PRE1 START
- canonical main: d706acacd1f51224c955fb9c8d0d9eab3deda186
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- completed planned Core V1 work packages = 19 / 20
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED

R1
- consumed / immutable
- bounded OpenAI request returned HTTP 429
- never rerun R1

R2
- execution ID: LIVE-20260909-BB75-R2
- run ID: 34287696335
- main: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
- no-paid preflight PASS
- execution fence consumed
- OpenAI STORY SUCCESS
- OpenAI usage: 544 prompt / 585 completion tokens
- last known confirmed/committed cost at STOP: USD 0.0072
- Gemini IMAGE reached provider and returned non-success HTTP surfaced as HTTP_ERROR
- exact historical Gemini HTTP status unavailable
- chargeable requests conservatively consumed: 2/6
- Vidu / ElevenLabs / downstream live proof NOT EXECUTED
- never rerun R2

C1
- P4-WP020-LIVE-R2-C1 = PASS / MERGED
- PR #74
- reviewed HEAD: 6c66650312ebbd2433e5b00c7864c086ea37e28e
- merge commit: d706acacd1f51224c955fb9c8d0d9eab3deda186
- future Gemini non-2xx evidence now retains sanitized HTTP status/classification
- C1 provider calls: 0
- C1 spend: USD 0.00

ACTIVE TASK
P4-WP020-LIVE-R3-PRE1 — Gemini Access Probe + Resume Contract + Control-Truth Sync

Owner-authorized boundary:
- NO-PAID PRE1 only
- base main: d706acacd1f51224c955fb9c8d0d9eab3deda186
- working branch: ai/p4-wp020-live-r3-pre1
- provider generation calls allowed: 0
- paid spend allowed: USD 0.00

PRE1 ALLOWED
- prepare manual-only Gemini metadata probe
- after merge, exactly one authenticated GET /v1beta/models/gemini-3.1-flash-image
- sanitize output to status/provider/model/http_status/error classification only
- explicit generation_request_sent=false / paid_generation_calls=0
- tests for 200/400/401/403/404/429/5xx with no network
- prove no API-key/provider-body leakage
- sync control docs
- draft R3 contract

PRE1 FORBIDDEN
- no OpenAI request
- no Gemini generation request or /interactions
- no Vidu/ElevenLabs request
- no paid workflow dispatch
- no R1/R2 rerun
- no R3 execution fence or paid authorization marker
- no release tag / production deployment / Core V1 release declaration

R3 DRAFT ONLY — NOT AUTHORIZED
R2 used ephemeral PostgreSQL/MinIO, so retained R2 evidence cannot be reused as canonical Story/project state. A future coherent end-to-end LIVE PASS is proposed as:
- OpenAI STORY x1
- Gemini IMAGE x1
- Vidu VIDEO x1
- ElevenLabs AUDIO x3
- max 6 chargeable requests
- hard cap USD 1.00
- sequential only
- OpenAI retries 0
- new execution ID and exact main SHA assigned only after execution tooling merge
- fresh Owner paid/live authorization required

PRE1 MERGE-READINESS
- targeted PRE1 tests PASS
- full backend CI PASS
- fresh PostgreSQL migrations PASS
- frontend CI PASS if triggered
- workflow_dispatch only
- permissions contents: read only
- static no-generation guard PASS
- secret/provider-body leakage = 0
- no paid/live workflow dispatch during implementation
- exact diff PRE1-only

NEXT GATE
- independently review exact PRE1 branch HEAD + CI
- STOP for Owner merge decision
- after merge, manually run metadata-only probe on main
- probe PASS still does NOT authorize paid R3 execution
- do NOT auto-start R3
- do NOT declare Core V1 released

OWNER-LOCKED PRODUCT DIRECTION
- Orbis = AI Video Production Orchestrator / Production Control Plane
- provider-neutral: CreativeProvider / ImageProvider / VideoProvider / AudioProvider
- Core V1 modes: STORY / SHORT / LOOP / SCENE
- later architecture only: PRODUCT / EXPLAINER / PRESENTER / MONTAGE
- LOCAL_AI = DISALLOWED
- CLOUD_AI = REQUIRED
- VENDOR_LOCK_IN = DISALLOWED
- never auto-expand Core V1 scope
```
