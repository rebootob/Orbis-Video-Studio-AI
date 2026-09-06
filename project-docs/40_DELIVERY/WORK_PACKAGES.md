# Work Package Roadmap

> **Canonical Document Location:** [`project-docs/40_DELIVERY/WORK_PACKAGES.md`](project-docs/40_DELIVERY/WORK_PACKAGES.md)

---

## 1. Roadmap Rule

Orbis Video Studio AI is delivered through discrete, bounded Work Packages. Every WP requires explicit Owner authorization before implementation. Completion of one WP never auto-authorizes the next.

One WP = one feature branch = one PR. Corrective work stays in the same branch/PR.

---

## 2. Completed Work

- **P0-WP001 — Project Governance & Architecture Documentation Foundation**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP002 — Backend Core Framework & Domain Database Setup**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP003 — S3 Object Storage & Asset Management API**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP004 — Document Ingestion & Text Extraction Engine**
  - **Status:** PASS / CLOSED / MERGED

- **P1-WP005 — Story & Screenplay Script Generator Service**
  - **Status:** PASS / CLOSED / MERGED

- **P2-WP006 — Reference Library & Character/Location Bibles**
  - **Status:** PASS / CLOSED / MERGED

- **P2-WP007 — Vidu Provider Adapter & Durable Job Dispatch Queue**
  - **Status:** PASS / CLOSED / MERGED
  - **PR:** #15

- **P2-WP008 — Hybrid Shot Engine, Asset Lock Machine & Base Video Modes**
  - **Status:** PASS / CLOSED / MERGED
  - **PR:** #19

- **P2-WP009 — Cost Control & Granular Usage Audit Ledger**
  - **Status:** PASS / CLOSED / MERGED
  - **PR:** #23
  - **Merge commit:** `9f094a5cbe9a4faeb5741231d0a819da0da283c1`

---

## 3. Active Work Package

### P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX

- **Issue:** #24
- **PR:** #25
- **Branch:** `ai/p2-wp010-mode-aware-web-workspace`
- **Initial reviewed HEAD:** `291ea773681831a0a68e585eb7e0664902102be3`
- **Current corrective HEAD:** `a687c7adca1bf204767410d51ef0e1cad3ee9436`
- **Status:** **CORRECTIVE PUSHED / WAITING CHATGPT INDEPENDENT RE-REVIEW**
- **CI at current HEAD:** backend-tests PASS, frontend-tests PASS

Initial review found blockers across history retention, staged review workflow, guided next action, multi-project completeness, real upload/reference UX, truthful history/audio/QC semantics, approval/status safety, cost-safe selected/batch generation, storyboard editing/autosave, provider neutrality, truthful progress/language/status and CORS.

Antigravity pushed corrective commit `a687c7ad...`. Those blockers are not considered closed until ChatGPT independently reviews the exact new HEAD.

Corrective/re-review MUST remain in the same WP010 branch and PR #25. Do not start WP011.

---

## 4. Remaining Roadmap

### Phase 2 — AI Generation & Production Pipeline

- **P2-WP011 — Selective Shot Regeneration Service**
  - **Status:** PROPOSED / NOT AUTHORIZED

### Phase 3 — Audio, Timeline Editing & Cloud Rendering

- **P3-WP012 — Audio Production & Voice Over / TTS Service**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P3-WP013 — Subtitle Generator & Auto-Ducking Processor**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P3-WP014 — Simplified Multi-Track Timeline Preview Engine**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P3-WP015 — Cloud FFmpeg Video Render Workers**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P3-WP016 — Human Approval Gates & QC Review Pipeline**
  - **Status:** PROPOSED / NOT AUTHORIZED

### Phase 4 — Multi-Output, Export & Core V1 Release

- **P4-WP018 — Multi-Output & Platform Export Presets**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P4-WP019 — Project Export/Import Archive Package (.orbis)**
  - **Status:** PROPOSED / NOT AUTHORIZED

- **P4-WP020 — End-to-End System Integration, UAT & Core V1 Release**
  - **Status:** PROPOSED / NOT AUTHORIZED

### Post-Core V1 / V1.x

- **P4-WP017 — Full Operational Integration Gateway (Hermes / n8n)**
  - **Status:** PROPOSED / POST-CORE V1 / V1.x

---

## 5. Repository Delivery Controls

- Root `AGENTS.md` routes all execution agents.
- `main` is protected by active ruleset `Protect main`.
- Required backend CI: `backend-tests`.
- Frontend-changing work must pass `frontend-tests` when present.
- ChatGPT independent review + Owner approval remain required even when CI is green.
- Merged head branches are auto-deleted.

---

## 6. Mode Expansion Rule

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready only until separately authorized:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Future-mode readiness must not silently expand an active WP.
