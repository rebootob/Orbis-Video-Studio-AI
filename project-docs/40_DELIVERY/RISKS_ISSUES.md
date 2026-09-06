# Risk Register & Issues Log

> **Canonical Document Location:** [`project-docs/40_DELIVERY/RISKS_ISSUES.md`](project-docs/40_DELIVERY/RISKS_ISSUES.md)

---

## 1. Current High-Priority Risks

| Risk ID | Risk Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R-01** | **Provider API / Capability Changes:** Vidu or other providers change request/response behavior or pricing/capabilities. | **HIGH** | Keep Creative/Image/Video/Audio providers behind adapters; core production state never depends on raw provider contracts. |
| **R-02** | **Provider Cost Overruns:** automation or accidental user actions trigger excessive paid generation. | **HIGH** | Project budgets, hard caps, soft warnings, known-cost confirmation, approval gates, Generate Selected / Continue Incomplete and idempotent durable jobs. |
| **R-03** | **Visual / Continuity Inconsistency:** character/location/style drifts across scenes/shots. | **HIGH** | Central Reference Library, locked bibles, reference priority rules, continuity QC before expensive video generation and selective regeneration. |
| **R-04** | **Silent History Loss:** edits/regeneration/hard-delete behavior destroys prior production evidence or approved versions. | **HIGH** | Full-history retention, audit/version lineage, archive over destructive deletion, locks and explicit restore/history UX. |
| **R-05** | **Automation Without Control:** Full Auto advances into expensive or incorrect downstream work before creative review. | **HIGH** | Approval-gated automation; allow review at Story / Storyboard / Shot Plan / Images / Final Review; Full Auto only by explicit user choice. |
| **R-06** | **User Confusion / Workflow Dead Ends:** a flexible system exposes too many controls or unclear next steps. | **HIGH** | Guided Flexibility, one clear Next Recommended Action, Simple/Advanced modes, contextual help, safe defaults and actionable error/empty states. |
| **R-07** | **Duplicate Billing / Retry Duplication:** retries or external agents create repeated chargeable jobs. | **HIGH** | DB-level idempotency/uniqueness, durable queue claim/fencing, retry/resume/reconciliation and external idempotency keys. |
| **R-08** | **Truthful UI Drift:** frontend claims QC/approval/audio/provider capability exists when only UI/readiness exists. | **MEDIUM-HIGH** | Product/UX truthfulness release gate; status must be backed by actual backend semantics or clearly labeled readiness/placeholder. |
| **R-09** | **Cloud Queue / Render Bottlenecks:** large batch/video render jobs degrade interactive UX. | **MEDIUM** | Background durable jobs, bounded polling, low-res/proxy preview where appropriate, continue-incomplete and independent render workers. |
| **R-10** | **CORS / Network Exposure:** permissive frontend/backend integration widens production attack surface. | **MEDIUM-HIGH** | Environment-specific allowed origins, proper auth/session policy, no wildcard credentials configuration in production. |
| **R-11** | **Editor Scope Creep:** product becomes a heavy Premiere/DAW clone and delays automation value. | **MEDIUM-HIGH** | Keep Core V1 editing simplified; prioritize orchestration, storyboard, batch generation, audio automation, QC, assembly and export. |
| **R-12** | **Provider Lock-In:** business logic becomes tied to one creative/image/video/audio vendor. | **HIGH** | Provider-neutral adapter/service boundaries and no direct provider SDK calls from core domain/UI. |

---

## 2. Current Open Delivery Issue

```text
P2-WP010 / PR #25
Reviewed HEAD: 291ea773681831a0a68e585eb7e0664902102be3
Status: CHANGES REQUIRED
```

Material open issues from independent review include:
- hard-delete/history conflict
- staged approval/guided workflow gaps
- incomplete multi-project lifecycle UX
- truthful QC/approval/audio readiness concerns
- placeholder reference upload concerns
- batch/cost safety gaps
- reorder/autosave/history-entry readiness gaps
- unsafe permissive CORS configuration

Antigravity corrective is authorized only on the existing WP010 branch/PR. The PR must be re-reviewed before merge.

---

## 3. Risk Handling Rule

A known risk does not automatically expand the active WP. Correct only risks that are blockers inside the authorized task contract; route larger follow-up work into separately proposed WPs and wait for Owner authorization.
