# Decision Log & Architectural Decision Records (ADRs)

> **Canonical Document Location:** [`project-docs/10_GOVERNANCE/DECISION_LOG.md`](project-docs/10_GOVERNANCE/DECISION_LOG.md)

---

## Architectural Decision Records Summary

| ADR ID | Decision Title | Status | Date |
| :--- | :--- | :--- | :--- |
| ADR-001 | Story-First Production Architecture | ACCEPTED / AMENDED BY ADR-016 | 2026-09-05 |
| ADR-002 | Whole-Story Video Generation Strategy | ACCEPTED / STORY-MODE SPECIFIC | 2026-09-05 |
| ADR-003 | Centralized Reference-Driven Production Model | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-004 | Hybrid Shot Workflow (AI + Imported Assets) | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-005 | Granular Asset & State Locking Machine | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-006 | Vidu-First Provider Adapter Architecture | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-007 | Provider-Independent Adapter Layer | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-008 | Cloud-First & PC-Independent Deployment | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-009 | Integrated Audio Production & Auto-Ducking | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-010 | Simplified Story & Shot Edit Timeline | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-011 | Selective Targeted Asset Regeneration | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-012 | Granular Cost & Provider Usage Control | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-013 | Multi-Output / Multi-Platform Master Rendering | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-014 | External Integration Gateway (Hermes / n8n / API) | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-015 | Configuration Hierarchy & Repository Truth | ACCEPTED / LOCKED | 2026-09-05 |
| ADR-016 | Multi-Mode Video Production Architecture | ACCEPTED / LOCKED | 2026-09-06 |
| **ADR-017** | **Orbis as AI Video Production Orchestrator / Control Plane** | **ACCEPTED / LOCKED** | **2026-09-06** |
| **ADR-018** | **Multi-Project Full-History Retention** | **ACCEPTED / LOCKED** | **2026-09-06** |
| **ADR-019** | **Automation-First, Approval-Gated Production** | **ACCEPTED / LOCKED** | **2026-09-06** |
| **ADR-020** | **Guided Flexibility UX & Progressive Disclosure** | **ACCEPTED / LOCKED** | **2026-09-06** |

---

## Key ADR Details

### ADR-001: Story-First Production Architecture — Amended

Original decision: cohesive narrative video production uses Brief/Docs -> Story -> Script -> Scenes -> Shots.

ADR-016 amends this rule so that it remains fully applicable to **STORY mode**, but is no longer a mandatory path for every Project.

### ADR-006: Vidu-First Provider Adapter Architecture

Vidu is the default V1 video provider behind provider-neutral interfaces. Core domain and UI may not depend directly on Vidu contracts.

### ADR-007: Provider-Independent Adapter Layer

External AI capabilities must integrate through stable adapter/service boundaries rather than changing production core logic.

Current direction separates provider concerns conceptually as:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Specific vendors may change over time without redesigning Project/Scene/Shot/history/approval/cost/QC core behavior.

### ADR-014: External Integration Gateway & Idempotency

External agents and automation systems may interact only through governed API/webhook boundaries with authentication, permission, audit and idempotency protections. Full Hermes/n8n operational integration remains post-Core V1 unless separately authorized.

### ADR-016: Multi-Mode Video Production Architecture

**Context:** Not every useful video requires a full narrative screenplay. Short-form, seamless loop and standalone scene production would be unnecessarily constrained by mandatory Story -> Script creation.

**Decision:** Introduce provider-neutral `video_mode` orchestration.

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready future modes:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Mode routing:

```text
STORY -> Story -> Script -> Scenes -> Shots
SHORT -> Hook/Concept -> Scene -> Shots
LOOP -> Loop Spec -> Shot(s)
SCENE -> Scene -> 1-N Shots
```

**Consequences:**
- Story becomes optional at Project domain level.
- Video Mode is separate from Purpose, Target Platform, Aspect Ratio and Output Preset.
- All modes reuse Reference, Shot, Provider Adapter, Queue, Lock, Cost, Approval, Timeline and Output infrastructure where applicable.
- No mode may call a video provider directly from core domain logic.
- Architecture readiness for future modes does not authorize their implementation.

### ADR-017: Orbis as AI Video Production Orchestrator / Control Plane

**Context:** Modern Creative/Image/Video/Audio AI services evolve quickly. Rebuilding foundation-model capability inside Orbis would increase cost, complexity and vendor-specific maintenance without improving the core product value.

**Decision:** Orbis is an **AI Video Production Orchestrator / Production Control Plane**. It coordinates capable external AI providers behind adapters while Orbis owns the durable production state and workflow.

Orbis-owned responsibilities include:
- Project / Scene / Shot structure and lineage
- references and continuity intent
- locks and approvals
- version/history retention
- durable queue, retry, resume and reconciliation
- cost/budget control
- QC and final-review state
- assembly/render/export orchestration

**Consequences:**
- Do not train/recreate foundation models unless separately authorized.
- Do not turn Orbis into a heavyweight manual NLE as a substitute for orchestration.
- Provider replacement should not require rewriting production-domain logic.

### ADR-018: Multi-Project Full-History Retention

**Decision:**

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
```

Projects must remain isolated and reopenable. Important Story/Scene/Shot/Asset/Reference/Generation/Cost/Approval/Lock history must not be silently destroyed by ordinary edits or regeneration.

Normal lifecycle UX should prefer archive/version lineage over destructive hard deletion. Current-state loading may remain efficient by separating current state from historical/audit state.

### ADR-019: Automation-First, Approval-Gated Production

**Decision:** AI performs repetitive production work; humans review and approve at useful checkpoints.

Target staged path:

```text
Brief / References
-> Story
-> Review / Approve
-> Storyboard
-> Review / Approve
-> Shot Plan + Prompts
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
```

The user may stop before expensive downstream generation. Full Auto can exist only as an explicit user choice and must not eliminate safe control. Batch generation, retry and continue-incomplete behavior are required product principles.

### ADR-020: Guided Flexibility UX & Progressive Disclosure

**Decision:** The UI should behave like an AI producer/production assistant that knows the next sensible step without trapping the user in a rigid wizard.

Required UX principles:
- one clear next recommended action
- concise contextual explanation
- safe defaults
- Simple mode hides provider/model/technical controls
- Advanced mode preserves expert control
- no dead-end empty/error states
- plain-language recovery actions
- known expensive actions expose cost/estimate when available
- unknown cost remains explicitly UNKNOWN

Guiding phrase:

```text
Simple enough for first-time users
Powerful enough for advanced users
Consistent across every screen
Safe for costly AI actions
Beautiful but not distracting
```
