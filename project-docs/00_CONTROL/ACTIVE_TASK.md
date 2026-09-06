# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX
```

Status:

```text
CORRECTIVE PUSHED / WAITING CHATGPT INDEPENDENT RE-REVIEW / DO NOT MERGE YET
```

Current Pull Request:

```text
PR #25
Branch: ai/p2-wp010-mode-aware-web-workspace
Reviewed HEAD: 9fb1d6fdeee8ec14ffcf2063133fca5263754640
Gate: WAITING CHATGPT INDEPENDENT RE-REVIEW
```

Owner authorization is recorded in GitHub Issue #24 and its Product Lock / UX addendum comments.

Execution Engine:
Antigravity, bounded to the existing WP010 branch/PR only.

## Current Corrective Priorities

1. Remove unsafe hard-delete behavior that conflicts with full-history retention.
2. Preserve multi-project history and no-silent-history-loss behavior.
3. Make staged production explicit and reviewable:
   `Story -> Storyboard -> Shot Plan -> Images -> Video -> Audio -> Final Review -> Export`.
4. Support approval gates and a clear next recommended action.
5. Improve Project Dashboard actions: rename, duplicate, archive, search, sort, recent.
6. Add truthful actionable queue states, Generate Selected / continue incomplete behavior and safe cost confirmation before chargeable batch work.
7. Ensure references/upload UX is real rather than placeholder.
8. Provide lightweight History / Version entry points and reorder/autosave readiness.
9. Fix unsafe CORS configuration.
10. Keep UI simple, guided, professional and progressively disclose advanced settings.

## Locked Product Direction Relevant to WP010

- Multi-project is required.
- Full history retention and auditable changes are required.
- Multi-mode Core V1: STORY / SHORT / LOOP / SCENE.
- Automation-first: AI handles repetitive production work; human reviews and approves.
- User must be able to review Story and Storyboard before detailed Shot/Image/Video generation.
- Guided Flexibility is required: always show a sensible next action while preserving expert control.
- No live paid provider calls are required for WP010 acceptance.
- Audio is Core V1, but WP010 only prepares truthful UI/readiness and must not expand into the full audio engine.

---

## Current Execution Roles

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane for the authorized WP only
Codex = STOP by default
Claude Code = STOP
```

The local GitHub watcher/dispatcher remains PAUSED and must not be treated as a production execution dependency.

---

## Next Allowed Action

Antigravity corrective commit pushed on PR #25. Antigravity MUST STOP.
ChatGPT performs independent review of the exact current PR #25 HEAD.

Do not merge PR #25 without explicit Owner approval.
Do not start WP011 or any later WP automatically.
