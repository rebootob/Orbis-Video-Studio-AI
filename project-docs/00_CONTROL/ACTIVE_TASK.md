# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
P2-WP008 — Hybrid Shot Engine, Asset Lock Machine & Base Video Mode Configuration
```

Status:

```text
IMPLEMENTED / WAITING CHATGPT INDEPENDENT REVIEW
```

Owner Authorization:
Authorized via GitHub Issue #18 on feature branch `ai/p2-wp008-hybrid-shot-lock-modes`.

Execution Engine:
Antigravity (bounded execution complete; STOPPING for ChatGPT review).

### Proposed objective

Establish the provider-neutral shot execution and locking layer needed by multiple production modes while preserving the existing Story workflow.

Candidate core scope:

1. Hybrid shot source model: AI generated, imported video, imported image, recorded footage, stock asset and mixed composition.
2. Granular lock state machine for Script / Scene / Shot / Character / Location / Voice / Timing where applicable.
3. Provider-neutral base `video_mode` model and mode configuration.
4. Initial V1 modes: `STORY`, `SHORT`, `LOOP`, `SCENE`.
5. Story becomes optional at Project level where the selected mode does not require it.
6. Configuration inheritance remains Project -> Scene -> Shot.
7. Preserve WP006 Reference Library and WP007 provider/queue boundaries.

Strictly not authorized merely by this proposal:

- PRODUCT / EXPLAINER / PRESENTER / MONTAGE implementation
- frontend workspace implementation
- cost ledger (WP009)
- selective regeneration service (WP011)
- audio/TTS/subtitles
- timeline/render work
- production deployment

---

## Current Execution Roles

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Architect / Independent Reviewer
Antigravity = STOP until explicitly authorized for the next bounded implementation
Codex = STOP
Claude Code = STOP
```

The local GitHub watcher/dispatcher remains PAUSED and must not be treated as a production execution dependency.

---

## Next Allowed Action

Owner may review and explicitly authorize P2-WP008. Until then: documentation/review only, no WP008 application-code implementation.
