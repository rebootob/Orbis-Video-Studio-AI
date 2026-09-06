# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

Repository:
rebootob/Orbis-Video-Studio-AI

Canonical branch:
main

ROLE MODEL:
- Owner = final human authority / UAT / merge approval
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = primary low-credit bounded Execution Plane
- Codex = STOP by default; use only for genuinely necessary local-only reproduction/verification
- Claude Code = STOP

IMPORTANT:
Fresh-fetch current GitHub/repository truth FIRST.
Repository truth newer than this prompt or documentation is authoritative.
Do not assume the SHAs below are still current if GitHub has advanced.

READ IN EXACT ORDER:
1. AGENTS.md
2. project-docs/00_CONTROL/START_HERE.md
3. project-docs/00_CONTROL/CURRENT_STATE.md
4. project-docs/00_CONTROL/ACTIVE_TASK.md
5. project-docs/00_CONTROL/DOCUMENT_INDEX.md
6. project-docs/00_CONTROL/CHAT_HANDOFF.md
7. project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md
8. GitHub Issue #24
9. PR #25 metadata, latest commits, CI, review comments and exact corrective diff
10. only other directly relevant routed documents/code

KNOWN COMPLETED STATE AT HANDOFF:
P0-WP001 = PASS / CLOSED / MERGED
P1-WP002 = PASS / CLOSED / MERGED
P1-WP003 = PASS / CLOSED / MERGED
P1-WP004 = PASS / CLOSED / MERGED
P1-WP005 = PASS / CLOSED / MERGED
P2-WP006 = PASS / CLOSED / MERGED
P2-WP007 = PASS / CLOSED / MERGED — PR #15
P2-WP008 = PASS / CLOSED / MERGED — PR #19
P2-WP009 = PASS / CLOSED / MERGED — PR #23

KNOWN MAIN HEAD AT HANDOFF:
9f094a5cbe9a4faeb5741231d0a819da0da283c1

ACTIVE WORK PACKAGE:
P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX

ISSUE:
#24

PR:
#25

BRANCH:
ai/p2-wp010-mode-aware-web-workspace

INITIAL REVIEWED HEAD:
291ea773681831a0a68e585eb7e0664902102be3

INITIAL REVIEW VERDICT:
CHANGES REQUIRED / NOT READY TO MERGE

CURRENT CORRECTIVE HEAD AT HANDOFF:
a687c7adca1bf204767410d51ef0e1cad3ee9436

CORRECTIVE COMMIT MESSAGE:
fix(wp010): address review blockers with soft retention, cost confirmation, staged workflow, and truthful readiness

CI AT CURRENT CORRECTIVE HEAD:
backend-tests = PASS
frontend-tests = PASS

CURRENT GATE:
WAITING CHATGPT INDEPENDENT RE-REVIEW

DO NOT ASSUME THE CORRECTIVE IS PASS JUST BECAUSE CI IS GREEN.

PREVIOUS BLOCKERS THAT MUST BE RE-VERIFIED AGAINST THE CURRENT EXACT HEAD:
1. safe retention/archive instead of destructive hard delete
2. staged Story -> Storyboard -> Shot Plan -> Images -> Video review gates
3. state-aware Next Best Action / Guided Flexibility
4. complete minimum multi-project management
5. real reference/document upload and truthful inherited/effective references
6. truthful history/version behavior and preserved prior generated results
7. provider-neutral non-fabricated audio readiness
8. backend-truth-driven QC or Not checked / Not available
9. no fake approval semantics from unrestricted raw project status mutation
10. Generate Selected + cost-safe batch confirmation/estimate + provider-neutral effective config
11. contracted reorder/duplicate/autosave/saved-state UX
12. safe configured CORS
13. truthful progress, Thai/general language support, validated status semantics, lock/cross-project safety

GIT / GOVERNANCE LOCKS:
- main is protected by active ruleset Protect main
- one WP = one branch = one PR
- corrective work stays in SAME WP010 branch and PR #25
- backend-tests is a required status check
- frontend changes must pass frontend-tests
- no direct main write
- no force push
- no replacement PR unless Owner explicitly authorizes
- no merge without ChatGPT PASS + Owner approval
- do not start WP011

LOW-CREDIT POLICY:
- Antigravity performs bounded implementation/corrective work
- use focused tests during corrective loops
- full regression only at final gate unless a concrete failure requires otherwise
- Codex must not duplicate Antigravity implementation/test loops

FIRST ACTION IN THE NEW CHAT:
1. Fresh-fetch live main HEAD and PR #25 HEAD/state/CI/comments.
2. Report whether PR #25 has advanced beyond a687c7adca1bf204767410d51ef0e1cad3ee9436.
3. Independently review the exact CURRENT PR #25 corrective HEAD against Issue #24 and the prior blocking findings.
4. If PASS, report PASS / READY TO MERGE and wait for Owner approval.
5. If findings remain, prepare only bounded corrective instructions for Antigravity on the SAME branch/PR.
6. Do not merge and do not start WP011 automatically.
```
