# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main
Canonical main SHA: fresh-fetch from GitHub repository truth (Post-Gate-C-UAT-Decision-Close canonical main: cefab1275bf8194f161f97b1a27f6bd50b129eee)

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
   project-docs/40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PATHA_DISCOVERY1.md
3. Newer repository/workflow/Issue/PR truth overrides stale docs.

CANONICAL STATE & ACTIVE GATE:
- P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
- Completed planned Core V1 WPs = 19 / 20 (95% by WP count)
- P4-WP020 = ACTIVE / NOT CLOSED
- Core V1 release = NOT DECLARED
- P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1 = PASS / OWNER APPROVED / MERGED / COMPLETE (PR #113, commit 71476a435013e78d0736cafc2af8c5cb6e27b5fe)
- P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1-CLOSE = PASS / OWNER APPROVED / MERGED / COMPLETE (PR #114, commit cefab1275bf8194f161f97b1a27f6bd50b129eee)
- ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PATHA-DISCOVERY1
- ACTIVE_EXECUTION_PACKAGE = NONE
- PACKAGE_STATUS = IN REVIEW / NOT MERGED
- DISCOVERY_MODE = READ-ONLY / NO-INFRA-MUTATION
- NEXT_CONTROL_DECISION = INDEPENDENT CHATGPT REVIEW OF PATH A DISCOVERY EVIDENCE & OWNER REVIEW
- CURRENT_GATE = Gate C UAT Infrastructure Path A Read-Only Discovery
- NEXT_GATE = Gate C UAT Infrastructure Path A Review & Decision
- DISCOVERY_RESULT = OWNER_ADMIN_INPUT_REQUIRED
- BIND1_ELIGIBILITY = NOT YET PROVEN
- BIND1_STATUS = NOT AUTHORIZED
- PATH_A_STATUS = PROPOSED / DISCOVERY COMPLETE / OWNER ADMIN INPUT REQUIRED
- PATH_B_STATUS = PROPOSED / NOT AUTHORIZED
- GATE_B_STATUS = PASS / OWNER APPROVED / MERGED / COMPLETE
- ROUTED_CHECKPOINT = project-docs/00_CONTROL/CONTINUATION_CHECKPOINT.md
- GATE_C_STATUS = UAT INFRASTRUCTURE PATH A READ-ONLY DISCOVERY COMPLETE / IN PR REVIEW
- REC1_RUN1_STATUS = BLOCKED / NOT AUTHORIZED / UNCONSUMED
- REAL PROVIDER CALLS = 0 (NO-PROVIDER)
- REAL VIDU GET / POST = 0
- NEW PROVIDER JOB = 0
- PAID CALLS = 0
- AUTHORIZED_BASE_MAIN = cefab1275bf8194f161f97b1a27f6bd50b129eee
- IN_FLIGHT_BRANCH = ai/p4-wp020-rec1-gatec-infra-patha-discovery1
- OWNER_AUTHORIZATION_COMMENT = 5724264933 (Issue #63)
- LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1-CLOSE (PR #114, commit cefab1275bf8194f161f97b1a27f6bd50b129eee)
- PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1 (PR #113, commit 71476a435013e78d0736cafc2af8c5cb6e27b5fe)
- PREV2_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-VERIFY1-CLOSE (PR #112, commit cb20631556bafdeaf17373fca3fd7ef8d9234c80)
- PREV3_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-VERIFY1 (PR #111, commit da39e32c35b689ba2d2852c7f9b5ca7961a1d92c)
- PREV4_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PREFLIGHT1 (PR #110, commit ead14bf9d9b36958618d0f6d6531ff44b9506492)
- PREV5_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-HARNESS1-CLOSE (PR #109, commit 79bf07cb7907b542d68871c7bc493e72d9562e8a)
- PREV6_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-HARNESS1 (PR #108, commit b605a4d9928a7411a7f41cd7058d3a8fbceae581)
- PREV7_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1-CLOSE (PR #107, commit ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7)
- PREV8_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1 (PR #106, commit e09ee2127d0a20c01f6aad38eb759e5bfba7e248)
- PREV9_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-READY1 (PR #105, commit 0326def88915b25fbb4e2b7019753c2b3fedc0f7)
- PREV10_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP-CLOSE (PR #104, commit ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c)
- PREV11_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-PREP (PR #103, commit 7ff516f317f84278f6143f15cc58b91fd3fa34d5)

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
