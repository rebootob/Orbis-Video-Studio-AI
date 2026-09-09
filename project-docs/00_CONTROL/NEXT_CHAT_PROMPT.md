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
1. Fresh-fetch main and any active R4-C1 PR/branch.
2. Read:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R4_C1.md
3. Inspect Issue #63 and R4 run 34316188814 when evidence is needed.
4. Newer repository/workflow/Issue truth overrides stale docs.

CURRENT KNOWN TRUTH
- canonical main at R4-C1 start = b1538f655bf526384845c1e8c536ad6fddc66ca7
- P4-WP020 ACTIVE / NOT CLOSED
- Core V1 release NOT DECLARED
- P4-WP020-LIVE-R4-PF1-CLOSE = PASS / MERGED / COMPLETE via PR #84
- P4-WP020-LIVE-R4-C1 = OWNER AUTHORIZED / NO-PAID CORRECTIVE
- active branch = ai/p4-wp020-live-r4-c1

R4 IMMUTABLE EXECUTION TRUTH
- execution ID = LIVE-20260909-DE17-R4
- run = 34316188814
- exact execution main = b1538f655bf526384845c1e8c536ad6fddc66ca7
- fence = CONSUMED / NEVER RERUN
- fence Issue #63 comment = 5596464603
- STOP Issue #63 comment = 5596467391
- terminal status = STOPPED / FAILURE
- phase = LIVE-03-VIDU-VIDEO
- conservative paid calls = 3 / 6
- last known committed/actual Orbis UAT cost at STOP = USD 0.0738
- OpenAI STORY = SUCCESS
- Gemini IMAGE = SUCCESS
- Vidu VIDEO = FAILED
- ElevenLabs TTS/Music/Ambience = NOT CALLED
- NEVER RERUN R4

VIDU BILLING TRUTH
- R4 artifact contains GenerationJob cost_usd = USD 0.15
- source truth shows this is the dispatch-time estimated cost, not proof of provider billing
- classify internal Vidu job estimate = USD 0.15 / ESTIMATED
- classify failed Vidu external billing = UNKNOWN / RECONCILIATION REQUIRED
- do not claim failed task was free
- do not claim provider charged USD 0.15
- provider-side Usage/Billing evidence is needed for run window around 2026-09-09T05:45:42Z through 2026-09-09T05:47:19Z

R4-C1 AUTHORIZED SCOPE
- preserve sanitized Vidu task/provider-job identity on terminal failure
- preserve safe typed provider status / provider error code / provider credits if returned
- never persist raw provider bodies, headers, prompts, credentials or provider error text
- preserve safe typed metadata through durable GenerationJob.result evidence
- make R4 failure sanitizer call the job amount estimated_cost_usd and cost_status ESTIMATED
- mark failed Vidu external billing UNKNOWN
- add mocked regression tests only
- sync control/delivery docs
- provider calls = 0
- spend added = USD 0.00

R4-C1 FORBIDDEN
- no provider API call
- no paid workflow dispatch
- no R4 rerun
- no R5 identity
- no new execution fence
- no billing adjustment without provider evidence
- no release/tag/deploy

CURRENT GATE
- finish R4-C1 bounded implementation
- exact-head Backend/Frontend CI
- independent review
- STOP for explicit Owner merge decision
- C1 merge does NOT authorize R5 or provider calls

R3 IMMUTABLE
- execution ID LIVE-20260909-363F-R3
- run 34297314995
- fence CONSUMED
- STOPPED at Gemini HTTP 429
- conservative calls 2 / 6
- known committed/actual Orbis UAT cost at STOP USD 0.0065
- NEVER RERUN R3

NO GATE AUTO-AUTHORIZES THE NEXT ONE.
```
