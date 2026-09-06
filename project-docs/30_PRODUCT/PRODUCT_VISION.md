# Product Vision & Core Mission

> **Canonical Document Location:** [`project-docs/30_PRODUCT/PRODUCT_VISION.md`](project-docs/30_PRODUCT/PRODUCT_VISION.md)

---

## 1. Product Mission

**Orbis Video Studio AI** is a cloud-first, provider-independent, multi-mode AI video production system that turns ideas, briefs, scripts, corporate documents, prompts, reference materials and imported media into complete high-quality videos.

The platform is structured-production-first rather than clip-centric. STORY mode retains the original narrative Story -> Script -> Scene -> Shot workflow, while SHORT, LOOP and SCENE modes intentionally allow lighter paths when a full Story/Script layer would be unnecessary.

---

## 2. Core Value Pillars

1. **Mode-Aware Structured Production** — STORY, SHORT, LOOP and SCENE share one production platform while using only the creative stages each mode needs.
2. **Reference-Driven Consistency** — Character, Location, Style, Brand and factual references remain consistent across generation.
3. **Hybrid Shot Flexibility** — AI generated shots can mix with imported video, images, recorded footage and stock assets.
4. **Cloud-First Accessibility** — Browser-based operation with no local GPU or local AI runtime dependency.
5. **Provider Independence** — Core Story/Scene/Shot/Timeline logic is isolated from Vidu and future providers by adapter boundaries.
6. **Asset Lock Protection** — Approved scripts, scenes, shots, characters, voices and timing can be protected against accidental overwrite.
7. **Selective Regeneration Safety** — Improve only selected unlocked or failed shots instead of recreating an entire project.
8. **Human Approval** — Final render remains gated by explicit human approval.
9. **Multi-Output Distribution** — One master project can produce 16:9, 9:16, 1:1 and other approved variants without rebuilding the project.
10. **Performance & Cost Discipline** — Prefer bounded deterministic processing, no duplicate chargeable jobs and no unnecessary heavy infrastructure.

---

## 3. Core V1 Video Modes

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready later modes:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Architecture readiness does not authorize implementation.

See [`VIDEO_PRODUCTION_MODES.md`](VIDEO_PRODUCTION_MODES.md) for canonical mode definitions.

---

## 4. Shared Production Mental Model

```text
Project
-> Video Mode
-> Purpose / Target Platform
-> Required creative structure only
-> Scenes / Shots
-> Reference Library
-> AI Generate and/or Import
-> Lock / QC / Selective Regeneration
-> Audio / Timeline as applicable
-> Human Approval
-> Cloud Render
-> Multi-Output Export
```
