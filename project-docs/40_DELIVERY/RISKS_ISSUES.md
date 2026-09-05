# Risk Register & Issues Log

> **Canonical Document Location:** [`project-docs/40_DELIVERY/RISKS_ISSUES.md`](project-docs/40_DELIVERY/RISKS_ISSUES.md)

---

## 1. Initial Risk Assessment Matrix

```
  High  │ [R-02] Provider Cost Overruns   │ [R-01] Vidu API Breaking Changes
        │                                  │
Impact  │ [R-04] Integration Duplication   │ [R-03] Visual Inconsistency
        │                                  │
  Low   │ [R-05] Cloud Queue Bottlenecks   │
        └──────────────────────────────────┴───────────────────────────────
                       Low                               High
                                   Probability
```

---

## 2. Risk Register & Mitigation Strategies

| Risk ID | Risk Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R-01** | **Vidu API Breaking Changes:** Vidu updates request parameters or deprecates endpoints. | **HIGH** | Encapsulate Vidu logic entirely inside `ViduProviderAdapter`. Domain model and UI never touch raw Vidu APIs. |
| **R-02** | **Provider Cost Overruns:** Automated loops or accidental user actions trigger massive AI generation bills. | **HIGH** | Enforce configurable budget safety caps, cost threshold human approval gates, and pre-generation cost confirmation. |
| **R-03** | **Shot-to-Shot Visual Inconsistency:** Generated character appearance shifts across sequential shots. | **HIGH** | Inject Character Bible turnaround images into Vidu adapter payloads; enforce seed retention and asset lock protection. |
| **R-04** | **Integration Retry Duplicate Billing:** Network retries from external agents (Hermes/n8n) trigger duplicate generation jobs. | **MEDIUM** | Enforce mandatory `X-Idempotency-Key` header on all API gateway mutation endpoints. |
| **R-05** | **Cloud Rendering Bottlenecks:** Heavy video compositing jobs stall user preview workflows. | **LOW** | Offload video compositing to asynchronous cloud render worker pools; render low-res proxies for browser timeline preview. |
