# Product Vision & Core Mission

> **Canonical Document Location:** [`project-docs/30_PRODUCT/PRODUCT_VISION.md`](project-docs/30_PRODUCT/PRODUCT_VISION.md)

---

## 1. Product Mission

**Orbis Video Studio AI** is a cloud-first, provider-independent, multi-mode **AI Video Production Orchestrator / Production Control Plane** that turns ideas, briefs, scripts, corporate documents, prompts, references and imported media into complete high-quality videos.

Orbis should not rebuild foundation AI models when capable external services already exist. It coordinates Creative, Image, Video and Audio providers behind stable adapter boundaries while Orbis owns production state, workflow, approvals, history, cost control, QC, assembly and export.

The platform is structured-production-first rather than clip-centric. STORY mode retains the narrative Story -> Script -> Scene -> Shot path, while SHORT, LOOP and SCENE intentionally allow lighter paths when a full Story/Script layer would be unnecessary.

---

## 2. Core Value Pillars

1. **Automation-First Production** — AI performs repetitive planning/generation work; the user reviews, guides and approves rather than micromanaging every shot.
2. **Guided Flexibility** — always suggest the next sensible action, use safe defaults and progressive disclosure, while preserving expert control.
3. **Approval-Gated Cost Safety** — users can inspect Story, Storyboard and Shot Plan before expensive image/video generation.
4. **Multi-Project & Full History** — users can manage many projects and reopen historical versions without silent loss or destructive overwrite.
5. **Mode-Aware Structured Production** — STORY, SHORT, LOOP and SCENE share one production platform while using only the creative stages each mode needs.
6. **Reference-Driven Consistency** — Character, Location, Style, Brand and factual references remain consistent across generation.
7. **Provider Independence** — core production logic is isolated from OpenAI, Gemini, Vidu, Veo, TTS/music/SFX services and future vendors by adapter boundaries.
8. **Hybrid Shot Flexibility** — AI-generated shots can mix with imported video, images, recorded footage and stock assets.
9. **Lock / Version / Selective Regeneration Safety** — approved entities can be protected; revisions target selected unlocked work and preserve historical evidence.
10. **Durable Production Operations** — queue, retry, resume, reconciliation, idempotency and cost accounting must survive failures without duplicating paid work.
11. **Core V1 Audio Production** — VO, BGM, SFX, ambience and basic mixing/ducking are part of the end-to-end product, without turning Orbis into a full DAW.
12. **Human Final Authority** — final render remains gated by explicit human approval.
13. **Multi-Output Distribution** — one master project can produce 16:9, 9:16, 1:1 and other approved variants without rebuilding the project.
14. **Performance & Cost Discipline** — prefer bounded deterministic processing and avoid unnecessary infrastructure or generation.

---

## 3. Provider-Orchestration Model

```text
CreativeProvider
  -> OpenAI / Gemini / future

ImageProvider
  -> Gemini Image / OpenAI Image / future

VideoProvider
  -> Vidu / Veo / future

AudioProvider
  -> TTS / music / SFX / future
```

Provider capability may change over time. Orbis should survive vendor changes by keeping orchestration, state and workflow in the product core rather than scattering provider SDK calls through domain/UI code.

---

## 4. Core V1 Video Modes

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

## 5. Target Production Mental Model

```text
Project / Brief / References
-> Mode-Aware Creative Planning
-> Story or Concept as applicable
-> Review / Approve
-> Storyboard / Visual Plan
-> Review / Approve
-> Detailed Shot Plan + Prompts
-> Review / Approve
-> Images / Keyframes as applicable
-> Continuity QC
-> Video Generation and/or Imported Media
-> VO / BGM / SFX / Ambience
-> Auto Assembly / Simplified Timeline
-> Final QC
-> Human Approval
-> Cloud Render
-> Multi-Output Export
```

The user may pause, review, go back, regenerate selected items, restore prior versions and continue incomplete work. Full Auto can exist, but must never eliminate safe user control.

---

## 6. UX Principle

```text
Simple enough for first-time users
Powerful enough for advanced users
Consistent across every screen
Safe for costly AI actions
Beautiful but not distracting
```

The UI should feel like an AI producer/production assistant that knows the next sensible step without forcing the user through a rigid wizard.
