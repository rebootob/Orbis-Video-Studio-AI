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

Product-wide locks currently include Multi-Project, Full History Retention, Automation-First, Approval-Gated Automation, Guided Flexibility, Core V1 Audio Production and Provider Independence. Their current execution/status interpretation is recorded in `CURRENT_STATE.md` and `ACTIVE_TASK.md`.

---

## 40_DELIVERY — Work Packages, QA & Delivery

| Topic / Responsibility | Canonical Document |
| :--- | :--- |
| Work Package Roadmap / Current WP Status | [`../40_DELIVERY/WORK_PACKAGES.md`](../40_DELIVERY/WORK_PACKAGES.md) |
| Historical P2-WP008 Proposal | [`../40_DELIVERY/P2_WP008_PROPOSAL.md`](../40_DELIVERY/P2_WP008_PROPOSAL.md) |
| Historical P3-WP017 Proposal | [`../40_DELIVERY/P3_WP017_PROPOSAL.md`](../40_DELIVERY/P3_WP017_PROPOSAL.md) |
| Historical P4-WP018 Proposal | [`../40_DELIVERY/P4_WP018_PROPOSAL.md`](../40_DELIVERY/P4_WP018_PROPOSAL.md) |
| Historical P4-WP019 Proposal | [`../40_DELIVERY/P4_WP019_PROPOSAL.md`](../40_DELIVERY/P4_WP019_PROPOSAL.md) |
| P4-WP020 E2E / UAT / Core V1 Release Proposal | [`../40_DELIVERY/P4_WP020_PROPOSAL.md`](../40_DELIVERY/P4_WP020_PROPOSAL.md) |
| P4-WP020 PRE1 Release Readiness Evidence | [`../40_DELIVERY/P4_WP020_PRE1_EVIDENCE.md`](../40_DELIVERY/P4_WP020_PRE1_EVIDENCE.md) |
| P4-WP020 S1 Bounded Corrective Plan | [`../40_DELIVERY/P4_WP020_S1_CORRECTIVE_PLAN.md`](../40_DELIVERY/P4_WP020_S1_CORRECTIVE_PLAN.md) |
| P4-WP020 LIVE Authorization Contract | [`../40_DELIVERY/P4_WP020_LIVE_AUTHORIZATION_CONTRACT.md`](../40_DELIVERY/P4_WP020_LIVE_AUTHORIZATION_CONTRACT.md) |
| P4-WP020 LIVE R2 C1 Corrective | [`../40_DELIVERY/P4_WP020_LIVE_R2_C1.md`](../40_DELIVERY/P4_WP020_LIVE_R2_C1.md) |
| P4-WP020 LIVE R3 PRE1 No-Paid Gate | [`../40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`](../40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md) |
| P4-WP020 LIVE R3 Proposed Resume Contract | [`../40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`](../40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md) |
| P4-WP020 LIVE R4 TOOL1 Contract | [`../40_DELIVERY/P4_WP020_LIVE_R4_TOOL1.md`](../40_DELIVERY/P4_WP020_LIVE_R4_TOOL1.md) |
| WP Acceptance Criteria | [`../40_DELIVERY/ACCEPTANCE_CRITERIA.md`](../40_DELIVERY/ACCEPTANCE_CRITERIA.md) |
| Test / Provider Mock / UAT Strategy | [`../40_DELIVERY/TEST_UAT_STRATEGY.md`](../40_DELIVERY/TEST_UAT_STRATEGY.md) |
| Risk Register | [`../40_DELIVERY/RISKS_ISSUES.md`](../40_DELIVERY/RISKS_ISSUES.md) |
| Release Gates | [`../40_DELIVERY/RELEASE_GATES.md`](../40_DELIVERY/RELEASE_GATES.md) |
| WP007 Final Corrective Evidence | [`../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md`](../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md) |

P4-WP020 remains active and Owner-gated. R1/R2/R3 are consumed immutable live histories. R4-PRE1 is closed PASS/NO-PAID. R4-TOOL1 is the current NO-PAID tooling package; it creates `LIVE-20260909-DE17-R4` tooling only and does not authorize provider generation or paid execution.

---

## Routing Rules

When a task affects project creation, Story/Storyboard/Shot routing, workflow, UI/UX, generation orchestration, selective/batch generation, timeline, QC, audio, render, export or archive portability, read at minimum:

1. `PRODUCT_VISION.md`
2. `VIDEO_PRODUCTION_MODES.md`
3. `USER_WORKFLOW.md`
4. the exact topic-specific document
5. the active GitHub Issue/PR contract, if one exists

For active work status, `CURRENT_STATE.md`, `ACTIVE_TASK.md` and live GitHub truth override stale historical proposal text.

Live repository truth newer than documentation remains authoritative for execution status.
