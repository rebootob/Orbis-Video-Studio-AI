# P2-WP008 Proposal — Hybrid Shot Engine, Asset Lock Machine & Base Video Mode Configuration

> Status: **PROPOSED / NOT AUTHORIZED**
>
> This document is planning only. It does not authorize implementation.

---

## 1. Objective

Build the provider-neutral production layer that lets Orbis combine generated and imported media safely while introducing the minimum domain/configuration support for multiple video production modes.

---

## 2. Proposed Scope

### A. Hybrid Shot Engine

Support shot source types:

```text
AI_GENERATED
IMPORTED_VIDEO
IMPORTED_IMAGE
RECORDED_FOOTAGE
STOCK_ASSET
MIXED
```

Requirements:
- one common Shot abstraction regardless of source
- source metadata separate from provider-specific configuration
- imported assets use existing Asset/storage boundaries
- generated assets continue through WP007 provider/queue boundaries
- no direct Vidu calls from Shot domain/service

### B. Asset Lock Machine

Provide explicit lock/unlock behavior for approved production entities.

Initial lock targets:

```text
SCRIPT
SCENE
SHOT
CHARACTER
LOCATION
VOICE
TIMING
```

Requirements:
- locked entities cannot be silently overwritten/regenerated
- unlock is explicit and auditable
- operations that would mutate locked dependencies fail closed
- locking must remain compatible with future selective regeneration

### C. Base Video Mode Configuration

Implement initial provider-neutral modes:

```text
STORY
SHORT
LOOP
SCENE
```

Minimum Project configuration:

```text
video_mode
purpose
target_platform
target_duration_seconds
preferred_aspect_ratio
mode_config
```

Rules:
- Story is optional at Project domain level
- STORY preserves existing Story -> Script -> Scenes -> Shots flow
- SHORT supports compact Hook/Concept -> Scene -> Shots flow
- LOOP may bypass Story and Script
- SCENE begins from one logical Scene and 1-N Shots
- Project -> Scene -> Shot configuration inheritance remains

---

## 3. Architecture-Ready, Not Implemented in WP008 Unless Separately Authorized

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

The schema/configuration design should remain extensible for these modes without implementing their dedicated workflows.

---

## 4. Integration Locks

WP008 must preserve:

- WP006 Reference Library / Character / Location / Style / Brand continuity
- WP007 provider adapter boundary
- WP007 durable generation queue, idempotency and reconciliation safety
- cloud-first architecture
- no local AI
- no vendor lock-in
- human approval architecture

---

## 5. Proposed Tests

- all hybrid source types validate correctly
- imported asset project ownership validation
- AI-generated shot dispatches only through provider-neutral generation service
- lock/unlock state transitions
- locked mutation/regeneration rejection
- project/scene/shot config inheritance
- STORY existing path regression
- SHORT can exist without Story
- LOOP can exist without Story/Script
- SCENE can exist without Story
- invalid/unsupported future mode rejected until enabled
- no Vidu-specific imports in core Shot/mode services
- full backend regression
- migration upgrade / downgrade -1 / upgrade if schema changes

---

## 6. Strictly Out of Scope

- PRODUCT / EXPLAINER / PRESENTER / MONTAGE dedicated workflows
- frontend workspace implementation (WP010)
- cost ledger (WP009)
- selective regeneration service (WP011)
- audio/TTS/subtitles
- timeline
- FFmpeg/cloud render
- live Vidu generation
- Redis/Celery
- n8n/Hermes operational gateway
- production deployment

---

## 7. Proposed Delivery Contract

If Owner authorizes WP008 later:

- create one bounded feature branch from fresh `main`
- one PR
- mocked provider behavior only
- minimum necessary migration(s)
- Antigravity as bounded execution plane unless Owner changes executor
- ChatGPT performs independent review
- no merge without Owner approval
- stop after WP008; do not auto-start WP009

---

## 8. Authorization Gate

Current state:

```text
P2-WP008 = PROPOSED / NOT AUTHORIZED
```

Required next action to start implementation:

```text
Explicit Owner authorization of the final WP008 scope.
```
