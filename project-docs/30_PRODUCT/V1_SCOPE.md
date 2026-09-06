# V1 Scope Definition & Pass Checklist

> **Canonical Document Location:** [`project-docs/30_PRODUCT/V1_SCOPE.md`](project-docs/30_PRODUCT/V1_SCOPE.md)

---

## 1. Official Core V1 PASS Definition

V1 is NOT PASS until a user can complete an end-to-end browser production flow appropriate to the selected Video Mode with automation, review gates, durable history and final export:

```text
Create / Open Project
-> Select Video Mode
-> Add Brief / Documents / Prompt / References
-> Generate or build only the creative structure required by that mode
-> Review / approve Story or Concept when applicable
-> Create / review Storyboard before expensive downstream generation
-> Create / review detailed Shot Plan + Prompts
-> Generate Images / Keyframes where applicable
-> Generate Video Shots via provider adapter and/or import media
-> Review, lock and selectively regenerate affected items
-> Produce VO / BGM / SFX / Ambience with basic mixing / auto-ducking
-> Auto assemble / preview using simplified timeline controls
-> Final QC / explicit human approval
-> Cloud render
-> Export final MP4 and approved output variants
```

The user must not be forced to micromanage every shot. Full Auto may be offered, but safe staged review must remain available.

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

## 3. Core Product Locks

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
AUTO_STORYBOARD = REQUIRED
AUTO_SHOT_PLANNING = REQUIRED
AUTO_PROMPT_GENERATION = REQUIRED
BATCH_GENERATION = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION = CORE_V1_REQUIRED
PROVIDER_INDEPENDENCE = REQUIRED
LOCAL_AI = DISALLOWED
```

The normal user experience should be simple and guided. Advanced provider/model controls must be progressively disclosed rather than required for first-time use.

---

## 4. Provider-Orchestration Requirement

Core V1 does not require Orbis to train or recreate foundation AI models. Orbis orchestrates external provider capabilities through stable boundaries:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Provider implementations may change without rewriting Project/Scene/Shot/history/approval/cost/QC core logic.

Vidu remains the initial/default V1 video provider behind the VideoProvider adapter. Additional production providers are separately authorized work.

---

## 5. V1 Feature Scope Matrix

| Feature Module | Requirement |
| :--- | :--- |
| Multi-Project Dashboard / Workspace UI | REQUIRED FOR CORE V1 |
| Guided Next-Best-Action UX / Simple + Advanced | REQUIRED FOR CORE V1 |
| Document Ingestion | REQUIRED FOR CORE V1 |
| Story & Script Engine | REQUIRED FOR STORY mode; reusable creative service elsewhere |
| Storyboard / Visual Planning Layer | REQUIRED FOR CORE V1 where applicable |
| Approval-Gated Staged Workflow | REQUIRED FOR CORE V1 |
| Video Mode Configuration | REQUIRED FOR STORY / SHORT / LOOP / SCENE |
| Reference Asset Library | REQUIRED FOR CORE V1 |
| Provider-Neutral Creative / Image / Video / Audio Boundaries | REQUIRED FOR CORE V1 DESIGN |
| Vidu Video Provider Adapter | REQUIRED FOR CORE V1 |
| Durable Generation Queue / Retry / Resume / Reconciliation | REQUIRED FOR CORE V1 |
| Hybrid Shot Support | REQUIRED FOR CORE V1 |
| Asset Lock Mechanism | REQUIRED FOR CORE V1 |
| History / Version Lineage / No Silent Loss | REQUIRED FOR CORE V1 |
| Batch Generation / Generate Selected / Continue Incomplete | REQUIRED FOR CORE V1 |
| Audio Production: VO / BGM / SFX / Ambience | REQUIRED FOR CORE V1 |
| Basic Audio Mixing / Fade / Mute / Auto-Ducking | REQUIRED FOR CORE V1 |
| Subtitle Generation / Export where applicable | REQUIRED FOR CORE V1 |
| Simplified Timeline / Auto Assembly | REQUIRED FOR CORE V1 |
| Selective Regeneration | REQUIRED FOR CORE V1 |
| Cost & Usage Controls | REQUIRED FOR CORE V1 |
| Continuity / Final QC and Human Approval | REQUIRED FOR CORE V1 |
| Cloud Master Render | REQUIRED FOR CORE V1 |
| Multi-Output Presets | REQUIRED FOR CORE V1 |
| Integration Architecture Readiness | REQUIRED FOR V1 DESIGN |
| Full Operational Integration Gateway | POST-CORE V1 / V1.x |

---

## 6. Architectural Readiness vs Operational Execution

- **Integration Architecture Readiness — REQUIRED FOR V1 DESIGN:** REST/API boundaries, webhook-ready hooks, auth/permissions, audit and idempotent job control.
- **Operational Integration Gateway — POST-CORE V1 / V1.x:** Full Hermes/n8n/external-agent operational connectors must not block Core V1.
- **Multi-Output Readiness — REQUIRED:** One master project preserves enough metadata for approved 16:9, 9:16, 1:1 and other output variants.
- **Provider Abstraction — REQUIRED:** Core domain code does not directly depend on Vidu, OpenAI, Gemini or future provider SDKs.
- **Cloud-First — REQUIRED:** No local GPU or local AI runtime dependency.

---

## 7. Explicit Out-of-V1 Boundaries

Without formal scope amendment, V1 excludes:

- enterprise multi-tenant administration
- native iOS / Android apps
- real-time Google-Docs-style collaborative editing
- Premiere Pro-class NLE features
- advanced DAW/waveform editing, deep EQ/compressor/limiter, complex audio keyframing or plugin ecosystems
- complex color grading/effects suites
- training proprietary foundation models from scratch
- local GPU / local AI runtime dependencies
- custom-model fine tuning
- full operational Hermes/n8n integration
- full PRODUCT / EXPLAINER / PRESENTER / MONTAGE workflows unless separately promoted by Owner decision
