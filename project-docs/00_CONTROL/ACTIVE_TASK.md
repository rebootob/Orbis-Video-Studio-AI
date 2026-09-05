# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Work Package ID:** P0-WP001
- **Title:** Project Governance & Architecture Documentation Foundation (Final Corrective Iteration)
- **Target Phase:** P0 — Foundation & Governance
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Correct and refine the initial project governance, architecture, product, and delivery documentation for **Orbis Video Studio AI** based on final ChatGPT review findings:
1. **Fix Handoff HEAD Semantics:** Replace self-invalidating "Current HEAD SHA" concept with `HANDOFF_BASE_SHA` (the repository SHA current immediately before handoff update commit) and establish explicit live HEAD authority rules.
2. **Fix V1 Integration Scope Contradiction:** Maintain Integration Architecture (REST/API boundary, webhooks, auth, permissions, audit, idempotency) as a LOCKED architectural requirement for V1 design, while explicitly clarifying that full operational Hermes/n8n Integration Gateway implementation is POST-CORE V1 / V1.x.

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
> - Merging PR `#1` or starting P0-WP002

---

## Required Deliverables

1. **Root Entry Point:** [`README.md`](README.md)
2. **00_CONTROL:** `START_HERE.md`, `CURRENT_STATE.md`, `ACTIVE_TASK.md`, `DOCUMENT_INDEX.md`, `CHAT_HANDOFF.md`
3. **10_GOVERNANCE:** `AUTHORITY_MODEL.md`, `SCOPE_LOCK.md`, `APPROVAL_POLICY.md`, `CHANGE_GOVERNANCE.md`, `AI_EXECUTION_POLICY.md`, `DECISION_LOG.md`
4. **20_ARCHITECTURE:** `SYSTEM_ARCHITECTURE.md`, `DOMAIN_MODEL.md`, `PROVIDER_ADAPTER_ARCHITECTURE.md`, `INTEGRATION_ARCHITECTURE.md`, `MULTI_OUTPUT_ARCHITECTURE.md`, `PORTABILITY_AND_MIGRATION.md`
5. **30_PRODUCT:** `PRODUCT_VISION.md`, `V1_SCOPE.md`, `USER_WORKFLOW.md`, `STORY_SCRIPT_MODEL.md`, `REFERENCE_LIBRARY_MODEL.md`, `SCENE_SHOT_MODEL.md`, `AUDIO_EDITING_MODEL.md`, `OUTPUT_MODEL.md`
6. **40_DELIVERY:** `WORK_PACKAGES.md`, `ACCEPTANCE_CRITERIA.md`, `TEST_UAT_STRATEGY.md`, `RISKS_ISSUES.md`, `RELEASE_GATES.md`

---

## Stop Conditions & Handoff Protocol

Upon completing all documentation corrections:
1. Commit changes to branch `ai/p0-wp001-doc-foundation`.
2. Push branch to origin PR `#1`.
3. **STOP.** Do NOT merge PR `#1`. Do NOT start P0-WP002. Do NOT attempt to create recursive commits to embed the new commit's own SHA into itself.
4. Report PR details, branch name, exact new HEAD SHA externally to Project Owner for ChatGPT review.
