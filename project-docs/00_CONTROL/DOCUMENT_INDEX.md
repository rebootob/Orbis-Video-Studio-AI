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
| Latest Routed Continuation Checkpoint | [`CONTINUATION_CHECKPOINT.md`](CONTINUATION_CHECKPOINT.md) |

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
| Historical P4-WP020 LIVE R4 C1 Vidu Failure/Billing Corrective | [`../40_DELIVERY/P4_WP020_LIVE_R4_C1.md`](../40_DELIVERY/P4_WP020_LIVE_R4_C1.md) |
| P4-WP020 LIVE R5 PRE1 Readiness Tooling | [`../40_DELIVERY/P4_WP020_LIVE_R5_PRE1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_PRE1.md) |
| P4-WP020 LIVE R5 VIDU1 Prep Tooling | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_PREP.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_PREP.md) |
| P4-WP020 LIVE R5 VIDU1 Workflow Guard Compatibility Corrective | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_COR1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_COR1.md) |
| P4-WP020 LIVE R5 VIDU1 HTTP Failure Diagnostics & Request Contract Corrective | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_C1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_C1.md) |
| P4-WP020 LIVE R5 VIDU1 C1 Post-Merge Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_C1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU1_C1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 Dedicated Probe Tooling | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PREP.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PREP.md) |
| P4-WP020 LIVE R5 VIDU2 PREP Post-Merge Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PREP_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PREP_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 PF1 Workflow Registration Corrective | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PF1_COR1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PF1_COR1.md) |
| P4-WP020 LIVE R5 VIDU2 PF1 Post-Run Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PF1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_PF1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 RUN1 Post-Run Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_RUN1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_RUN1_CLOSE.md) |
| P4-WP020 LIVE R5 FINAL-GAP1 Review | [`../40_DELIVERY/P4_WP020_LIVE_R5_FINAL_GAP1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_FINAL_GAP1.md) |
| P4-WP020 LIVE R5 FINAL-GAP1-CLOSE Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_FINAL_GAP1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_FINAL_GAP1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Prep Tooling | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_PREP.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_PREP.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Prep Post-Merge Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_PREP_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_PREP_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Readiness Review | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_READY1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_READY1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Runtime & Recovery Contract | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_CONTRACT1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_CONTRACT1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Contract Post-Merge Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_CONTRACT1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_CONTRACT1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate B Delivery Report | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_HARNESS1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_HARNESS1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Harness 1 Post-Merge Control Closure | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_HARNESS1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_HARNESS1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C Infrastructure Preflight Evidence | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PREFLIGHT1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PREFLIGHT1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C Infrastructure Verification Evidence | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_VERIFY1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_VERIFY1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C Infrastructure Verify Close | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_VERIFY1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_VERIFY1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C UAT Infrastructure Decision Record | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_UAT_INFRA_DECISION1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_UAT_INFRA_DECISION1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C UAT Infrastructure Decision Close | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_UAT_INFRA_DECISION1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_UAT_INFRA_DECISION1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C UAT Infrastructure Path A Read-Only Discovery | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PATHA_DISCOVERY1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PATHA_DISCOVERY1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C UAT Infrastructure Path A Discovery Close | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PATHA_DISCOVERY1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_PATHA_DISCOVERY1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C Owner/Admin Infrastructure Input | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_OWNER_ADMIN_INPUT1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_OWNER_ADMIN_INPUT1.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C Owner/Admin Infrastructure Input Close | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_OWNER_ADMIN_INPUT1_CLOSE.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_OWNER_ADMIN_INPUT1_CLOSE.md) |
| P4-WP020 LIVE R5 VIDU2 REC1 Gate C Local PC Infrastructure Design | [`../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_LOCALPC_DESIGN1.md`](../40_DELIVERY/P4_WP020_LIVE_R5_VIDU2_REC1_GATEC_INFRA_LOCALPC_DESIGN1.md) |
| WP Acceptance Criteria | [`../40_DELIVERY/ACCEPTANCE_CRITERIA.md`](../40_DELIVERY/ACCEPTANCE_CRITERIA.md) |
| Test / Provider Mock / UAT Strategy | [`../40_DELIVERY/TEST_UAT_STRATEGY.md`](../40_DELIVERY/TEST_UAT_STRATEGY.md) |
| Risk Register | [`../40_DELIVERY/RISKS_ISSUES.md`](../40_DELIVERY/RISKS_ISSUES.md) |
| Release Gates | [`../40_DELIVERY/RELEASE_GATES.md`](../40_DELIVERY/RELEASE_GATES.md) |
| WP007 Final Corrective Evidence | [`../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md`](../40_DELIVERY/WP007_FINAL_CORRECTIVE_EVIDENCE.md) |

P4-WP020 remains active and Owner-gated. R1/R2/R3/R4 are consumed immutable live histories. R4 stopped at Vidu after OpenAI and Gemini succeeded. `P4-WP020-LIVE-R4-C1`, C1-CLOSE, C1-CLOSE-R1, and BILL1-CLOSE are complete. P4-WP020-LIVE-R5-PRE1 and its closure gates are complete with zero provider generation calls. P4-WP020-LIVE-R5-VIDU1-PREP delivers dedicated 1-call probe tooling. P4-WP020-LIVE-R5-VIDU1-COR1 corrected workflow comments pagination. Live probe run `34423580310` was consumed (1 POST, HTTP_ERROR, credits UNKNOWN / NOT CONFIRMED). `P4-WP020-LIVE-R5-VIDU1-C1` delivers safe HTTP failure diagnostic metadata and request contract verification with zero provider calls.

`P4-WP020-LIVE-R5-VIDU2-REC1-PREP` is complete and merged via PR #103 at commit `7ff516f317f84278f6143f15cc58b91fd3fa34d5`. `P4-WP020-LIVE-R5-VIDU2-REC1-PREP-CLOSE` is complete and merged via PR #104 at commit `ea62dcb6db8c4a801429dd1d0cea8ad7fd13ae2c`. `P4-WP020-LIVE-R5-VIDU2-REC1-READY1` is complete and merged via PR #105 at commit `0326def88915b25fbb4e2b7019753c2b3fedc0f7`. `P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1` is complete and merged via PR #106 at commit `e09ee2127d0a20c01f6aad38eb759e5bfba7e248`. `P4-WP020-LIVE-R5-VIDU2-REC1-CONTRACT1-CLOSE` is complete and merged via PR #107 at commit `ed9f4baf1bfd73771ed6ba357dd1854a7d4ec0a7`. `P4-WP020-LIVE-R5-VIDU2-REC1-HARNESS1` (Gate B) is complete, Owner-approved, and merged via PR #108 at commit `b605a4d9928a7411a7f41cd7058d3a8fbceae581` (Final Review 5231880182: PASS). `P4-WP020-LIVE-R5-VIDU2-REC1-HARNESS1-CLOSE` is complete and merged via PR #109 at commit `79bf07cb7907b542d68871c7bc493e72d9562e8a`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PREFLIGHT1` is complete and merged via PR #110 at commit `ead14bf9d9b36958618d0f6d6531ff44b9506492`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-VERIFY1` is complete, Owner-approved, and merged via PR #111 at commit `da39e32c35b689ba2d2852c7f9b5ca7961a1d92c`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-VERIFY1-CLOSE` is complete and merged via PR #112 at commit `cb20631556bafdeaf17373fca3fd7ef8d9234c80`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1` is complete, Owner-approved, and merged via PR #113 at commit `71476a435013e78d0736cafc2af8c5cb6e27b5fe`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-UAT-INFRA-DECISION1-CLOSE` is complete, Owner-approved, and merged via PR #114 at commit `cefab1275bf8194f161f97b1a27f6bd50b129eee`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PATHA-DISCOVERY1` is complete, Owner-approved, and merged via PR #115 at commit `9b1cfe1ccff9c8b66be1b6c40fd3a64a7b971ad7`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PATHA-DISCOVERY1-CLOSE` is complete, Owner-approved, and merged via PR #116 at commit `92ce4665529cbe99ecb4c30cf28e59fd786b0599`. `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-OWNER-ADMIN-INPUT1` is complete, Owner-approved, and merged via PR #117 at commit `addf1db25bc8f197f215f24c937d89b66be08403`. Current active state is `ACTIVE_WORK_PACKAGE = NONE`, `ACTIVE_EXECUTION_PACKAGE = NONE`, `PACKAGE_STATUS = POST-MERGE CLOSED / COMPLETE`, `FINAL_RESULT = OWNER_ADMIN_INPUT_STILL_INCOMPLETE`, `CURRENT_GATE = Gate C Owner/Admin Infrastructure Input Required`, `NEXT_GATE = OWNER / ADMIN INFRASTRUCTURE INPUT DECISION`, `NEXT_CONTROL_DECISION = OWNER / ADMIN INFRASTRUCTURE INPUT REQUIRED`, `DISCOVERY_RESULT = OWNER_ADMIN_INPUT_REQUIRED`, `BIND1_ELIGIBILITY = NOT YET PROVEN`, `BIND1_STATUS = NOT AUTHORIZED`, `PROVISION1_STATUS = NOT AUTHORIZED`, `PATH_A_STATUS = OWNER-ADMIN INPUT STILL INCOMPLETE / BIND1 ELIGIBILITY NOT PROVEN`, `PATH_B_STATUS = PROPOSED / NOT AUTHORIZED`, `LAST_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-OWNER-ADMIN-INPUT1`, and `PREV_COMPLETED_GATE = P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-PATHA-DISCOVERY1-CLOSE`. Consumed runs `34423580310` (VIDU1) and `34569728383` (VIDU2) are permanently consumed and never rerun. Gate C Path A read-only discovery and Owner/Admin input are closed with Owner/Admin input still incomplete. BIND1 is NOT AUTHORIZED. PROVISION1 is NOT AUTHORIZED. REC1-RUN1 is BLOCKED / NOT AUTHORIZED / UNCONSUMED.

Authorized base main is `6a8c0d2b55c74163a16faa15a30fb693a6d19e24`. Canonical main must be fresh-fetched from repository truth. Active package is `P4-WP020-LIVE-R5-VIDU2-REC1-GATEC-INFRA-LOCALPC-DESIGN1` on branch `ai/p4-wp020-rec1-gatec-infra-localpc-design1`.

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
