# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
P2-WP011 — Selective / Batch Regeneration & Resume Service + Performance & Scalability Guardrails
```

Status:

```text
AUTHORIZED / IMPLEMENTED / WAITING CHATGPT INDEPENDENT REVIEW
```

Current Work Tracking:

```text
Issue: #28
Branch: ai/p2-wp011-batch-resume
Gate: WAITING CHATGPT INDEPENDENT REVIEW
```

Execution Roles:

```text
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = STOP / WAITING REVIEW (bounded low-credit Execution Plane)
Codex = STOP
Claude Code = STOP
```

---

## Scope Implemented in P2-WP011

1. **Canonical Backend Batch / Resume Service (`BatchResumeService`)**:
   - Centralized candidate evaluation supporting `GENERATE_SELECTED`, `CONTINUE_INCOMPLETE`, `RETRY_FAILED`.
   - Set-based DB queries (no N+1 loops per shot).
   - Candidate rules enforce:
     - Archived shots/scenes -> `ARCHIVED` (including parent scenes marked archived)
     - Locked shots/scenes/scripts -> `LOCKED`
     - Non-generatable shots -> `NOT_GENERATABLE`
     - Completed jobs -> `ALREADY_COMPLETED`
     - Active jobs -> `ACTIVE_JOB_EXISTS`
     - Failed jobs without completed/active work -> `ELIGIBLE` for retry
     - Retry with no failure history -> `NO_FAILED_HISTORY`
     - Missing or cross-project requested shot IDs -> `NOT_FOUND`
   - Strict `BatchOperationType` enum validation; unknown operations fail closed with 400 Bad Request.
   - Bounded chunk pagination (`CHUNK_SIZE = 100`) for shot lookups and job status queries.
2. **Shot-Level Deduplication & Real Concurrency Fencing**:
   - Row-level lock on `Shot` during dispatch (`with_for_update()`).
   - Transactional re-check of active generation jobs in the same transaction.
   - Database-level partial unique index `uq_generation_jobs_active_shot` preventing duplicate concurrent active jobs.
   - Concurrency barrier test proving exactly one active job survives races across separate threads/sessions.
3. **Truthful BatchRun Lifecycle & Dynamic Count Reconciliation**:
   - `BatchRun` status lifecycle starts at `DISPATCHED` (or `PARTIAL_FAILED` / `FAILED` if dispatch errors occur).
   - Chunked dispatch execution (`EXECUTE_CHUNK_SIZE = 50`) with per-shot failure capture (`decision="FAILED"` with truthful reason).
   - Dynamic reconciliation of `completed_count` and `failed_count` on read from linked generation job statuses.
4. **API & Frontend Preview / Execute Equivalence**:
   - `/projects/{project_id}/jobs/estimate` accepts `operation_type` and enforces identical candidate selection rules as execution.
   - Bounded listing query for `/projects/{project_id}/batch-runs` with `limit` and `offset`.
   - Frontend `CostConfirmationModal` supports `operationType`, wiring both batch generation and `Retry Failed` through preview and confirmation.

---

## Next Allowed Action

1. Antigravity: STOP.
2. Open PR targeting `main`.
3. Do not merge without explicit Owner approval and ChatGPT independent PASS review.
4. Do not start WP012.
