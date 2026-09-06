# Master Document Index

> **Canonical Document Location:** [`project-docs/00_CONTROL/DOCUMENT_INDEX.md`](project-docs/00_CONTROL/DOCUMENT_INDEX.md)

This index routes each project topic to its canonical documentation source.

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
| AI Execution Policy | [`../10_GOVERNANCE/AI_EXECUTION_POLICY.md`](../10_GOVERNANCE/AI_EXECUTION_POLICY.md) |
| Architecture Decisions | [`../10_GOVERNANCE/DECISION_LOG.md`](../10_GOVERNANCE/DECISION_LOG.md) |

---

## 20_ARCHITECTURE — Technical Architecture

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Cloud System Architecture | [`../20_ARCHITECTURE/SYSTEM_ARCHITECTURE.md`](../20_ARCHITECTURE/SYSTEM_ARCHITECTURE.md) |
| Core Domain Model / Project-Scene-Shot State | [`../20_ARCHITECTURE/DOMAIN_MODEL.md`](../20_ARCHITECTURE/DOMAIN_MODEL.md) |
| Provider Adapter Boundary | [`../20_ARCHITECTURE/PROVIDER_ADAPTER_ARCHITECTURE.md`](../20_ARCHITECTURE/PROVIDER_ADAPTER_ARCHITECTURE.md) |
| External API/Webhook Integration | [`../20_ARCHITECTURE/INTEGRATION_ARCHITECTURE.md`](../20_ARCHITECTURE/INTEGRATION_ARCHITECTURE.md) |
| Multi-Output Rendering | [`../20_ARCHITECTURE/MULTI_OUTPUT_ARCHITECTURE.md`](../20_ARCHITECTURE/MULTI_OUTPUT_ARCHITECTURE.md) |
| Portability / Migration / DR | [`../20_ARCHITECTURE/PORTABILITY_AND_MIGRATION.md`](../20_ARCHITECTURE/PORTABILITY_AND_MIGRATION.md) |

Provider work must preserve separate Creative / Image / Video / Audio adapter boundaries as the product evolves. Core production state must not call provider SDKs directly.

---

## 30_PRODUCT — Product & Feature Models

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Product Vision / AI Production Orchestrator Direction | [`../30_PRODUCT/PRODUCT_VISION.md`](../30_PRODUCT/PRODUCT_VISION.md) |
| Video Production Modes | [`../30_PRODUCT/VIDEO_PRODUCTION_MODES.md`](../30_PRODUCT/VIDEO_PRODUCTION_MODES.md) |
| V1 Scope / Pass Criteria | [`../30_PRODUCT/V1_SCOPE.md`](../30_PRODUCT/V1_SCOPE.md) |
| End-to-End Guided / Approval-Gated Workflow | [`../30_PRODUCT/USER_WORKFLOW.md`](../30_PRODUCT/USER_WORKFLOW.md) |
| Story / Script Model | [`../30_PRODUCT/STORY_SCRIPT_MODEL.md`](../30_PRODUCT/STORY_SCRIPT_MODEL.md) |
| Reference Library Model | [`../30_PRODUCT/REFERENCE_LIBRARY_MODEL.md`](../30_PRODUCT/REFERENCE_LIBRARY_MODEL.md) |
| Scene / Shot / Hybrid / Lock Model | [`../30_PRODUCT/SCENE_SHOT_MODEL.md`](../30_PRODUCT/SCENE_SHOT_MODEL.md) |
| Core V1 Audio Production Model | [`../30_PRODUCT/AUDIO_EDITING_MODEL.md`](../30_PRODUCT/AUDIO_EDITING_MODEL.md) |
| Output / Aspect Ratio Model | [`../30_PRODUCT/OUTPUT_MODEL.md`](../30_PRODUCT/OUTPUT_MODEL.md) |

Product-wide locks currently include Multi-Project, Full History Retention, Automation-First, Approval-Gated Automation, Guided Flexibility, Core V1 Audio Production and Provider Independence. Their current execution/status interpretation is recorded in `CURRENT_STATE.md` and the active GitHub Issue/PR contract.

---

## 40_DELIVERY — Work Packages, QA & Delivery

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Work Package Roadmap / Current WP Status | [`../40_DELIVERY/WORK_PACKAGES.md`](../40_DELIVERY/WORK_PACKAGES.md) |
| Historical P2-WP008 Proposal | [`../40_DELIVERY/P2_WP008_PROPOSAL.md`](../40_DELIVERY/P2_WP008_PROPOSAL.md) |
| WP Acceptance Criteria | [`../40_DELIVERY/ACCEPTANCE_CRITERIA.md`](../40_DELIVERY/ACCEPTANCE_CRITERIA.md) |
| Test / Provider Mock / UAT Strategy | [`../40_DELIVERY/TEST_UAT_STRATEGY.md`](../40_DELIVERY/TEST_UAT_STRATEGY.md) |
| Risk Register | [`../40_DELIVERY/RISKS_ISSUES.md`](../40_DELIVERY/RISKS_ISSUES.md) |
| Release Gates | [`../40_DELIVERY/RELEASE_GATES.md`](../40_DELIVERY/RELEASE_GATES.md) |
| WP007 Final Corrective Evidence | [`../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md`](../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md) |

---

## Routing Rules

When a task affects project creation, Story/Storyboard/Shot routing, workflow, UI/UX, generation orchestration, selective/batch generation, timeline, QC, audio, render or export, read at minimum:

1. `PRODUCT_VISION.md`
2. `VIDEO_PRODUCTION_MODES.md`
3. `USER_WORKFLOW.md`
4. the exact topic-specific document
5. the active GitHub Issue/PR contract

For active work status, `CURRENT_STATE.md`, `ACTIVE_TASK.md` and live GitHub truth override stale historical proposal text.

Live repository truth newer than documentation remains authoritative for execution status.
