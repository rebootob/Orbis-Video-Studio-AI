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

Then note:
- Closed work packages (including Issue #24 / PR #25) may be consulted only for audit, regression, or historical context when relevant. Do NOT require re-review of closed PR #25.

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
P2-WP011 = PASS / CLOSED / MERGED
P2-WP012 = PASS / CLOSED / MERGED
P2-WP013 = PASS / CLOSED / MERGED
P3-WP014 = PASS / CLOSED / MERGED
P3-WP015 = PASS / CLOSED / MERGED

WP014 reviewed HEAD:
cbbcea8c9a84bd9c08222dabf95d1788b2d3945e
WP014 merge:
f50e2568d197b3c4bab5e4303f31af817db6e1bf
WP014 PR:
#36 (MERGED / CLOSED)

WP015 reviewed HEAD:
640212f71182ba3f6a5024a442beb363868eabc1
WP015 merge / main HEAD:
35b31c3c41834209fcb9d63ad7ac52e9632d63d2
WP015 PR:
#38 (MERGED / CLOSED)

CURRENT GATE:
ACTIVE WORK PACKAGE = NONE
CURRENT_GATE = POST-WP015 / READY FOR OWNER NEXT-WP AUTHORIZATION
NEXT CANDIDATE = P3-WP016 (PROPOSED / NOT AUTHORIZED)

Do not start WP016 or any later WP without explicit Owner authorization.

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
1. Fresh-fetch live origin/main and report exact live main HEAD SHA.
2. Confirm ACTIVE_WORK_PACKAGE = NONE and CURRENT_GATE = OWNER DECISION FOR NEXT WORK PACKAGE.
3. Await explicit Owner authorization before starting or implementing any new Work Package (including P2-WP011).
4. Do not start WP011 or any later WP automatically.
```
