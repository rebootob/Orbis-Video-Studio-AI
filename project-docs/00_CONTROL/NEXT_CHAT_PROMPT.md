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
1. Fresh-fetch main.
2. Read:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
   project-docs/40_DELIVERY/P4_WP020_LIVE_R3_C1.md
3. Inspect Issue #63 and recent P4-WP020 workflow evidence only when needed for the current gate.
4. Newer repository/workflow/Issue truth overrides stale docs.

CURRENT KNOWN TRUTH
- canonical main before R4-PRE1-CLOSE docs PR: 170e82d19315e80cc7393922d7daa1b1c7f2093b
- P4-WP020 ACTIVE / NOT CLOSED
- Core V1 release NOT DECLARED
- ACTIVE_WORK_PACKAGE = NONE
- LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R4-PRE1
- R4-PRE1-CLOSE = CONTROL-DOC ONLY / OWNER AUTHORIZED
- R4 paid execution NOT AUTHORIZED
- R4 execution identity NONE
- R4 execution fence NONE

R3
- execution ID LIVE-20260909-363F-R3
- run 34297314995
- exact execution main 82ce42116e3f866227dd598814cf79c0b9c640c4
- execution fence CONSUMED
- OpenAI STORY SUCCESS
- usage 546 prompt / 513 completion
- known committed/actual Orbis UAT cost at STOP USD 0.0065
- Gemini IMAGE HTTP 429
- retryable true
- submission_uncertain false
- conservative calls 2/6
- Vidu / ElevenLabs / downstream NOT EXECUTED
- NEVER RERUN R3

R3-C1 / C1-CLOSE
- PR #78 merged exact reviewed head b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6
- C1 status PASS / MERGED / CLOSED
- PR #79 merged
- canonical main advanced to 170e82d19315e80cc7393922d7daa1b1c7f2093b
- C1-CLOSE status PASS / MERGED / COMPLETE

EXTERNAL GEMINI REMEDIATION
- project Orbis-Video-Production
- Billing Tier 1 / Prepay
- observed credit balance USD 5.00
- Nano Banana 2 (Gemini 3.1 Flash Image) quota RPM 100 / TPM 200K / RPD 1K
- prior Free-tier image quota was 0 / 0 / 0
- Owner updated GitHub Actions GEMINI_API_KEY to the new Orbis project key
- secret value is never exposed or persisted

R4-PRE1
- Owner authorized NO-PAID runtime readiness verification on exact main 170e82d19315e80cc7393922d7daa1b1c7f2093b
- full runtime preflight run 34302711166 = SUCCESS
- Gemini metadata-only access probe run 34302730786 = SUCCESS
- both runs exact head SHA 170e82d19315e80cc7393922d7daa1b1c7f2093b
- runtime required credentials present
- PostgreSQL migration PASS
- MinIO/object storage PASS
- provider routing/pricing/budget checks PASS
- current GitHub Actions Gemini credential authenticated
- target model gemini-3.1-flash-image returned HTTP 200 / ACCESS_PROBE_PASS
- generation_request_sent=false
- paid provider/generation calls=0
- execution_fence_written=false
- spend added USD 0.00
- the two NO-PAID runs overlapped briefly but had same exact SHA and no shared paid state/fence; evidence remains valid

NEXT GATE
- finish P4-WP020-LIVE-R4-PRE1-CLOSE CONTROL-DOC ONLY first
- do NOT auto-start R4 paid execution
- after closure merge, candidate gate is separate R4 paid execution planning/authorization
- that gate must create a new immutable R4 execution identity and bind it to exact then-current main
- fresh exact-main Owner paid authorization is required
- fresh no-paid preflight immediately before fence consumption is required
- a new one-shot execution fence is required
- separate explicit Owner run authorization is required
- hard cap/call-count and STOP-on-uncertainty semantics remain mandatory
- no gate auto-authorizes the next one
```
