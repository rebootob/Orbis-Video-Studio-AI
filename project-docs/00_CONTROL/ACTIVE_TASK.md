# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package Details

- **Work Package ID:** P0-WP001
- **Title:** Project Governance & Architecture Documentation Foundation (Corrective Iteration)
- **Target Phase:** P0 — Foundation & Governance
- **Authorized Agent:** Antigravity (Low-Credit / Bounded Execution Plane)
- **Authority / Oversight:** ChatGPT (Control Plane / Architect), Project Owner (Final Human Authority)

---

## Task Objectives

Correct and refine the initial project governance, architecture, product, and delivery documentation for **Orbis Video Studio AI** based on ChatGPT independent review findings:
1. Replace all local machine-specific links (`file:///c:/...`) with repository-relative Markdown links.
2. Update `CHAT_HANDOFF.md` to reflect actual post-PR state and remove stale pending action items.
3. Avoid premature technology lock-in by distinguishing REQUIRED CAPABILITY vs RECOMMENDED CANDIDATE vs TBD / NOT YET LOCKED.
4. Ensure V1 scope clarity while preserving integration-ready and multi-output-ready architectural design.

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
3. **STOP.** Do NOT merge PR `#1`. Do NOT start P0-WP002.
4. Return PR details, branch name, exact new HEAD SHA, files changed summary, and confirmation to Project Owner for ChatGPT review.
