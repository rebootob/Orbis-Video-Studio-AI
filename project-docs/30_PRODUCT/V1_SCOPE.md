# V1 Scope Definition & Pass Checklist

> **Canonical Document Location:** [`project-docs/30_PRODUCT/V1_SCOPE.md`](project-docs/30_PRODUCT/V1_SCOPE.md)

---

## 1. Official Core V1 PASS Definition

V1 is NOT PASS until a user can complete an end-to-end browser production flow appropriate to the selected Video Mode:

```text
Create Project
-> Select Video Mode
-> Add Brief / Documents / Prompt / References
-> Build only the creative structure required by that mode
-> Create Shots
-> Generate via provider adapter and/or import media
-> Review and lock approved assets
-> Configure dialogue / VO / music / SFX / subtitle where applicable
-> Preview / edit using simplified timeline
-> Selectively regenerate affected unlocked shots
-> Human approval
-> Cloud render
-> Export final MP4 and approved output variants
```

---

## 2. Core V1 Video Modes

| Mode | V1 Status | Required Creative Path |
| :--- | :--- | :--- |
| STORY | REQUIRED | Story -> Script -> Scenes -> Shots |
| SHORT | REQUIRED | Hook/Concept -> Scene -> Shots; Story optional |
| LOOP | REQUIRED | Loop Spec -> Shot(s); Story/Script optional |
| SCENE | REQUIRED | Scene -> 1-N Shots; Story optional |
| PRODUCT | ARCHITECTURE-READY | Later activation only |
| EXPLAINER | ARCHITECTURE-READY | Later activation only |
| PRESENTER | ARCHITECTURE-READY | Later activation only |
| MONTAGE | ARCHITECTURE-READY | Later activation only |

Video Mode is separate from Purpose, Target Platform, Aspect Ratio and Output Preset.

---

## 3. Architectural Readiness vs Operational Execution

- **Integration Architecture Readiness — REQUIRED FOR V1 DESIGN:** REST/API boundaries, webhook-ready hooks, auth/permissions, audit and idempotent job control.
- **Operational Integration Gateway — POST-CORE V1 / V1.x:** Full Hermes/n8n operational connectors must not block Core V1.
- **Multi-Output Readiness — REQUIRED:** One master project preserves enough metadata for approved 16:9, 9:16, 1:1 and other output variants.
- **Provider Abstraction — REQUIRED:** Core domain code does not directly depend on Vidu or future providers.
- **Cloud-First — REQUIRED:** No local GPU or local AI runtime dependency.

---

## 4. V1 Feature Scope Matrix

| Feature Module | Requirement |
| :--- | :--- |
| Web Workspace UI | REQUIRED FOR CORE V1 |
| Document Ingestion | REQUIRED FOR CORE V1 |
| Story & Script Engine | REQUIRED FOR STORY mode; reusable creative service elsewhere |
| Video Mode Configuration | REQUIRED FOR STORY / SHORT / LOOP / SCENE |
| Reference Asset Library | REQUIRED FOR CORE V1 |
| Vidu Provider Adapter | REQUIRED FOR CORE V1 |
| Durable Generation Queue | REQUIRED FOR CORE V1 |
| Hybrid Shot Support | REQUIRED FOR CORE V1 |
| Asset Lock Mechanism | REQUIRED FOR CORE V1 |
| Audio & Subtitle Engine | REQUIRED FOR CORE V1 where applicable |
| Simplified Timeline | REQUIRED FOR CORE V1 |
| Selective Regeneration | REQUIRED FOR CORE V1 |
| Cost & Usage Controls | REQUIRED FOR CORE V1 |
| Human Approval / QC | REQUIRED FOR CORE V1 |
| Cloud Master Render | REQUIRED FOR CORE V1 |
| Multi-Output Presets | REQUIRED FOR CORE V1 |
| Integration Architecture Readiness | REQUIRED FOR V1 DESIGN |
| Full Operational Integration Gateway | POST-CORE V1 / V1.x |

---

## 5. Explicit Out-of-V1 Boundaries

Without formal scope amendment, V1 excludes:

- enterprise multi-tenant administration
- native iOS / Android apps
- real-time Google-Docs-style collaborative editing
- Premiere Pro-class NLE features
- training proprietary foundation models from scratch
- local GPU / local AI runtime dependencies
- custom-model fine tuning
- dedicated non-Vidu video-provider implementation in the initial build
- full PRODUCT / EXPLAINER / PRESENTER / MONTAGE workflows unless separately promoted into V1 by Owner decision
