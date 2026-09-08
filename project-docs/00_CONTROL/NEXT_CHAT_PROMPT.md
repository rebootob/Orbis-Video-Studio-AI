# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

RESPOND TO OWNER IN THAI.

PROJECT
- Repository: rebootob/Orbis-Video-Studio-AI
- Canonical branch: main

ROLE MODEL
- Owner = final human authority / authorization / UAT / merge approval
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = LOW-CREDIT / BOUNDED Execution Plane only when explicitly authorized
- Codex = STOP by default
- Claude Code = STOP by default
- Repository truth is authoritative

CURRENT CANONICAL TRUTH
- main HEAD after P4-WP019 merge: a09fcab835515679bf4f0bbfce8aec84f7e15062
- P4-WP019 = PASS / CLOSED / MERGED
- P4-WP019 PR #50 = MERGED / CLOSED
- P4-WP019 final reviewed HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
- P4-WP019 final review ID: 5135969695
- P4-WP019 merge commit: a09fcab835515679bf4f0bbfce8aec84f7e15062
- ACTIVE_WORK_PACKAGE = NONE
- IMPLEMENTATION_AUTHORIZED = NONE
- P4-WP020 = PROPOSED / NOT AUTHORIZED
- Completed Core V1 work packages = 19 / 20 (95% by WP count)

MANDATORY STARTUP — BEFORE STATUS OR WORK
1. Fresh-fetch current main HEAD.
2. Read in this exact order:
   project-docs/00_CONTROL/START_HERE.md
   project-docs/00_CONTROL/CURRENT_STATE.md
   project-docs/00_CONTROL/ACTIVE_TASK.md
   project-docs/00_CONTROL/DOCUMENT_INDEX.md
   project-docs/00_CONTROL/CHAT_HANDOFF.md
   project-docs/00_CONTROL/NEXT_CHAT_PROMPT.md
   project-docs/40_DELIVERY/WORK_PACKAGES.md
3. Read routed product/architecture documents only when relevant.
4. Live repository truth newer than these documents overrides stale text.

KNOWN COMPLETED STATE
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
P3-WP016 = PASS / CLOSED / MERGED
P3-WP017 = PASS / CLOSED / MERGED
P4-WP018 = PASS / CLOSED / MERGED
P4-WP019 = PASS / CLOSED / MERGED

P4-WP019 CLOSURE
- PRE1 PR #49 merged at 5f3ccbbcd0ee528bb85501a32efb64c5b13fbce5
- Implementation PR #50 merged at a09fcab835515679bf4f0bbfce8aec84f7e15062
- Final reviewed implementation HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
- Final Independent Review: PASS / READY FOR OWNER MERGE DECISION (Review ID 5135969695)
- Exact-head CI before merge:
  - Backend: 412 passed, 2 skipped
  - Frontend: 52/52 tests PASS
  - Frontend build/typecheck: PASS
  - Frontend lint: 0 errors

P4-WP019 ACCEPTED CAPABILITIES
1. .orbis ZIP-compatible archive package.
2. Canonical manifest/checksum trust root and canonical JSON.
3. Archive security/path/size/compression guards.
4. FULL_SELF_CONTAINED Core V1 archive contract only.
5. Full project graph export/import.
6. CLONE import with UUID/FK remap, storage re-upload and source lineage.
7. RESTORE import with fail-closed collision handling.
8. Phase-3 referential-integrity and asset-completeness preflight.
9. Historical RenderJob/GenerationJob truth preservation and worker fencing.
10. Historical UsageLedger truth preservation, partial-index fencing and budget exclusion.
11. Transaction rollback and storage compensation.
12. REST API export/import endpoints.
13. Frontend Export/Import UX with fixed canonical archive contract.

OWNER-LOCKED PRODUCT DIRECTION
- Orbis is an AI Video Production Orchestrator / Production Control Plane, not a foundation model.
- Provider-neutral boundaries:
  CreativeProvider
  ImageProvider
  VideoProvider
  AudioProvider
- Core owns production state, lineage, references, locks, history, approvals, durable jobs, retry/resume/reconciliation, cost/budget, QC, assembly, render, multi-output and project portability.
- Core V1 modes: STORY, SHORT, LOOP, SCENE.
- Architecture-ready later only: PRODUCT, EXPLAINER, PRESENTER, MONTAGE.
- Vidu remains the Core V1 default VideoProvider behind an adapter.
- LOCAL_AI = DISALLOWED.
- Cloud-hosted ComfyUI is future planning only.

LOCKED PRODUCT QUALITIES
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
HUMAN_REVIEW_NOT_HUMAN_MICROMANAGEMENT = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION_CORE_V1 = REQUIRED
PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE

CURRENT GATE
ACTIVE_WORK_PACKAGE = NONE
P4-WP019 = PASS / CLOSED / MERGED
P4-WP020 = PROPOSED / NOT AUTHORIZED

NEXT ALLOWED ACTION
- Inspect/define P4-WP020 scope, E2E/UAT matrix, release gates and closure evidence when requested by Owner.
- Present a bounded P4-WP020 authorization contract to Owner.
- Do NOT start P4-WP020 implementation until explicit Owner authorization.
- Do NOT reopen P4-WP019 absent a proven regression.
- Do NOT expand into post-Core-V1 integrations/providers.
- Do NOT merge future implementation without explicit Owner approval.
```
