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
     - Archived shots/scenes -> `ARCHIVED`
     - Locked shots/scenes/scripts -> `LOCKED`
     - Non-generatable shots -> `NOT_GENERATABLE`
     - Completed jobs -> `ALREADY_COMPLETED`
     - Active jobs -> `ACTIVE_JOB_EXISTS`
     - Failed jobs without completed/active work -> `ELIGIBLE` for retry.
2. **Shot-Level Deduplication**:
   - Multiple failed jobs for one shot create at most ONE new retry job.
   - Repeated resume calls do not duplicate active work.
3. **Lightweight BatchRun Audit**:
   - `BatchRun` and `BatchRunItem` models and migration `011_batch_resume_runs_and_indexes.py`.
   - Records requested, eligible, queued, skipped counts with truthful skip reasons.
4. **Performance & Scalability Guardrails**:
   - Elimination of per-shot DB loops in candidate evaluation.
   - Added `ix_shots_scene_id` and `ix_generation_jobs_shot_status`.
5. **API & Frontend Integration**:
   - Endpoints `/projects/{project_id}/jobs/estimate`, `/batch`, `/resume`, `/batch-runs`.
   - Frontend `handleConfirmBatchGenerate` and `handleRetryFailed` wired to canonical endpoints.

---

## Next Allowed Action

1. Antigravity: STOP.
2. Open PR targeting `main`.
3. Do not merge without explicit Owner approval and ChatGPT independent PASS review.
4. Do not start WP012.
