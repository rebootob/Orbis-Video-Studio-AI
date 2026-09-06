# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P3-WP014
```

Status:

```text
ACTIVE / AUTHORIZED
```

Current Work Tracking:

```text
Active Package: P3-WP014 (Core V1 Audio Production Automation)
Issue: #35
PR: To be opened
Branch: ai/p3-wp014-audio-production
Start HEAD: c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd
Canonical main HEAD: c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd
Gate: IMPLEMENTATION / IN PROGRESS
```

Execution Roles:

```text
Owner = final human authority / authorization
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = Bounded Low-Credit Execution Plane
Codex = STOP
Claude Code = STOP
```

---

## Prior Delivery: P2-WP013 Closure Truth

- **P2-WP013**: PASS / CLOSED / MERGED
- Issue: #33
- PR: #34
- Reviewed HEAD: `f9fd46b917390224a5ab58bad0d3be238edbd7b3`
- Merge commit: `c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd`
- Final Independent Review: PASS / READY TO MERGE

---

## P3-WP014 Scope & Requirements (Issue #35)

1. **Provider-Neutral Audio Boundary**:
   - `AudioProvider` abstraction / adapter boundary (VO, BGM, SFX, Ambience).
   - VideoProvider capability discovery (`supports_native_audio`, `supports_dialogue`, `supports_lip_sync`).
   - Provider-neutral configuration and capability resolution without hardcoded provider endpoints.

2. **Locked Three-Dimensional Audio Model**:
   - Source Type: `EMBEDDED_VIDEO_AUDIO`, `GENERATED_AUDIO`, `IMPORTED_AUDIO`, `RECORDED_AUDIO`.
   - Audio Type: `ORIGINAL_AUDIO`, `VO`, `DIALOGUE`, `BGM`, `SFX`, `AMBIENCE`.
   - Generation Mode: `WITH_VIDEO`, `SEPARATE_AUDIO`, `EMBEDDED_EXISTING`.
   - Never conflate these three orthogonal dimensions.

3. **Audio Scope & Ownership Model**:
   - Scopes: `PROJECT`, `SCENE`, `SHOT`, `VIDEO_CLIP`.
   - Lineage through `project_id`, `scene_id`, `shot_id`, `video_asset_id`.
   - Automatic scope assignment with safe human override.

4. **Canonical AudioSpec**:
   - Structured AudioSpec renderable into VideoProvider prompt, TTS request, Music request, SFX request, or manual prompt.

5. **Embedded / Original Video Audio**:
   - First-class non-destructive handling of original clip audio (volume, mute, retain).

6. **Audio Plan & Automated Actions**:
   - `GENERATE_AUDIO_PLAN`, `GENERATE_ALL_VO`, `GENERATE_SELECTED_AUDIO`, `ASSIGN_BGM`, `ASSIGN_SFX`, `ASSIGN_AMBIENCE`, `CONTINUE_INCOMPLETE_AUDIO`, `RETRY_FAILED_AUDIO`, `AUTO_MIX_AUDIO`.

7. **Basic Mixing & Auto-Ducking (Core V1)**:
   - Volume, mute, fade in/out, speech-over-music auto-ducking metadata.

8. **Cost, Budget & Concurrency Safety**:
   - `UsageLedger`, `BudgetService`, hard caps, atomic pre-provider claim, in-flight reservations, fail-closed reconciliation.

9. **Production Orchestrator & Web Workspace**:
   - Progression after video generation: `AUDIO_PLAN` -> `AUDIO_GENERATION` -> `AUDIO_MIX_READY` -> `AUDIO_APPROVED` -> Ready for WP015 assembly.
   - Web workspace audio controls, review, status, and recommended actions.

---

## Next Allowed Action

1. Implement authorized P3-WP014 contract on branch `ai/p3-wp014-audio-production`.
2. Run full backend tests, frontend tests, lint, typecheck, build, git diff check.
3. Push branch and open PR against main referencing Issue #35.
4. Codex: STOP.
5. Claude Code: STOP.
6. Await ChatGPT Independent Review on PR for Issue #35.
7. Do NOT merge without Owner approval.
8. Do NOT start WP015.
