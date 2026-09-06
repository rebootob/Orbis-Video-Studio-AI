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
PR: #29
Branch: ai/p2-wp011-batch-resume
Gate: WAITING CHATGPT INDEPENDENT RE-REVIEW (Review ID 5124507165 corrected)
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

## Scope Implemented in P2-WP011 (Including Review ID 5124507165 Corrective)

1. **Transactional Job + Batch Audit**:
   - Atomic savepoint (`begin_nested()`) wrapping `JobDispatchService.create_and_dispatch_job(..., commit=False)` and `BatchRunItem(decision="QUEUED")`.
   - Failure injection test proving failures between Job construction and audit persistence roll back atomically without unaudited queued work.
2. **Reconciliation / Cancellation Safety**:
   - `CANCELLING` treated as active/in-flight (`CandidateSkipReason.CANCELLATION_IN_PROGRESS`), blocking automatic regeneration.
   - `RECONCILIATION_REQUIRED` blocks automatic generation/resume/retry (`CandidateSkipReason.RECONCILIATION_REQUIRED`).
   - Single-shot create path fails closed with 409 for both states.
   - Status sets consistent across `BatchResumeService`, `JobDispatchService`, `GenerationJob` partial index, and migration `011_batch_resume_runs_and_indexes`.
3. **Real Bounded Processing**:
   - Evaluates -> persists `BatchRunItems` -> dispatches per bounded chunk (`EXECUTE_CHUNK_SIZE = 50`) without accumulating full-project candidate lists in memory.
   - Deterministic chunk ordering with stable tie-breaker: `(Scene.scene_number.asc(), Shot.shot_number.asc(), Shot.id.asc())`.
   - Zero N+1 queries in `list_project_batch_runs`: exactly 2 set-based queries execute regardless of run count.
   - Bounded items retrieval with pagination in `get_batch_run_details` (`item_limit`, `item_offset`).
4. **Truthful Run / UI Outcomes**:
   - BatchRun `failed_count` truthfully reflects dispatch failures and linked worker job failures.
   - Transactional active-job conflicts during dispatch are truthfully reported as `SKIPPED / ACTIVE_JOB_EXISTS` (not generic FAILED).
   - Frontend `handleBatchGenerateShots` strictly guards stage transition: does NOT switch project status to `VIDEO_IN_PROGRESS` when `queued_count == 0`.

---

## Next Allowed Action

1. Antigravity: STOP.
2. Push corrective commits to existing PR #29.
3. Wait for ChatGPT independent PASS re-review and explicit Owner approval.
4. Do not merge without approval.
5. Do not start WP012.
