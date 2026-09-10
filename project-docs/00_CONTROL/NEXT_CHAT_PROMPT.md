# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main
- Canonical main SHA: cdfe3ce44ba9a9d6219909d12c0536c1cd716cec

ROLE MODEL
- Owner = final human authority
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = LOW-CREDIT / BOUNDED Execution Plane only when explicitly authorized
- Codex = STOP by default
- Claude Code = STOP by default
- repository truth is authoritative

MANDATORY STARTUP
1. Fresh-fetch canonical main before any status/merge/authorization/execution decision.
2. Read from the freshest applicable ref in this order:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_C1.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_C1_CLOSE.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PREP.md
3. Newer repository/workflow/Issue/PR truth overrides stale docs.

CANONICAL POST-MERGE BASELINE
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- Completed planned Core V1 WPs = 19 / 20 (95% by WP count)
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- P4-WP020-LIVE-R5-VIDU1-C1 = PASS / MERGED / COMPLETE (PR #94, commit b8d935b2d9e63668663dda0b9d92b5e3c20f1546)
- P4-WP020-LIVE-R5-VIDU1-C1-CLOSE = PASS / MERGED / COMPLETE (PR #95)
- P4-WP020-LIVE-R5-VIDU2-PREP = IN_PROGRESS / PR OPEN / IN REVIEW
- ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-VIDU2-PREP
- CURRENT_GATE = P4-WP020-LIVE-R5-VIDU2-PREP
- NEXT_GATE = CHATGPT_REVIEW_AND_OWNER_MERGE_DECISION
- LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-C1-CLOSE
- PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-C1
- PREV2_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-COR1

IMMUTABLE CONSUMED LIVE HISTORY
- Run 34423580310 / Execution ID LIVE-20260909-VIDU1-R5 = STOPPED / CONSUMED / NEVER RERUN
- Execution canonical main = 5a818b9dbf642b1e456dba51c9a80745d966919e
- Historical HTTP status = UNKNOWN
- Historical Vidu credits consumed = UNKNOWN / NOT CONFIRMED

FUTURE PAID STATUS
- VIDU1_PAID_IDENTITY = NONE / NOT AUTHORIZED
- VIDU1_PAID_EXECUTION = NOT AUTHORIZED
- R5_PAID_IDENTITY = NONE / NOT AUTHORIZED
- R5_PAID_EXECUTION = NOT AUTHORIZED
- Any future probe requires a fresh dedicated execution identity, fresh explicit Owner authorization, and a fresh exact marker bound to canonical main SHA.

NO AUTO-START: Wait for explicit Owner instruction for the next gate.
```
