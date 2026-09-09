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
1. Fresh-fetch canonical main and PR #88 before any status/merge/authorization/execution decision.
2. Read from the freshest applicable ref in this order:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R4_C1.md
3. Inspect Issue #63 and R4 run 34316188814 when evidence is needed.
4. Newer repository/workflow/Issue/PR truth overrides stale docs.
5. Never use a handoff SHA as a merge target without fresh-fetching the current PR head.

ACTIVE PR AT HANDOFF
- PR = #88
- title = docs(wp020-live): close BILL1 provider billing disposition
- branch = ai/p4-wp020-live-r4-bill1-close
- base main at gate start = da381bbd2cc407393e7326e9824bef68ea356e6b
- scope = P4-WP020-LIVE-R4-BILL1-CLOSE / CONTROL-DOC ONLY
- Owner merge authorization for PR #88 = NOT YET GRANTED

PRE-HANDOFF-SUMMARY CHECKPOINT — HISTORICAL ONLY
- prior reviewed PR head = 56fe78f6ec8bfc450db87b9dba62063b5ae781e6
- Backend Tests 34332792991 = SUCCESS
- backend suite = 538 passed / 2 skipped / 3 warnings
- migrations fresh-head = SUCCESS
- migrations from-revision-010 = SUCCESS
- Frontend Tests 34332792980 = SUCCESS
- independent review = PASS / READY FOR OWNER MERGE DECISION

IMPORTANT: the final handoff-summary documentation commits moved PR #88 beyond 56fe78... . Therefore 56fe78... is NOT the current merge target. Fresh-fetch PR #88 exact current HEAD and use only that current HEAD for CI/review/Owner merge approval.

IMMEDIATE ACTION IN THE NEW CHAT
1. Fresh-fetch canonical main; require no unexpected drift from live GitHub truth.
2. Fresh-fetch PR #88 and capture its exact current HEAD.
3. Confirm PR #88 remains open/mergeable and changed filenames remain exactly these 6 control/delivery docs:
   - project-docs/00_CONTROL/ACTIVE_TASK.md
   - project-docs/00_CONTROL/CHAT_HANDOFF.md
   - project-docs/00_CONTROL/CURRENT_STATE.md
   - project-docs/00_CONTROL/DOCUMENT_INDEX.md
   - project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   - project-docs/40_DELIVERY/WORK_PACKAGES.md
4. Fetch Backend/Frontend workflow runs for that exact current HEAD. Both must be COMPLETED / SUCCESS; backend migrations fresh-head and from-revision-010 must also PASS.
5. Review the exact current diff. Confirm no source/test/workflow/provider/runner/pricing/fence/execution implementation changes, no secret/raw provider content, and BILL1 evidence wording stays exact.
6. Perform/confirm independent review on that exact current HEAD. If PASS, record: INDEPENDENT_REVIEW: PASS / READY FOR OWNER MERGE DECISION.
7. STOP and ask Owner for exact-head merge authorization using:
   อนุมัติ merge PR #88 ที่ HEAD <EXACT_CURRENT_HEAD> เข้า main สำหรับ P4-WP020-LIVE-R4-BILL1-CLOSE CONTROL-DOC ONLY
8. DO NOT merge until Owner explicitly approves that exact current HEAD.

CURRENT KNOWN TRUTH
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- R4 = STOPPED / CONSUMED / NEVER RERUN
- C1 = PASS / MERGED / COMPLETE via PR #85
- C1-CLOSE = PASS / MERGED / COMPLETE via PR #86
- C1-CLOSE-R1 = PASS / MERGED / COMPLETE via PR #87
- BILL1 = PASS / EVIDENCE ACCEPTED / NOT CHARGED
- R5 identity = NONE / NOT AUTHORIZED

BILL1 PROVIDER-SIDE EVIDENCE
- authorization Issue #63 comment = 5598882289
- disposition Issue #63 comment = 5598962073
- Owner-provided Vidu Usage view date range = 2026-08-09 - 2026-09-09 UTC0
- All Keys selected
- Type / Model Version / Resolution / Template / Generate Mode = ALL
- Usage History = No data to export / no usage rows for the displayed range
- displayed range includes R4 interval 2026-09-09T05:45:42Z through approximately 2026-09-09T05:47:19Z
- failed R4 Vidu external billing = NOT CHARGED, meaning no provider-recorded credit usage is shown for the failed task/target interval in accepted evidence
- this does NOT erase the fact that R4 Vidu VIDEO terminal state was FAILED
- internal Vidu job estimate = USD 0.15 / ESTIMATED ONLY
- R4 last known committed/actual Orbis UAT cost at STOP = USD 0.0738
- BILL1 provider calls = 0
- BILL1 spend added = USD 0.00
- no credits-to-USD conversion was inferred

VIDU READINESS EVIDENCE
- Owner-provided post-top-up Vidu Credit Balance = 2,000 credits
- readiness evidence only
- not historical R4 billing evidence
- do not convert to USD in control truth
- does not authorize a provider request

R4 IMMUTABLE EXECUTION TRUTH
- execution ID = LIVE-20260909-DE17-R4
- run = 34316188814
- exact execution main = b1538f655bf526384845c1e8c536ad6fddc66ca7
- fence = CONSUMED / NEVER RERUN
- STOP phase = LIVE-03-VIDU-VIDEO
- conservative paid calls = 3 / 6
- OpenAI STORY = SUCCESS
- Gemini IMAGE = SUCCESS
- Vidu VIDEO = FAILED
- ElevenLabs TTS/Music/Ambience = NOT CALLED
- NEVER RERUN R4

BILL1-CLOSE HARD EXCLUSIONS
- no source/test/workflow/provider implementation change
- no Vidu API call
- no provider generation
- no R4 rerun
- no R5 identity
- no paid authorization marker
- no execution fence
- no paid/live workflow dispatch
- no billing adjustment
- no credits-to-USD conversion
- no release/tag/deploy

AFTER PR #88 IS MERGED — NOT BEFORE
- ACTIVE_WORK_PACKAGE returns to NONE
- wait for a separately authorized next gate
- a possible next gate is R5 NO-PAID readiness/preflight
- BILL1-CLOSE does NOT authorize that readiness gate
- R5 remains NONE / NOT AUTHORIZED until separately approved

NO GATE AUTO-AUTHORIZES THE NEXT ONE.
```
