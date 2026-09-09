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
1. Fresh-fetch canonical main before any status/merge/authorization/execution decision.
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
- canonical main at C1 closure-sync start = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- P4-WP020-LIVE-R4-C1 = PASS / MERGED / COMPLETE via PR #85
- exact reviewed C1 HEAD = c6f02fe56d4248011b0ef0cb96910d6997195e60
- C1 merge commit = 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
- Backend CI 34323625029 = SUCCESS
- backend suite = 538 passed / 2 skipped / 3 warnings
- both migration paths = SUCCESS
- Frontend CI 34323625048 = SUCCESS
- C1 provider calls = 0
- C1 spend added = USD 0.00
- ACTIVE_WORK_PACKAGE = NONE
- next gate requires explicit Owner authorization

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

VIDU BILLING TRUTH AFTER C1
- internal Vidu job estimate = USD 0.15 / ESTIMATED
- failed Vidu external billing = UNKNOWN / RECONCILIATION REQUIRED
- do not claim failed task was free
- do not claim provider charged USD 0.15
- provider-side Usage/Billing evidence is required to resolve it
- relevant interval: 2026-09-09T05:45:42Z through 2026-09-09T05:47:19Z

R5 / FUTURE LIVE
- R5 identity = NONE
- R5 = NOT AUTHORIZED
- no future provider call is authorized
- no new paid authorization marker is authorized
- no new execution fence is authorized
- no paid/live workflow dispatch is authorized

R3 IMMUTABLE
- execution ID LIVE-20260909-363F-R3
- run 34297314995
- fence CONSUMED
- STOPPED at Gemini HTTP 429
- conservative calls 2 / 6
- known committed/actual Orbis UAT cost at STOP USD 0.0065
- NEVER RERUN R3

CURRENT GATE
- NONE
- wait for explicit Owner decision
- valid future directions may include provider-side Vidu billing evidence disposition or separately authorized readiness work for a new execution identity
- do not auto-start R5
- do not release/tag/deploy

NO GATE AUTO-AUTHORIZES THE NEXT ONE.
```
