# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main
- Canonical main SHA: fresh-fetch from GitHub repository truth (Gate B authorized base: ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7)

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
   project-docs/00_CONTROL/CONTINUATION_CHECKPOINT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_CONTRACT1.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_CONTRACT1_CLOSE.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_HARNESS1.md
3. Newer repository/workflow/Issue/PR truth overrides stale docs.

CANONICAL STATE & ACTIVE GATE:
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- Completed planned Core V1 WPs = 19 / 20 (95% by WP count)
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 = PASS / MERGED / COMPLETE (PR #106, commit e09ee2127d0a20c01f6aad38eb759e5bfba7e248)
- P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1-CLOSE = PASS / MERGED / COMPLETE (PR #107, commit ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7)
- P4-WP020-LIVE-R5-VIDU2-REC1-HARNESS1 = IN REVIEW / NO-PROVIDER / PR OPEN / NOT MERGED
- ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-VIDU2-REC1-HARNESS1
- CURRENT_GATE = Gate B (Execution Harness, Standalone Schema & Failure Matrix)
- NEXT_GATE = CHATGPT_INDEPENDENT_REVIEW
- GATE_B_STATUS = IN PROGRESS / CORRECTIVE IMPLEMENTED / IN REVIEW (REVIEW 5204067383: CHANGES REQUIRED -> R5 CORRECTIVE RESOLVED)
- ROUTED_CHECKPOINT = project-docs/00_CONTROL/CONTINUATION_CHECKPOINT.md
- GATE_C_STATUS = PROPOSED / NOT AUTHORIZED / NOT STARTED
- REC1_RUN1_STATUS = BLOCKED / NOT AUTHORIZED
- REAL PROVIDER CALLS = 0 (NO-PROVIDER)
- REAL VIDU GET / POST = 0
- NEW PROVIDER JOB = 0
- PAID CALLS = 0
- AUTHORIZED_BASE_MAIN = ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7
- LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1-CLOSE (PR #107, commit ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7)
- PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 (PR #106, commit e09ee2127d0a20c01f6aad38eb759e5bfba7e248)
- PREV2_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-READY1 (PR #105, commit 0326def88915b25fbb4e2b7019753c2b3fedc0f7)
- PREV3_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP-CLOSE (PR #104, commit ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c)
- PREV4_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP (PR #103, commit 7ff516f317f84278f6143f15cc58b91fd3fa34d5)
- PREV5_COMPLETED_GATE = P4-WP020-LIVE-R5-FINAL-GAP1-CLOSE (PR #102, commit 8cae4bd72bd447470f214cf852b516b856638b7f)
- PREV6_COMPLETED_GATE = P4-WP020-LIVE-R5-FINAL-GAP1 (PR #101, commit a62d0ebfb1d56aedecfe17c85e5d67752f8de6c0)
- PREV7_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-RUN1-CLOSE (PR #100, commit 1bdcaff64ab756e7144f45f0af44eca1e1bad731)

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
