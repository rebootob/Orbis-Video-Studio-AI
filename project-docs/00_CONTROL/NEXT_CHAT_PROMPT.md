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
- canonical main after C1 merge: 1c63045497eb7ee708cd81876f6bf7a011907f77
- P4-WP020 ACTIVE / NOT CLOSED
- Core V1 release NOT DECLARED
- ACTIVE_WORK_PACKAGE = NONE
- LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R3-C1
- C1 closure sync = PR #79 CONTROL-DOC ONLY
- R4 NOT AUTHORIZED
- PAID_LIVE_EXECUTION STOP / NOT AUTHORIZED

R3
- execution ID LIVE-20260909-363F-R3
- run 34297314995
- exact execution main 82ce42116e3f866227dd598814cf79c0b9c640c4
- immediate no-paid preflight PASS
- execution fence CONSUMED
- OpenAI STORY SUCCESS
- usage 546 prompt / 513 completion
- known committed/actual Orbis UAT cost at STOP USD 0.0065
- Gemini IMAGE HTTP 429
- retryable true
- submission_uncertain false
- conservative calls 2/6
- Vidu / ElevenLabs / downstream NOT EXECUTED
- STOP evidence comment 5594143482
- NEVER RERUN R3

R3-C1
- PR #78 merged
- exact reviewed head b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6
- merge commit 1c63045497eb7ee708cd81876f6bf7a011907f77
- status PASS / MERGED / CLOSED
- backend CI 34298997460 SUCCESS
- backend tests 511 passed / 2 skipped / 3 warnings
- migrations fresh-head PASS / from-revision-010 PASS
- frontend CI 34298997360 SUCCESS
- strict sanitized structured 429 evidence + nested STOP-artifact allowlist implemented
- provider calls 0
- spend USD 0.00

EXTERNAL GEMINI REMEDIATION
- Owner created/imported project Orbis-Video-Production
- Billing tier now Tier 1 / Prepay
- observed credit balance USD 5.00
- Nano Banana 2 (Gemini 3.1 Flash Image) quota now RPM 100 / TPM 200K / RPD 1K
- prior Free-tier image quota was 0 / 0 / 0
- Owner reports GitHub Actions GEMINI_API_KEY secret updated to the new Orbis project key
- secret value is never exposed or persisted
- runtime adoption of the replacement secret is NOT YET PROVEN

NEXT GATE
- finish/merge PR #79 C1-CLOSE first
- do NOT auto-start R4 or any paid execution
- after C1-CLOSE, candidate gate is P4-WP020-LIVE-R4-PRE1 NO-PAID runtime readiness validation
- R4-PRE1 requires separate Owner authorization
- R4-PRE1 must send no image-generation request, spend USD 0.00, and consume no execution fence
- any future paid execution requires a new identity, fresh exact-main authorization, fresh no-paid preflight, a new one-shot fence, and separate Owner run authorization
```
