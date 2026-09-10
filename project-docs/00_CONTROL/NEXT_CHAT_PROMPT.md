# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main
- Canonical main SHA: fresh-fetch from GitHub repository truth (closure base main: fb72d683c0dd4daa721507b6a0c12dcec17d7366)

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
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PREP_CLOSE.md
3. Newer repository/workflow/Issue/PR truth overrides stale docs.

CANONICAL STATE & ACTIVE GATE:
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- Completed planned Core V1 WPs = 19 / 20 (95% by WP count)
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- P4-WP020-LIVE-R5-VIDU2-PREP-CLOSE = PASS / MERGED / COMPLETE (PR #97, commit 8bc2765a8b09d93340c3aada4f7deff46dc29144)
- P4-WP020-LIVE-R5-VIDU2-PF1 = AUTHORIZED / BLOCKED BEFORE EXECUTION
- P4-WP020-LIVE-R5-VIDU2-PF1-COR1 = IN PROGRESS / PR OPEN
- ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-VIDU2-PF1-COR1
- CURRENT_GATE = P4-WP020-LIVE-R5-VIDU2-PF1-COR1
- NEXT_GATE = CHATGPT_REVIEW_AND_OWNER_MERGE_DECISION
- AUTHORIZED_BASE_MAIN = 8bc2765a8b09d93340c3aada4f7deff46dc29144
- LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-PREP-CLOSE
- PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-PREP (PR #96)
- PREV2_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-C1-CLOSE (PR #95)
- PREV3_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-C1 (PR #94)
- PREV4_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-COR1 (PR #93)
- PREV5_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU1-PREP (PR #92)
- PREV6_COMPLETED_GATE = P4-WP020-LIVE-R5-PRE1-CLOSE-R1 (PR #91)

IMMUTABLE CONSUMED LIVE HISTORY
- Run 34423580310 / Execution ID LIVE-20260909-VIDU1-R5 = STOPPED / CONSUMED / NEVER RERUN
- Execution canonical main = 5a818b9dbf642b1e456dba51c9a80745d966919e
- Historical HTTP status = UNKNOWN
- Historical Vidu credits consumed = UNKNOWN / NOT CONFIRMED

FUTURE PAID STATUS
- VIDU2_PAID_IDENTITY = NONE / NOT AUTHORIZED
- VIDU2_PAID_EXECUTION = NOT AUTHORIZED
- VIDU2_TOOLING_RESERVED_IDENTITY = LIVE-20260910-VIDU2-R5 (TOOLING ONLY / NOT AUTHORIZED FOR LIVE EXECUTION)
- VIDU1_CONSUMED_EXECUTION_ID = LIVE-20260909-VIDU1-R5 (STOPPED / CONSUMED / NEVER RERUN)
- Any future probe refers to VIDU2 tooling only and strictly requires fresh explicit Owner authorization, a fresh exact marker bound to canonical main SHA, and a fresh unconsumed fence.

NO AUTO-START: Wait for explicit Owner instruction for the next gate.
```
