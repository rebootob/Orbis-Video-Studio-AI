# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main
- Canonical main SHA: fresh-fetch from GitHub repository truth (REC1-PREP-CLOSE authorized base: 7ff516f317f84278f6143f15cc58b91fd3fa34d5)

ROLE MODEL
- Owner = final human authority / merge approval
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer (ตรวจ GitHub อิสระ)
- Hermes = Execution Coordinator / direct control sync & safe git operator
- Antigravity = LOW-CREDIT / BOUNDED Execution Plane (bounded implementation/testing เฉพาะที่จำเป็นเมื่อได้รับอนุมัติ)
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
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_PREP.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_PREP_CLOSE.md
3. Newer repository/workflow/Issue/PR truth overrides stale docs.

CANONICAL STATE & ACTIVE GATE:
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- Completed planned Core V1 WPs = 19 / 20 (95% by WP count)
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- P4-WP020-LIVE-R5-VIDU2-REC1-PREP = PASS / MERGED / COMPLETE (PR #103, commit 7ff516f317f84278f6143f15cc58b91fd3fa34d5)
- P4-WP020-LIVE-R5-VIDU2-REC1-PREP-CLOSE = IN PROGRESS / DOCS-ONLY / PR OPEN / NOT MERGED
- ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP-CLOSE
- CURRENT_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP-CLOSE
- NEXT_GATE = CHATGPT_INDEPENDENT_REVIEW
- AUTHORIZED_BASE_MAIN = 7ff516f317f84278f6143f15cc58b91fd3fa34d5
- LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP
- PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-FINAL-GAP1-CLOSE
- PREV2_COMPLETED_GATE = P4-WP020-LIVE-R5-FINAL-GAP1
- PREV3_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-RUN1-CLOSE
- PREV4_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-RUN1
- PREV5_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-PF1-CLOSE
- PREV6_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-PF1 (Run 34501285649)

IMMUTABLE CONSUMED LIVE HISTORY
- Run 34569728383 / Execution ID LIVE-20260910-VIDU2-R5 = PASS / CONSUMED / NEVER RERUN
  - Execution canonical main = 04909d7e1f89af25d7d47615775e496948303fd5
  - Generation posts = 1, Poll attempts = 6, Provider job ID = 995880130565918720
  - Video URL present = true
  - Retained recoverable URL = NOT PROVEN
  - Durable VIDEO Asset = NOT PROVEN
  - Provider credits reported = 30.0, Actual credits consumed = UNKNOWN / NOT CONFIRMED
  - USD equivalent = UNKNOWN / NOT CONVERTED
- Run 34423580310 / Execution ID LIVE-20260909-VIDU1-R5 = STOPPED / CONSUMED / NEVER RERUN
  - Execution canonical main = 5a818b9dbf642b1e456dba51c9a80745d966919e
  - Historical HTTP status = UNKNOWN
  - Historical Vidu credits consumed = UNKNOWN / NOT CONFIRMED

FUTURE PAID STATUS
- REC1-RUN1 PROBE = PROPOSED ONLY / NOT AUTHORIZED
- VIDU2_NEXT_PAID_IDENTITY = NONE / NOT AUTHORIZED
- VIDU2_NEXT_PAID_EXECUTION = NOT AUTHORIZED
- FULL_R5_NEXT_PAID_EXECUTION = NOT AUTHORIZED
- Any future live action strictly requires fresh explicit Owner authorization on newest canonical main SHA, a fresh exact marker, and a fresh unconsumed fence.

NO AUTO-START: Wait for explicit Owner instruction for the next gate.
```
