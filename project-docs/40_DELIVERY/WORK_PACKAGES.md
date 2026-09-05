# Work Package Roadmap

> **Canonical Document Location:** [`project-docs/40_DELIVERY/WORK_PACKAGES.md`](project-docs/40_DELIVERY/WORK_PACKAGES.md)

---

## 1. Roadmap Overview

The delivery of Orbis Video Studio AI is structured into discrete, sequential **Work Packages (WPs)**. Each Work Package defines a self-contained scope, strict deliverables, acceptance criteria, and stop conditions.

> [!IMPORTANT]
> **PROPOSAL STATUS NOTICE**
> 
> Work Packages beyond **P0-WP001** are PROPOSED roadmap items. Technology selections and frameworks listed in proposed WPs are **candidate tech stacks (TBD)** and MUST be formally authorized by the Project Owner prior to execution.

---

## 2. Work Package Master Breakdown

```mermaid
graph TD
    P0["P0: Foundation & Governance (P0-WP001)"] --> P1["P1: Core Architecture & Data Engine (P1-WP002 to P1-WP005)"]
    P1 --> P2["P2: Generation & Production Pipeline (P2-WP006 to P2-WP011)"]
    P2 --> P3["P3: Audio, Editing & Cloud Render (P3-WP012 to P3-WP016)"]
    P3 --> P4["P4: Multi-Output, Export & Core V1 Release (P4-WP018 to P4-WP020)"]
    P4 -.-> P1x["POST-CORE V1 / V1.x: Integration Gateway Expansion (P4-WP017)"]
```

---

## 3. Work Package Registry

### Phase 0 — Foundation & Governance
- **`P0-WP001` — Project Governance & Architecture Documentation Foundation**
  - **Status:** **ACTIVE / CORRECTIVE REVIEW**
  - **Scope:** Establish canonical governance, system architecture, product specs, and delivery docs. Zero application code.

### Phase 1 — Core Architecture & Data Engine
- **`P1-WP002` — Backend Core Framework & Domain Database Setup**
  - **Scope:** Backend API framework setup, persistent relational database migrations, domain schemas, container environment setup. *(Tech choice: TBD)*
- **`P1-WP003` — S3 Object Storage & Asset Management API**
  - **Scope:** S3-compatible storage adapter, file upload pipeline, media asset metadata service.
- **`P1-WP004` — Document Ingestion & Text Extraction Engine**
  - **Scope:** Implement PDF, Word (.docx), PowerPoint (.pptx), and brief text parsers.
- **`P1-WP005` — Story & Screenplay Script Generator Service**
  - **Scope:** Story outline generator, screenplay formatter, scene/shot parser.

### Phase 2 — AI Generation & Production Pipeline
- **`P2-WP006` — Reference Library & Character/Location Bibles**
  - **Scope:** Reference asset CRUD service, visual similarity tagging, prompt reference injector.
- **`P2-WP007` — Vidu Provider Adapter & Job Dispatch Queue**
  - **Scope:** Implement `IVideoGenerationProviderAdapter` for Vidu (V1 default), durable async worker queue, retry handler.
- **`P2-WP008` — Hybrid Shot Engine & Asset Lock Machine**
  - **Scope:** Hybrid shot import (video, image, recorded, stock), granular entity locking state machine.
- **`P2-WP009` — Cost Control & Granular Usage Audit Ledger**
  - **Scope:** Budget cap guards, provider job usage logging, cost audit API needed for generation safety.
- **`P2-WP010` — Web Workspace UI: Storyboard & Shot Grid**
  - **Scope:** Browser UI workspace for project creation, document upload, script editor, and shot grid. *(Tech choice: TBD)*
- **`P2-WP011` — Selective Shot Regeneration Service**
  - **Scope:** Target shot selection, lock validation guard, selective provider dispatch.

### Phase 3 — Audio, Timeline Editing & Cloud Rendering
- **`P3-WP012` — Audio Production & Voice Over / TTS Service**
  - **Scope:** Multi-stem audio track manager, TTS dubbing integration, SFX/BGM assignment.
- **`P3-WP013` — Subtitle Generator & Auto-Ducking Processor**
  - **Scope:** SRT/VTT auto-generation, sidechain audio ducking algorithm implementation.
- **`P3-WP014` — Simplified Multi-Track Timeline Preview Engine**
  - **Scope:** Browser timeline UI, shot trimming, track syncing, real-time preview player.
- **`P3-WP015` — Cloud FFmpeg Video Render Workers**
  - **Scope:** Scalable cloud render worker pool, FFmpeg multi-track compositing, watermark overlay.
- **`P3-WP016` — Human Approval Gates & QC Review Pipeline**
  - **Scope:** Cost threshold approval gates, preview watermark player, human sign-off state machine.

### Phase 4 — Multi-Output, Export & Core V1 Release
- **`P4-WP018` — Multi-Output & Platform Export Presets**
  - **Scope:** Presets for 16:9, 9:16, 1:1, smart subject cropping, subtitle burning profiles.
- **`P4-WP019` — Project Export/Import Archive Package (.orbis)**
  - **Scope:** ZIP package exporter/importer, metadata validation, disaster recovery scripts.
- **`P4-WP020` — End-to-End System Integration, UAT & Core V1 Release**
  - **Scope:** Complete Core V1 PASS checklist validation, end-to-end UAT sign-off, production release tag.

### Post-Core V1 / V1.x — Integration Expansion
- **`P4-WP017` — Full Operational Integration Gateway (Hermes / n8n)**
  - **Status:** **POST-CORE V1 / V1.x (Architecture Ready in V1)**
  - **Scope:** Full operational integration gateway connectors, external agent automation hooks, webhook dispatchers. Architecture readiness (REST boundaries, auth, permissions, audit, idempotency) is maintained in V1.
