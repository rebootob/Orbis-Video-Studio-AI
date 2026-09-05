# Decision Log & Architectural Decision Records (ADRs)

> **Canonical Document Location:** [`project-docs/10_GOVERNANCE/DECISION_LOG.md`](project-docs/10_GOVERNANCE/DECISION_LOG.md)

---

## Architectural Decision Records Summary

This log records all baseline architectural decisions governing Orbis Video Studio AI.

| ADR ID | Decision Title | Status | Date |
| :--- | :--- | :--- | :--- |
| **ADR-001** | Story-First Production Architecture | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-002** | Whole-Story Video Generation Strategy | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-003** | Centralized Reference-Driven Production Model | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-004** | Hybrid Shot Workflow (AI + Imported Assets) | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-005** | Granular Asset & State Locking Machine | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-006** | Vidu-First Provider Adapter Architecture | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-007** | Provider-Independent Adapter Layer (Veo/Runway/Luma) | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-008** | Cloud-First & PC-Independent Deployment | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-009** | Integrated Audio Production & Auto-Ducking | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-010** | Simplified Story & Shot Edit Timeline | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-011** | Selective Targeted Asset Regeneration | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-012** | Granular Cost & Provider Usage Control | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-013** | Multi-Output / Multi-Platform Master Rendering | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-014** | External Integration Gateway (Hermes / n8n / API) | **ACCEPTED / LOCKED** | 2026-09-05 |
| **ADR-015** | Configuration Hierarchy & Repository Truth | **ACCEPTED / LOCKED** | 2026-09-05 |

---

## Key ADR Details

### ADR-001: Story-First Production Architecture
- **Context:** Isolated clip generators fail to deliver cohesive narrative videos.
- **Decision:** Video generation flows strictly through narrative stages: Brief/Docs -> Story -> Script -> Scenes -> Shots -> Render.
- **Consequences:** All generation requests must map to an underlying script scene and shot context.

### ADR-006: Vidu-First Provider Adapter Architecture
- **Context:** Need a primary high-quality video generation engine for V1 release.
- **Decision:** Vidu is established as the default provider for V1.
- **Consequences:** Initial adapter spec targets Vidu API contracts, encapsulated behind generic adapter interfaces.

### ADR-007: Provider-Independent Adapter Layer
- **Context:** AI video models evolve rapidly; hardcoding provider logic creates lock-in.
- **Decision:** Implement abstract `VideoGenerationProviderAdapter` interface. Future providers (Veo, Runway, Luma) plug in via adapters.
- **Consequences:** Core domain and UI are completely isolated from provider API changes.

### ADR-014: External Integration Gateway & Idempotency
- **Context:** External AI agents (Hermes) and automation platforms (n8n) need to create projects and trigger rendering.
- **Decision:** Expose a secure REST/Webhook integration gateway enforcing API keys, role permissions, and mandatory `X-Idempotency-Key` headers. Direct DB or provider access is strictly forbidden.
- **Consequences:** Duplicate external API retries will not cause duplicate chargeable video generations.
