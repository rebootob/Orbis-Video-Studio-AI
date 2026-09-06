# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
P2-WP009 — Cost Control & Granular Usage Audit Ledger
```

Status:

```text
IMPLEMENTED / WAITING CHATGPT INDEPENDENT REVIEW
```

Owner Authorization:
Authorized via GitHub Issue #22 on feature branch `ai/p2-wp009-cost-ledger`.

Execution Engine:
Antigravity (bounded execution complete; STOPPING for ChatGPT review).

### Objective

Build a provider-neutral, auditable usage and cost-control layer that records billable AI/provider activity per project/job/shot, prevents duplicate charging under retry/reconciliation flows, and enforces project-level budget controls before chargeable dispatch.

Scope Delivered:
1. Provider-neutral `UsageLedger` and `LedgerAdjustment` audit models with migration 009.
2. Idempotent recording of usage events, preventing duplicate charges across retries and reconciliations.
3. Pluggable `ProviderPricingService` registry without hard-coded pricing in core domain logic.
4. Project budget management: soft warning thresholds and fail-closed hard caps before chargeable dispatch.
5. Manual adjustment audit trail preserving original costs and reasons without overwriting history.
6. Summary and query endpoints grouping by provider and operation.

---

## Current Execution Roles

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Architect / Independent Reviewer
Antigravity = STOP until explicitly authorized for the next bounded implementation
Codex = STOP
Claude Code = STOP
```

The local GitHub watcher/dispatcher remains PAUSED and must not be treated as a production execution dependency.

---

## Next Allowed Action

Owner may review and explicitly authorize P2-WP008. Until then: documentation/review only, no WP008 application-code implementation.
