# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
```

Status:

```text
WAITING OWNER NEXT-WORK-PACKAGE AUTHORIZATION
```

Current Work Tracking:

```text
Active Package: NONE
Last Completed: P2-WP011 (Selective / Batch Regeneration & Resume Service + Performance & Scalability Guardrails)
Issue: #28
PR: #29 (MERGED / CLOSED)
Branch: ai/p2-wp011-batch-resume (MERGED)
Reviewed HEAD: b2f349adb6d5704fa1aadfb19e06644b40a37080
Merge Commit: 643614b089a295ea96be179e470707609cbe4b53
Final Review: PASS / READY TO MERGE (Review ID 5124729394)
Canonical main HEAD: 643614b089a295ea96be179e470707609cbe4b53
Gate: WAITING OWNER NEXT-WORK-PACKAGE AUTHORIZATION
```

Execution Roles:

```text
Owner = final human authority / authorization of next WP
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = STOP / NONE (bounded low-credit Execution Plane when explicitly authorized)
Codex = STOP
Claude Code = STOP
```

---

## P2-WP011 Closure Evidence

1. **Transactional Job + Batch Audit Persistence**:
   - Savepoint-level isolation (`begin_nested()`) wrapping `JobDispatchService.create_and_dispatch_job(commit=False)` and `BatchRunItem(decision="QUEUED")`.
   - Durable consistency: GenerationJob, UsageLedger entry, and BatchRunItem persist atomically or roll back cleanly together without unaudited queued work.
2. **Reconciliation / Cancellation Safety**:
   - `CANCELLING` treated as active/in-flight (`CandidateSkipReason.CANCELLATION_IN_PROGRESS`), preventing duplicate generation.
   - `RECONCILIATION_REQUIRED` blocks automatic generation/resume/retry (`CandidateSkipReason.RECONCILIATION_REQUIRED`).
   - Single-shot create path fails closed with 409 for both states.
3. **Bounded Keyset Processing**:
   - Keyset pagination based on `(created_at, id)` snapshot boundary; eliminated unbounded in-memory candidate materialization.
   - Streaming execution in chunks of $\le 50$ (`EXECUTE_CHUNK_SIZE = 50`).
   - Set-based DB queries in `list_project_batch_runs` (0 N+1 queries).
   - Paginated item details in `get_batch_run_details` (`item_limit`, `item_offset`).
4. **Bounded Memory Retention & Truthful TOCTOU Boundary Enforcement**:
   - Legacy `/jobs/batch` enforces strict execution boundary $\le 100$ with atomic rollback and 400 Bad Request if $> 100$ jobs would be queued, preventing untracked active jobs.
   - `BatchResumeService.execute_batch` bounds compatibility `created_jobs` list via `MAX_COMPATIBILITY_RETURNED_JOBS = 100` and `accumulate_jobs=False` on canonical `/jobs/resume`, preventing unbounded ORM memory retention.
   - Canonical `/jobs/resume` relies truthfully on durable `BatchRun` and `BatchRunItem` records.
5. **Truthful Run / UI Outcomes & Stage Safety**:
   - BatchRun counters reconciled dynamically on read.
   - `handleBatchGenerateShots` strictly guards stage transition: does NOT switch project status to `VIDEO_IN_PROGRESS` when `queued_count == 0`.

---

## Next Allowed Action

1. Antigravity: STOP / NONE.
2. Codex: STOP.
3. Claude Code: STOP.
4. Wait for explicit Owner authorization of the next work package.
5. P2-WP012 remains: PROPOSED / NOT AUTHORIZED. Do NOT start or pre-authorize WP012.
