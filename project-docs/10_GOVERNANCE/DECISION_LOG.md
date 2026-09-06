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
| **ADR-016** | **Multi-Mode Video Production Architecture** | **ACCEPTED / LOCKED** | **2026-09-06** |

---

## Key ADR Details

### ADR-001: Story-First Production Architecture — Amended

Original decision: cohesive narrative video production uses Brief/Docs -> Story -> Script -> Scenes -> Shots.

ADR-016 amends this rule so that it remains fully applicable to **STORY mode**, but is no longer a mandatory path for every Project.

### ADR-006: Vidu-First Provider Adapter Architecture

Vidu is the default V1 video provider behind provider-neutral interfaces. Core domain and UI may not depend directly on Vidu contracts.

### ADR-007: Provider-Independent Adapter Layer

Future providers such as Veo, Runway or Luma must integrate by implementing provider adapters rather than changing Story/Scene/Shot core logic.

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
- No mode may call Vidu directly from core domain logic.
- Architecture readiness for future modes does not authorize their implementation.
- Earliest planned base implementation is P2-WP008 and still requires explicit Owner authorization.
