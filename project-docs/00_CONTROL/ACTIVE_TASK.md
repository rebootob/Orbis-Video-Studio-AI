# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Work Package ID:** P0-WP001
- **Title:** Project Governance & Architecture Documentation Foundation
- **Target Phase:** P0 — Foundation & Governance
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Create the initial project governance, architecture, product, and delivery documentation for **Orbis Video Studio AI** so future ChatGPT sessions and execution agents can continue from repository truth without losing scope or project state.

---

## Strictly Enforced Constraints

> [!CAUTION]
> **DOCUMENTATION-ONLY WORK PACKAGE**
> 
> The following actions are STRICTLY PROHIBITED in this Work Package:
> - Writing application code (frontend, backend, scripts, tools)
> - Implementing UI components or backend API endpoints
> - Provisioning cloud resources or databases
> - Making API calls to Vidu or any AI generation provider
> - Adding API keys, secrets, or cloud credentials
> - Deploying any services or infrastructure
> - Starting P0-WP002 or expanding project scope

---

## Required Deliverables

1. **Root Entry Point:**
   - [`README.md`](file:///c:/Users/allda/Desktop/Dev/git/Orbis%20Video%20Studio%20AI/README.md)
2. **00_CONTROL (Control Plane Docs):**
   - `START_HERE.md`, `CURRENT_STATE.md`, `ACTIVE_TASK.md`, `DOCUMENT_INDEX.md`, `CHAT_HANDOFF.md`
3. **10_GOVERNANCE (Governance Docs):**
   - `AUTHORITY_MODEL.md`, `SCOPE_LOCK.md`, `APPROVAL_POLICY.md`, `CHANGE_GOVERNANCE.md`, `AI_EXECUTION_POLICY.md`, `DECISION_LOG.md`
4. **20_ARCHITECTURE (Technical Architecture Docs):**
   - `SYSTEM_ARCHITECTURE.md`, `DOMAIN_MODEL.md`, `PROVIDER_ADAPTER_ARCHITECTURE.md`, `INTEGRATION_ARCHITECTURE.md`, `MULTI_OUTPUT_ARCHITECTURE.md`, `PORTABILITY_AND_MIGRATION.md`
5. **30_PRODUCT (Product & Domain Specs):**
   - `PRODUCT_VISION.md`, `V1_SCOPE.md`, `USER_WORKFLOW.md`, `STORY_SCRIPT_MODEL.md`, `REFERENCE_LIBRARY_MODEL.md`, `SCENE_SHOT_MODEL.md`, `AUDIO_EDITING_MODEL.md`, `OUTPUT_MODEL.md`
6. **40_DELIVERY (Delivery & QA Specs):**
   - `WORK_PACKAGES.md`, `ACCEPTANCE_CRITERIA.md`, `TEST_UAT_STRATEGY.md`, `RISKS_ISSUES.md`, `RELEASE_GATES.md`

---

## Stop Conditions & Handoff Protocol

Upon completing all documentation files:
1. Commit changes to branch `ai/p0-wp001-doc-foundation` with commit message:
   `docs: establish Orbis Video Studio AI governance and architecture foundation`
2. Push branch `ai/p0-wp001-doc-foundation` to origin.
3. Open a Pull Request targeting `main`.
4. **STOP.** Do NOT merge PR. Do NOT start P0-WP002.
5. Return PR details, branch name, HEAD SHA, created file list, and confirmation to Project Owner for ChatGPT independent review.
