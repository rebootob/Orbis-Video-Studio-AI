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
1. Fresh-fetch main and any active reconciliation PR/branch.
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
- canonical main at reconciliation start: de08c98f2644ed9e56983aad265a82b32d91e462
- P4-WP020 ACTIVE / NOT CLOSED
- Core V1 release NOT DECLARED
- P4-WP020-LIVE-R4-TOOL1 = PASS / MERGED / COMPLETE via PR #82
- reviewed TOOL1 HEAD = 7fe35f3c51d248435ab1c90355b29cd1ade66f67
- R4 execution ID = LIVE-20260909-DE17-R4
- R4 paid authorization = NOT AUTHORIZED
- R4 execution fence = NONE
- R4 paid execution = NOT AUTHORIZED

R4 TOOL1 CONTRACT
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

PF1 GOVERNANCE RECONCILIATION
- run 34306778867 = SUCCESS
- workflow = WP020 LIVE R4 No-Paid Preflight
- exact SHA = de08c98f2644ed9e56983aad265a82b32d91e462
- technical status = PREFLIGHT_PASS
- required_credentials_present = true
- generation_request_sent = false
- paid_provider_calls = 0
- execution_fence_written = false
- estimated reservation = USD 0.2739
- IMPORTANT: the dispatch occurred before a separately recorded Owner PF1 authorization gate
- therefore retain as technical NO-PAID evidence only
- NOT adopted as Owner-authorized PF1 completion
- no retroactive authorization inferred
- Issue #63 reconciliation comment = 5595805718

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
- P4-WP020-LIVE-R4-TOOL1-CLOSE-R1
- CONTROL-DOC + PF1 Governance Reconciliation only
- no provider generation
- no paid authorization marker
- no fence consumption
- no paid workflow dispatch
- reconciliation spend = USD 0.00

NEXT AFTER RECONCILIATION MERGE
- do NOT auto-start paid execution
- Owner must explicitly choose:
  A) adopt run 34306778867 as PF1 evidence through a fresh governance gate; or
  B) authorize a fresh R4 PF1 NO-PAID run on the then-current exact main
- only after Owner-authorized PF1 may a separate exact-SHA paid authorization be considered
- then a distinct Owner RUN authorization is still required
- no gate auto-authorizes the next one
```
