# Master Document Index

> **Canonical Document Location:** [`project-docs/00_CONTROL/DOCUMENT_INDEX.md`](project-docs/00_CONTROL/DOCUMENT_INDEX.md)

This index routes each project topic to its canonical documentation source.

---

## Repository Root / Git Controls

| Topic / Responsibility | Canonical Source |
| :--- | :--- |
| Agent operating policy / Git execution rules | [`../../AGENTS.md`](../../AGENTS.md) |
| Backend required CI | [`../../.github/workflows/backend-tests.yml`](../../.github/workflows/backend-tests.yml) |
| Frontend CI (introduced by WP010) | [`../../.github/workflows/frontend-tests.yml`](../../.github/workflows/frontend-tests.yml) |
| Protected canonical branch | GitHub ruleset `Protect main` |

---

## 00_CONTROL — Project Control Plane

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Mandatory Startup Protocol | [`START_HERE.md`](START_HERE.md) |
| Real-time Project State | [`CURRENT_STATE.md`](CURRENT_STATE.md) |
| Active Work Package / Next Gate | [`ACTIVE_TASK.md`](ACTIVE_TASK.md) |
| Master Topic Routing Matrix | [`DOCUMENT_INDEX.md`](DOCUMENT_INDEX.md) |
| Chat Session Handoff | [`CHAT_HANDOFF.md`](CHAT_HANDOFF.md) |
| Copy/Paste Prompt for Next Chat | [`NEXT_CHAT_PROMPT.md`](NEXT_CHAT_PROMPT.md) |

---

## 10_GOVERNANCE — Project Governance & Rules

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Roles & AI/Human Authority | [`../10_GOVERNANCE/AUTHORITY_MODEL.md`](../10_GOVERNANCE/AUTHORITY_MODEL.md) |
| Scope Locks | [`../10_GOVERNANCE/SCOPE_LOCK.md`](../10_GOVERNANCE/SCOPE_LOCK.md) |
| Approval Gates | [`../10_GOVERNANCE/APPROVAL_POLICY.md`](../10_GOVERNANCE/APPROVAL_POLICY.md) |
| Documentation/RFC Change Rules | [`../10_GOVERNANCE/CHANGE_GOVERNANCE.md`](../10_GOVERNANCE/CHANGE_GOVERNANCE.md) |
| AI Execution / Low-Credit / Git Guardrails | [`../10_GOVERNANCE/AI_EXECUTION_POLICY.md`](../10_GOVERNANCE/AI_EXECUTION_POLICY.md) |
| Architecture Decisions | [`../10_GOVERNANCE/DECISION_LOG.md`](../10_GOVERNANCE/DECISION_LOG.md) |

---

## 20_ARCHITECTURE — Technical Architecture

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Cloud System Architecture | [`../20_ARCHITECTURE/SYSTEM_ARCHITECTURE.md`](../20_ARCHITECTURE/SYSTEM_ARCHITECTURE.md) |
| Core Domain Model | [`../20_ARCHITECTURE/DOMAIN_MODEL.md`](../20_ARCHITECTURE/DOMAIN_MODEL.md) |
| Provider Adapter / Vidu Boundary | [`../20_ARCHITECTURE/PROVIDER_ADAPTER_ARCHITECTURE.md`](../20_ARCHITECTURE/PROVIDER_ADAPTER_ARCHITECTURE.md) |
| External API/Webhook Integration | [`../20_ARCHITECTURE/INTEGRATION_ARCHITECTURE.md`](../20_ARCHITECTURE/INTEGRATION_ARCHITECTURE.md) |
| Multi-Output Rendering | [`../20_ARCHITECTURE/MULTI_OUTPUT_ARCHITECTURE.md`](../20_ARCHITECTURE/MULTI_OUTPUT_ARCHITECTURE.md) |
| Portability / Migration / DR | [`../20_ARCHITECTURE/PORTABILITY_AND_MIGRATION.md`](../20_ARCHITECTURE/PORTABILITY_AND_MIGRATION.md) |

---

## 30_PRODUCT — Product & Feature Models

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Product Vision & Core Principles | [`../30_PRODUCT/PRODUCT_VISION.md`](../30_PRODUCT/PRODUCT_VISION.md) |
| Video Production Modes | [`../30_PRODUCT/VIDEO_PRODUCTION_MODES.md`](../30_PRODUCT/VIDEO_PRODUCTION_MODES.md) |
| V1 Scope / Pass Criteria | [`../30_PRODUCT/V1_SCOPE.md`](../30_PRODUCT/V1_SCOPE.md) |
| End-to-End User Workflow | [`../30_PRODUCT/USER_WORKFLOW.md`](../30_PRODUCT/USER_WORKFLOW.md) |
| Story / Script Model | [`../30_PRODUCT/STORY_SCRIPT_MODEL.md`](../30_PRODUCT/STORY_SCRIPT_MODEL.md) |
| Reference Library Model | [`../30_PRODUCT/REFERENCE_LIBRARY_MODEL.md`](../30_PRODUCT/REFERENCE_LIBRARY_MODEL.md) |
| Scene / Shot / Hybrid / Lock Model | [`../30_PRODUCT/SCENE_SHOT_MODEL.md`](../30_PRODUCT/SCENE_SHOT_MODEL.md) |
| Audio / Subtitle / Ducking | [`../30_PRODUCT/AUDIO_EDITING_MODEL.md`](../30_PRODUCT/AUDIO_EDITING_MODEL.md) |
| Output / Aspect Ratio Model | [`../30_PRODUCT/OUTPUT_MODEL.md`](../30_PRODUCT/OUTPUT_MODEL.md) |

---

## 40_DELIVERY — Work Packages, QA & Delivery

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Work Package Roadmap / Current WP | [`../40_DELIVERY/WORK_PACKAGES.md`](../40_DELIVERY/WORK_PACKAGES.md) |
| Historical P2-WP008 Proposal | [`../40_DELIVERY/P2_WP008_PROPOSAL.md`](../40_DELIVERY/P2_WP008_PROPOSAL.md) |
| WP Acceptance Criteria | [`../40_DELIVERY/ACCEPTANCE_CRITERIA.md`](../40_DELIVERY/ACCEPTANCE_CRITERIA.md) |
| Test / Provider Mock / UAT Strategy | [`../40_DELIVERY/TEST_UAT_STRATEGY.md`](../40_DELIVERY/TEST_UAT_STRATEGY.md) |
| Risk Register | [`../40_DELIVERY/RISKS_ISSUES.md`](../40_DELIVERY/RISKS_ISSUES.md) |
| Release Gates / Required CI / Review | [`../40_DELIVERY/RELEASE_GATES.md`](../40_DELIVERY/RELEASE_GATES.md) |
| WP007 Final Corrective Evidence | [`../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md`](../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md) |
| Active WP010 Contract | GitHub Issue #24 |
| Active WP010 Delivery / Review | GitHub PR #25 |

---

## Routing Rule

When a task affects project creation, Story/Script routing, Scene/Shot behavior, workflow, UI, generation orchestration, timeline, or export logic, read `VIDEO_PRODUCTION_MODES.md` plus the exact active WP contract.

For active corrective work or re-review, also read the latest PR review comments and exact current diff before acting.

Live repository truth newer than documentation remains authoritative for execution status.
