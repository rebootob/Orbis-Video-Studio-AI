# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main

ROLE MODEL
- Owner = final human authority
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = LOW-CREDIT / BOUNDED Execution Plane only when explicitly authorized
- Codex = STOP by default
- Claude Code = STOP by default
- repository truth is authoritative

MANDATORY STARTUP
1. Fresh-fetch main and any active PF1 closure PR/branch.
2. Read:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R4_TOOL1.md
3. Inspect Issue #63 and recent P4-WP020 workflow evidence only when needed for the current gate.
4. Newer repository/workflow/Issue truth overrides stale docs.

CURRENT KNOWN TRUTH
- canonical main at PF1-CLOSE start: 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
- P4-WP020 ACTIVE / NOT CLOSED
- Core V1 release NOT DECLARED
- P4-WP020-LIVE-R4-TOOL1 = PASS / MERGED / COMPLETE via PR #82
- P4-WP020-LIVE-R4-TOOL1-CLOSE-R1 = PASS / MERGED / COMPLETE via PR #83
- P4-WP020-LIVE-R4-PF1 = PASS / COMPLETED / NO-PAID
- R4 execution ID = LIVE-20260909-DE17-R4
- R4 paid authorization = NOT AUTHORIZED
- R4 execution fence = NONE
- R4 paid execution = NOT AUTHORIZED

R4 TOOLING CONTRACT
- tooling base de17a125dcd3b8066a546369d03aba813a7b5641
- Issue #63
- hard cap USD 1.00
- max 6 chargeable provider requests
- exact sequence:
  1. OPENAI_CREATIVE_STORY:gpt-4o
  2. GEMINI_IMAGE:gemini-3.1-flash-image:1K
  3. VIDU_VIDEO:viduq2:text2video:4s:720p
  4. ELEVENLABS_TTS:Thai:<=150chars
  5. ELEVENLABS_MUSIC:<=10s
  6. ELEVENLABS_AMBIENCE:<=3s
- sequential only
- OpenAI retries 0
- future marker: FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact authorized main SHA>
- future fence: EXECUTION_STARTED: LIVE-20260909-DE17-R4
- neither marker nor fence exists yet

CANONICAL OWNER-AUTHORIZED R4-PF1 EVIDENCE
- Owner authorized fresh exact-main PF1 on 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
- run 34313038252 = SUCCESS
- workflow = WP020 LIVE R4 No-Paid Preflight
- run number = 2
- exact SHA = 7de0d3344cd32a1a016f0ee1f4d6121861c57a43
- technical status = PREFLIGHT_PASS
- execution ID = LIVE-20260909-DE17-R4
- required_credentials_present = true
- fresh PostgreSQL 16 migration to Alembic head = PASS
- ephemeral MinIO health = PASS
- provider routing/pricing/budget reservation = PASS
- generation_request_sent = false
- paid_provider_calls = 0
- execution_fence_written = false
- budget cap = USD 1.00
- max paid calls = 6
- estimated total reservation = USD 0.2739
- PF1 spend added = USD 0.00
- Issue #63 result comment = 5596078866
- PF1 PASS does NOT authorize paid execution

PRIOR PF1 GOVERNANCE EVIDENCE
- run 34306778867 = SUCCESS on de08c98f2644ed9e56983aad265a82b32d91e462
- technical NO-PAID PASS only
- dispatch occurred before a separately recorded Owner PF1 authorization gate
- not retroactively authorized
- not the canonical Owner-authorized PF1 completion
- canonical PF1 completion is run 34313038252

R4-PRE1 CLOSED EVIDENCE
- run 34302711166 = SUCCESS full runtime no-paid preflight
- run 34302730786 = SUCCESS Gemini metadata GET / HTTP 200 / ACCESS_PROBE_PASS
- exact SHA = 170e82d19315e80cc7393922d7daa1b1c7f2093b
- generation calls 0
- spend added USD 0.00
- fence false
- Google AI Studio: Orbis-Video-Production Tier 1 / Prepay
- Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K

R3 IMMUTABLE
- execution ID LIVE-20260909-363F-R3
- run 34297314995
- exact execution main 82ce42116e3f866227dd598814cf79c0b9c640c4
- fence CONSUMED
- OpenAI STORY SUCCESS
- Gemini IMAGE HTTP 429
- conservative calls 2/6
- known committed/actual Orbis UAT cost at STOP USD 0.0065
- NEVER RERUN R3

CURRENT ACTIVE GATE
- P4-WP020-LIVE-R4-PF1-CLOSE
- CONTROL-DOC ONLY
- active branch ai/p4-wp020-live-r4-pf1-close
- no source/test/workflow/provider implementation changes
- no provider generation
- no paid authorization marker
- no fence consumption
- no paid workflow dispatch
- closure spend = USD 0.00
- finish exact-head CI + independent review, then STOP for Owner merge decision

NEXT AFTER PF1-CLOSE MERGE
- do NOT auto-start paid execution
- a separate exact-SHA R4 paid authorization may be considered for LIVE-20260909-DE17-R4
- paid authorization does NOT equal RUN authorization
- a later distinct Owner RUN authorization remains required before any chargeable request/fence consumption
- no gate auto-authorizes the next one
```
