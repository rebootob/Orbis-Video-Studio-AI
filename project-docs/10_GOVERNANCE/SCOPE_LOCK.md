# Scope Lock & Boundaries

> **Canonical Document Location:** [`project-docs/10_GOVERNANCE/SCOPE_LOCK.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/10_GOVERNANCE/SCOPE_LOCK.md)

---

## 1. Locked Architectural Principles

The following core principles are **LOCKED** by Project Owner directive and MUST NOT be altered without formal governance review:

1. **Story-First Production:** Video creation begins with narrative structure (Brief -> Story -> Script -> Scenes -> Shots), generating cohesive story videos rather than isolated clips.
2. **Whole-Story Generation:** System optimizes for story flow, visual continuity, and cross-shot consistency.
3. **Reference-Driven Production:** Production utilizes a centralized reference library (Characters, Locations, Documents, Props, Brand, Style, Images, Existing Shots, Audio).
4. **Hybrid Shot Workflow:** Every shot may be AI generated, imported video, imported image, recorded footage, existing stock, or mixed.
5. **Asset Locking:** Approved assets (Script, Scene, Shot, Character, Location, Voice, Timing) can be LOCKED to prevent accidental overwrite during regeneration.
6. **Vidu-First Provider:** Vidu is the DEFAULT video generation provider for V1.
7. **Provider-Independent Architecture:** Provider adapters (Vidu, Veo, Runway, Luma) remain decoupled behind abstract adapter interfaces.
8. **Cloud-First & PC-Independent:** No local GPU or AI dependency. Access via browser anywhere.
9. **Comprehensive Audio Pipeline:** Supports Dialogue/Dubbing, Voice Over, Original Audio, Music/BGM, SFX, Subtitles, and Auto-Ducking.
10. **Simplified Timeline:** V1 timeline focuses on story layout, shot trimming, track placement, and auto-editing — NOT a complex Premiere Pro clone.
11. **Selective Regeneration:** Re-generate only target missing, failed, or selected shots. Complete project regeneration is NEVER the default.
12. **Cost Control & Usage Tracking:** Track cost/job usage per provider, model, generation count, retries, and shot level.
13. **Human Approval Gates:** Configurable approval gates protect against unintended generation costs and final cloud rendering.
14. **Multi-Output / Multi-Platform:** Master project renders to multiple aspect ratios (16:9, 9:16, 1:1), languages, and presets without rebuilding the core story.
15. **Integration-First Architecture:** Controlled integration via REST APIs, webhooks, and connectors for Hermes, n8n, and external AI agents with strict auth and idempotency.

---

## 2. Categorized Scope Matrix

| Category | Features / Elements | Status |
| :--- | :--- | :--- |
| **V1 Scope (Authorized Target)** | Web UI, Document Ingestion (PDF/Word/PPT/Brief), Story/Script Engine, Scene/Shot Pipeline, Vidu Adapter, Hybrid Shot Import, Asset Locking, Reference Library, Audio Subtitle & Ducking, Timeline Preview, Cloud Render, Selective Regeneration, Usage Tracking, Multi-Output Presets, Idempotent Integration Gateway. | **LOCKED (V1 Target)** |
| **Future Planned Scope** | Secondary provider adapters (Veo, Runway, Luma), advanced agent workflows, extended multi-language dubbing. | **PLANNED** |
| **Under Evaluation** | Automated AI QC visual scoring algorithms, automated social publishing connectors. | **TBD** |
| **Out of Scope for V1** | Enterprise multi-user administration, native mobile apps, real-time multi-user collaborative editing, Premiere-class NLE timeline, training proprietary video foundation models, local GPU execution dependencies, custom model fine-tuning. | **OUT OF V1** |

---

## 3. Strict Scope Protection Rule

No agent, developer, or session may silently convert a **PLANNED** or **TBD** item into V1 implementation scope without explicit Project Owner approval and formal Work Package authorization.
