# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P2-WP013
```

Status:

```text
ACTIVE / AUTHORIZED
```

Current Work Tracking:

```text
Active Package: P2-WP013 (Provider-Neutral Storyboard Image / Keyframe Pipeline)
Issue: #33
PR: To be opened
Branch: ai/p2-wp013-image-keyframe-pipeline
Start HEAD: cdd79aaa80eaefa8be6c4e4894cb40db0b097a60
Canonical main HEAD: cdd79aaa80eaefa8be6c4e4894cb40db0b097a60
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

## Prior Delivery: P2-WP012 Closure Truth

- **P2-WP012**: PASS / CLOSED / MERGED
- Issue: #31
- PR: #32
- Reviewed HEAD: `a781926bbf607cad1b992d089920be6f094e41c9`
- Merge commit: `cdd79aaa80eaefa8be6c4e4894cb40db0b097a60`
- Final Independent Review: PASS / READY TO MERGE (Review ID: 5125098674)

---

## P2-WP013 Scope & Requirements (Issue #33)

1. **Provider-Neutral Image Provider**:
   - `ImageProvider` abstraction / boundary.
   - Provider implementation isolated behind adapter pattern.
   - Capability & config resolution via provider-neutral configuration.
   - No hardcoded provider endpoints in core orchestrator.
   - No ComfyUI in WP013.

2. **Storyboard / Keyframe Pipeline**:
   - Generate image/keyframe assets for eligible storyboard shots.
   - Persist through existing Asset / Object Storage model.
   - Preserve project -> story/scene -> shot -> asset lineage and version history.
   - Never silently overwrite locked or historical assets.

3. **Continuity & Reference Mapping**:
   - Reuse Reference Library truth (character, location, style).
   - Map relevant references into ImageProvider request.
   - Respect hierarchy and reference locks.
   - Preserve provenance/source metadata for audit and regeneration.

4. **Batch & Selective Operations**:
   - `GENERATE_SELECTED_KEYFRAMES`, `CONTINUE_INCOMPLETE_KEYFRAMES`, `RETRY_FAILED_KEYFRAMES`.
   - Repeat-safe, idempotent, no duplicate active jobs.
   - Completed assets preserved; ambiguous provider outcomes remain fail-closed / reconciliation-required.
   - Set-based / bounded processing; no N+1.

5. **Cost & Approval Safety**:
   - Image jobs participate in UsageLedger / Budget model.
   - Respect hard budget caps.
   - AUTO mode must not silently incur chargeable image generation without explicit cost authorization.
   - Human approval gates remain authoritative.

6. **Production Orchestrator Integration**:
   - Stage flow: `SHOT_PLAN_APPROVED` -> Keyframe/image generation -> `IMAGES_GENERATED` -> `IMAGES_APPROVED` -> Video generation.
   - Browser Recommended Next Action is backend-owned.
   - No generic PATCH status bypass; fail-closed reconciliation.

7. **Frontend Workflow**:
   - Web workspace displays keyframe/image generation status, recommended action, blocked reasons.
   - Support selective and batch keyframe generation from UI.
   - Display generated image assets and history with lazy/bounded media loading.

---

## Next Allowed Action

1. Implement authorized P2-WP013 contract on branch `ai/p2-wp013-image-keyframe-pipeline`.
2. Run full backend tests, frontend tests, lint, typecheck, build, git diff check.
3. Push branch and open PR against main referencing Issue #33.
4. Codex: STOP.
5. Claude Code: STOP.
6. Await ChatGPT Independent Review on PR for Issue #33.
7. Do NOT merge without Owner approval.
8. Do NOT start WP014.
