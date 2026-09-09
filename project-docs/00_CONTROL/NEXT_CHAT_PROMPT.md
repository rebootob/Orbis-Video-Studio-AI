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
1. Fresh-fetch main and active R4 TOOL1 branch/PR if still open.
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
- canonical main at R4 TOOL1 start: de17a125dcd3b8066a546369d03aba813a7b5641
- active branch: ai/p4-wp020-live-r4-tool1
- P4-WP020 ACTIVE / NOT CLOSED
- Core V1 release NOT DECLARED
- ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R4-TOOL1
- R4 TOOL1 = OWNER AUTHORIZED / NO-PAID
- R4 execution ID = LIVE-20260909-DE17-R4
- R4 paid authorization = NOT AUTHORIZED
- R4 execution fence = NONE
- R4 paid execution = NOT AUTHORIZED
- TOOL1 provider generation calls = 0
- TOOL1 spend authorization = USD 0.00

R4 TOOL1 CONTRACT
- tooling base main de17a125dcd3b8066a546369d03aba813a7b5641
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
- future marker: FRESH_OWNER_AUTHORIZED_R4: LIVE-20260909-DE17-R4 @ <exact post-merge main SHA>
- future fence: EXECUTION_STARTED: LIVE-20260909-DE17-R4
- neither marker may be written during TOOL1

R4 TOOLING IMPLEMENTATION
- dedicated R4 contract/fence/preflight/failure exporter/workflows/tests
- R4 runner adapter reuses only frozen reviewed R3 runner blob 24150cdece623004443e03ceecea10490955822b
- no dynamic source rewrite
- adapter must STOP on inherited runner blob drift
- paid workflow is manual-only and inert until later gates
- fresh R4 no-paid preflight must run immediately before fence consumption

R4-PRE1 CLOSED EVIDENCE
- run 34302711166 = SUCCESS full runtime no-paid preflight
- run 34302730786 = SUCCESS Gemini metadata GET / HTTP 200 / ACCESS_PROBE_PASS
- exact SHA for both: 170e82d19315e80cc7393922d7daa1b1c7f2093b
- generation calls 0
- spend added USD 0.00
- fence false
- Google AI Studio: Orbis-Video-Production Tier 1 / Prepay, observed credit USD 5.00
- Nano Banana 2 quota RPM 100 / TPM 200K / RPD 1K
- R4-PRE1-CLOSE merged PR #81 -> main de17a125dcd3b8066a546369d03aba813a7b5641

R3 IMMUTABLE
- execution ID LIVE-20260909-363F-R3
- run 34297314995
- exact execution main 82ce42116e3f866227dd598814cf79c0b9c640c4
- fence CONSUMED
- OpenAI STORY SUCCESS
- Gemini IMAGE HTTP 429
- conservative calls 2/6
- known committed/actual Orbis UAT cost at STOP USD 0.0065
- Vidu / ElevenLabs / downstream NOT EXECUTED
- NEVER RERUN R3

NEXT GATE
- finish R4 TOOL1 implementation
- exact-head backend/frontend/migration CI
- independent review
- STOP for Owner merge decision
- merge does NOT authorize PF1, paid auth, fence, or paid run
- after merge: fresh R4 PF1 NO-PAID on exact post-merge main
- then fresh exact-SHA Owner R4 paid authorization
- then separate explicit Owner RUN authorization
- only then may R4 paid workflow execute
- no gate auto-authorizes the next one
```
