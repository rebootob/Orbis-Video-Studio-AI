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
6. project-docs/30_PRODUCT/PRODUCT_VISION.md
7. project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md
8. project-docs/30_PRODUCT/USER_WORKFLOW.md
9. project-docs/30_PRODUCT/V1_SCOPE.md
10. only other directly relevant routed documents

Then inspect:
- GitHub Issue #24 and ALL Product Lock / UX addendum comments
- PR #25 and latest review/corrective comments
- exact current PR #25 HEAD and changed files
- current workflow/CI results for that exact HEAD

KNOWN COMPLETED STATE:
P0-WP001 = PASS / CLOSED / MERGED
P1-WP002 = PASS / CLOSED / MERGED
P1-WP003 = PASS / CLOSED / MERGED
P1-WP004 = PASS / CLOSED / MERGED
P1-WP005 = PASS / CLOSED / MERGED
P2-WP006 = PASS / CLOSED / MERGED
P2-WP007 = PASS / CLOSED / MERGED
P2-WP008 = PASS / CLOSED / MERGED
P2-WP009 = PASS / CLOSED / MERGED
P2-WP010 = PASS / CLOSED / MERGED

WP007 reviewed HEAD:
5a03d4d7f56ac8ae39a78914276610c0512da78b
WP007 merge:
9cb098dea7fc2948b023ad48163c729f566573a7

WP008 reviewed HEAD:
a2c3f3d4e80a0b0aedb58fba5a04a436c9e88797
WP008 merge:
a360c3b38d1d962f9f3c5f6412e3107e90fae7db

WP009 reviewed HEAD:
250df0bb6df24577e2e1f14c7ada3d0dbbaf75fa
WP009 merge:
9f094a5cbe9a4faeb5741231d0a819da0da283c1

WP010 reviewed HEAD:
0f0a16fa95c8110bc8ab7a0c52d45351eaa82182
WP010 merge / documented main HEAD:
639e61fb69b6abee8598074add458035db906ceb
WP010 PR:
#25 (MERGED / CLOSED)

CURRENT GATE:
ACTIVE WORK PACKAGE = NONE
CURRENT_GATE = OWNER DECISION FOR NEXT WORK PACKAGE
NEXT CANDIDATE = P2-WP011 (PROPOSED / NOT AUTHORIZED)

Do not start WP011 or any later WP without explicit Owner authorization.

PLANNING NOTE FOR FUTURE WP011:
PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE
When WP011 is authorized, ensure:
- selective/batch operations avoid unbounded loading
- avoid N+1 database queries
- pagination/chunking for large job/shot sets
- required DB indexes for batch/resume paths
- bounded concurrency and truthful batch progress
- performance/load regression tests

FUTURE-PERFORMANCE BACKLOG (PRESERVED):
- server-side Project pagination
- Asset/Job history pagination
- media thumbnail/lazy-loading
- streaming/multipart large-file upload
- media preview streaming
- frontend virtualization where needed

OWNER-LOCKED PRODUCT DIRECTION:
Orbis is an AI Video Production Orchestrator / Production Control Plane.
Do not rebuild foundation AI models when provider services can be orchestrated behind adapters.

Provider-neutral model:
CreativeProvider -> OpenAI / Gemini / future
ImageProvider -> Gemini Image / OpenAI Image / future
VideoProvider -> Vidu / Veo / future
AudioProvider -> TTS / music / SFX / future

Orbis owns production state/control:
Project, multi-mode structure, references, Story/Scene/Shot lineage, approvals, history/versioning, locks, durable jobs/retry/recovery, cost/budget, QC, assembly and export.

CORE V1 MODES:
STORY
SHORT
LOOP
SCENE

ARCHITECTURE-READY LATER:
PRODUCT
EXPLAINER
PRESENTER
MONTAGE

MULTI-PROJECT / HISTORY LOCKS:
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED

AUTOMATION-FIRST LOCKS:
AUTOMATION_FIRST = REQUIRED
AUTO_STORYBOARD = REQUIRED
AUTO_SHOT_PLANNING = REQUIRED
AUTO_PROMPT_GENERATION = REQUIRED
BATCH_GENERATION = REQUIRED
HUMAN_REVIEW_NOT_HUMAN_MICROMANAGEMENT = REQUIRED

GUIDED FLEXIBILITY:
Always show the next sensible action.
Use safe defaults and progressive disclosure.
Simple mode hides technical provider/model settings.
Advanced mode preserves expert control.
No dead ends; explain blockers and recovery in plain language.

APPROVAL-GATED TARGET FLOW:
Brief / References
-> Story
-> Review / Approve
-> Storyboard
-> Review / Approve
-> Detailed Shot Plan + Prompts
-> Review / Approve
-> Images / Keyframes
-> Continuity QC
-> Review / Approve
-> Video Generation
-> VO / BGM / SFX / Ambience
-> Auto Assembly
-> Final QC
-> Final Approval
-> Render / Export

The user must be able to inspect Story and Storyboard before detailed Shot/Image/Video generation.
Full Auto may exist, but must not remove safe user control.

AUDIO CORE V1:
VO = REQUIRED
BGM = REQUIRED
SFX = REQUIRED
AMBIENCE = REQUIRED
BASIC_AUTO_DUCKING = REQUIRED
BATCH_AUDIO_AUTOMATION = REQUIRED
ADVANCED_DAW_STYLE_EDITING = OUT OF V1

ARCHITECTURE LOCKS:
Cloud-first
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
Vidu = V1 default video provider behind adapter
Provider abstraction required
Vendor lock-in prohibited
Human approval before final render
Multi-output from one master project

ROLES:
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = low-credit bounded Execution Plane only when implementation is genuinely necessary
Codex = STOP by default
Claude Code = STOP

AUTOMATION INFRA:
Local Antigravity watcher/dispatcher is PAUSED and not production-trusted.
Do not depend on it.

FIRST ACTION:
Report exact live main HEAD and exact PR #25 HEAD.
If PR #25 has a new corrective HEAD, independently review only the authorized WP010 scope and compare it against Issue #24 + addenda.
If the PR HEAD is still 291ea773681831a0a68e585eb7e0664902102be3, report that no corrective commit is available yet and wait.
Do not merge or start another WP automatically.
```
