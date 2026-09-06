# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

Repository:
rebootob/Orbis-Video-Studio-AI

Canonical branch:
main

IMPORTANT:
Fresh-fetch current GitHub/repository truth first.
Repository truth newer than documentation is authoritative.

Read in exact order:
1. project-docs/00_CONTROL/START_HERE.md
2. project-docs/00_CONTROL/CURRENT_STATE.md
3. project-docs/00_CONTROL/ACTIVE_TASK.md
4. project-docs/00_CONTROL/DOCUMENT_INDEX.md
5. project-docs/00_CONTROL/CHAT_HANDOFF.md
6. project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md
7. only directly relevant routed documents

KNOWN COMPLETED STATE:
P0-WP001 = PASS / CLOSED / MERGED
P1-WP002 = PASS / CLOSED / MERGED
P1-WP003 = PASS / CLOSED / MERGED
P1-WP004 = PASS / CLOSED / MERGED
P1-WP005 = PASS / CLOSED / MERGED
P2-WP006 = PASS / CLOSED / MERGED
P2-WP007 = PASS / CLOSED / MERGED

WP007 PR #15 reviewed feature HEAD:
5a03d4d7f56ac8ae39a78914276610c0512da78b

WP007 merge commit:
9cb098dea7fc2948b023ad48163c729f566573a7

CURRENT GATE:
ACTIVE WORK PACKAGE = NONE
P2-WP008 = PROPOSED / NOT AUTHORIZED

Do not start WP008 unless the Owner explicitly authorizes it.
Do not reopen WP007 unless a proven regression exists.

OWNER-LOCKED PRODUCT DIRECTION:
Orbis is a cloud-first, provider-independent, reference-driven, shot-based, multi-mode AI video production platform.

Core V1 Video Modes:
STORY
SHORT
LOOP
SCENE

Architecture-ready later:
PRODUCT
EXPLAINER
PRESENTER
MONTAGE

Mode routing:
STORY -> Story -> Script -> Scenes -> Shots
SHORT -> Hook/Concept -> Scene -> Shots
LOOP -> Loop Spec -> Shot(s)
SCENE -> Scene -> 1-N Shots

Story is optional at Project domain level.
Video Mode is separate from Purpose, Target Platform, Aspect Ratio and Output Preset.

ARCHITECTURE LOCKS:
Cloud-first
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
Vidu = V1 default video provider
Provider abstraction required
Vendor lock-in prohibited
Human approval before final render
Multi-output from one master project
No embeddings/vector DB/RAG unless separately authorized

ROLES:
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Architect / Independent Reviewer
Antigravity = low-credit bounded Execution Plane when explicitly authorized
Codex = STOP by default
Claude Code = STOP

AUTOMATION:
Local Antigravity watcher/dispatcher is PAUSED and is not production-trusted.
Do not depend on watcher automation for active project delivery.

FIRST ACTION:
Report exact live main HEAD and current authorization gate.
If WP008 is still only proposed, review the proposal and wait for Owner authorization.
Do not start implementation automatically.
```
