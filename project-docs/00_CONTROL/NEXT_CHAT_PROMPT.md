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
3. Inspect Issue #63 and recent P4-WP020 workflow evidence when making any live/status decision.
4. Newer repository/workflow/Issue #63 truth overrides stale text.

CURRENT KNOWN TRUTH AT C1 START
- canonical main: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- completed planned Core V1 work packages = 19 / 20
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED

LIVE R1
- consumed / immutable
- bounded OpenAI request returned HTTP 429
- STOP enforced
- never rerun R1

LIVE R2
- execution ID: LIVE-20260909-BB75-R2
- run ID: 34287696335
- main: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
- no-paid preflight PASS
- EXECUTION_STARTED fence written => R2 consumed
- OpenAI STORY SUCCESS
- OpenAI usage: 544 prompt / 585 completion tokens
- last known confirmed/committed UAT cost at STOP: USD 0.0072
- Gemini IMAGE reached provider, returned non-success HTTP, surfaced as HTTP_ERROR
- exact Gemini HTTP status was not retained in durable R2 evidence
- chargeable requests conservatively consumed: 2/6
- Vidu NOT EXECUTED
- ElevenLabs NOT EXECUTED
- downstream live proof NOT EXECUTED
- STOP enforced
- never rerun R2

ACTIVE CORRECTIVE
P4-WP020-LIVE-R2-C1 — Gemini HTTP Evidence + Control-Truth Corrective

Owner-authorized boundary:
- NO-PAID / CODE + TEST + CONTROL-DOC only
- provider calls allowed: 0
- paid spend allowed: USD 0.00
- working branch: ai/p4-wp020-live-r2-c1-gemini-evidence

C1 ALLOWED
- persist sanitized Gemini non-2xx evidence through existing GenerationJob.result
- retain only provider/model/http_status/error_code/retryable/submission_uncertain
- never persist provider error body, headers, API keys, credentials or reference bytes
- test HTTP 400/401/403/429/503
- verify deterministic failure vs RECONCILIATION_REQUIRED behavior
- sync control docs
- run normal CI/migrations

C1 FORBIDDEN
- no real provider call
- no paid workflow dispatch
- no R1/R2 rerun
- no R3 paid execution
- no model/endpoint/pricing/retry-policy change
- no schema migration
- no release tag or production deployment

C1 MERGE-READINESS EVIDENCE REQUIRED
- targeted Gemini tests PASS
- full backend CI PASS
- fresh PostgreSQL migrations PASS
- frontend CI PASS if triggered
- secret/provider-body leakage = 0
- paid workflow dispatch during C1 = 0
- exact diff remains inside C1 scope

NEXT GATE
- Independently review exact C1 branch HEAD and CI.
- STOP for Owner merge decision.
- Do NOT auto-start R3.
- A later R3 requires a new execution ID, fresh no-paid preflight, bounded resume/cost contract, fresh Owner paid/live authorization tied to exact then-current main, and a new one-shot fence.
- Prefer resuming from Gemini rather than repeating already-proven OpenAI work unless evidence requires otherwise.

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
