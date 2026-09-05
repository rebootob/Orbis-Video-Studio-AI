# V1 Scope Definition & Pass Checklist

> **Canonical Document Location:** [`project-docs/30_PRODUCT/V1_SCOPE.md`](project-docs/30_PRODUCT/V1_SCOPE.md)

---

## 1. Official Core V1 PASS Definition

V1 is **NOT PASS** until a user can perform the primary end-to-end production path in the Web Workspace UI:

```
Create Project
  └─► Upload Brief / Script / Documents / References
        └─► Create / Edit Story
              └─► Create Scenes
                    └─► Create Shots
                          └─► Generate video via Vidu AND/OR Import existing shots
                                └─► Lock approved assets (Script, Scene, Shot, Character, Voice)
                                      └─► Configure Dialogue / VO / Music / SFX / Subtitle
                                            └─► Preview / Edit using simplified Timeline
                                                  └─► Selective regeneration (affected shots only)
                                                        └─► Cloud Render
                                                              └─► Export complete Final MP4
```

---

## 2. Architectural Readiness vs Operational Execution

- **Integration Architecture Readiness (LOCKED FOR V1):** The system design MUST preserve REST/API boundaries, webhook-ready hooks, authentication boundaries, permission models, audit logging, and idempotent job control (`X-Idempotency-Key`).
- **Operational Integration Gateway (POST-CORE V1 / V1.x):** Full operational integration with external systems (Hermes, n8n) is scheduled as post-core V1 / V1.x delivery, ensuring core browser production flows remain unblocked.
- **Multi-Output Readiness (LOCKED FOR V1):** The master project asset model preserves aspect ratio metadata and track parameters, delivering core export presets (16:9 YouTube, 9:16 TikTok/Reels, 1:1 Instagram).

---

## 3. V1 Feature Scope Matrix

| Feature Module | V1 Requirement Status | Implementation Strategy |
| :--- | :--- | :--- |
| **Web Workspace UI** | **REQUIRED FOR CORE V1** | Browser-accessible client workspace UI. |
| **Document Ingestion** | **REQUIRED FOR CORE V1** | Supports text brief, PDF, Word (.docx), PowerPoint (.pptx). |
| **Story & Script Engine** | **REQUIRED FOR CORE V1** | Generates narrative outline, formatted script, scenes, and shots. |
| **Reference Asset Library** | **REQUIRED FOR CORE V1** | Character, Location, Prop, Style, Image, Audio Bibles. |
| **Vidu Provider Adapter** | **REQUIRED FOR CORE V1** | Default Vidu video generation API integration. |
| **Hybrid Shot Support** | **REQUIRED FOR CORE V1** | Mix AI generated, imported video, image, recorded, stock. |
| **Asset Lock Mechanism** | **REQUIRED FOR CORE V1** | Lock Script, Scene, Shot, Character, Voice, Timing entities. |
| **Audio & Subtitle Engine** | **REQUIRED FOR CORE V1** | Dubbing/VO, Music, SFX, Subtitle generation, Auto-ducking. |
| **Simplified Timeline** | **REQUIRED FOR CORE V1** | Multi-track timeline preview (shot layout, trimming, audio placement). |
| **Selective Regeneration** | **REQUIRED FOR CORE V1** | Regenerate only missing or selected unlocked shots. |
| **Cost & Usage Controls** | **REQUIRED FOR CORE V1** | Budget safety caps and cost audit logging needed for generation safety. |
| **Cloud Master Render** | **REQUIRED FOR CORE V1** | Cloud video compositing worker render exporting final MP4 video. |
| **Multi-Output Presets** | **REQUIRED FOR CORE V1** | Basic approved presets for 16:9 (YouTube), 9:16 (TikTok/Reels), 1:1 (Instagram). |
| **Integration Architecture Readiness** | **REQUIRED FOR V1 DESIGN** | REST API boundary, webhook hooks, auth/permissions, audit logs, idempotency model. |
| **Full Operational Integration Gateway** | **POST-CORE V1 / V1.x** | Active Hermes / n8n operational integration connectors. |

---

## 4. Explicit Out-of-V1 Scope Boundaries

> [!WARNING]
> The following features are strictly **OUT OF V1** and MUST NOT be introduced without formal scope amendment:
> - Enterprise multi-user tenant administration
> - Native mobile apps (iOS / Android)
> - Real-time collaborative multi-user editing (Google Docs style)
> - Premiere Pro-class NLE video editing capabilities
> - Training proprietary video foundation models from scratch
> - Local GPU or local client hardware execution dependencies
> - Fine-tuning custom AI models
> - Implementing non-Vidu video generation provider adapters in initial build
