# V1 Scope Definition & Pass Checklist

> **Canonical Document Location:** [`project-docs/30_PRODUCT/V1_SCOPE.md`](project-docs/30_PRODUCT/V1_SCOPE.md)

---

## 1. Official V1 PASS Definition

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
                                                        └─► Render in Cloud
                                                              └─► Export complete Final MP4
```

---

## 2. Architectural Readiness vs V1 Scope

- **Integration Readiness:** Architectural design preserves REST API, webhook, and idempotency boundaries for external systems (Hermes, n8n), while V1 focuses on browser user workflow success.
- **Multi-Output Readiness:** Master project asset model preserves aspect ratio and track metadata, while V1 delivers core export presets (16:9 YouTube, 9:16 TikTok/Reels, 1:1 Instagram).

---

## 3. V1 Feature Matrix

| Feature Module | V1 Requirement Status | Implementation Strategy |
| :--- | :--- | :--- |
| **Web Workspace UI** | **REQUIRED FOR V1** | Browser-accessible client workspace UI. |
| **Document Ingestion** | **REQUIRED FOR V1** | Supports text brief, PDF, Word (.docx), PowerPoint (.pptx). |
| **Story & Script Engine** | **REQUIRED FOR V1** | Generates narrative outline, formatted script, scenes, and shots. |
| **Reference Asset Library** | **REQUIRED FOR V1** | Character, Location, Prop, Style, Image, Audio Bibles. |
| **Vidu Provider Adapter** | **REQUIRED FOR V1** | Default Vidu video generation API integration. |
| **Hybrid Shot Support** | **REQUIRED FOR V1** | Mix AI generated, imported video, image, recorded, stock. |
| **Asset Lock Mechanism** | **REQUIRED FOR V1** | Lock Script, Scene, Shot, Character, Voice, Timing entities. |
| **Audio & Subtitle Engine** | **REQUIRED FOR V1** | Dubbing/VO, Music, SFX, Subtitle generation, Auto-ducking. |
| **Simplified Timeline** | **REQUIRED FOR V1** | Multi-track timeline preview (shot layout, trimming, audio placement). |
| **Selective Regeneration** | **REQUIRED FOR V1** | Regenerate only missing or selected unlocked shots. |
| **Cloud Master Render** | **REQUIRED FOR V1** | Cloud video compositing worker render exporting final MP4 video. |
| **Usage & Cost Tracking** | **REQUIRED FOR V1** | Real-time budget tracking per provider job and shot. |
| **Multi-Output Presets** | **REQUIRED FOR V1** | Presets for 16:9 (YouTube), 9:16 (TikTok/Reels), 1:1 (Instagram). |
| **Integration Gateway** | **REQUIRED FOR V1** | Idempotent REST API & webhooks for Hermes / n8n integration. |

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
