# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P2-WP012
```

Status:

```text
IMPLEMENTED / AWAITING CHATGPT INDEPENDENT REVIEW
```

Current Work Tracking:

```text
Active Package: P2-WP012 (Production Orchestrator & Staged Approval State Machine)
Issue: #31
PR: To be opened
Branch: ai/p2-wp012-production-orchestrator
Start HEAD: 3be8ffed28f8807ae89bab22fb64a8018a8fbdb7
Canonical main HEAD: 3be8ffed28f8807ae89bab22fb64a8018a8fbdb7
Gate: AWAITING CHATGPT INDEPENDENT REVIEW
```

Execution Roles:

```text
Owner = final human authority / authorization
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = Bounded Execution Plane
Codex = STOP
Claude Code = STOP
```

---

## P2-WP012 Delivery Evidence

1. **State Machine & Mode-Aware Orchestrator Service**:
   - `ProductionOrchestrator` service (`backend/app/services/production_orchestrator.py`) handles state evaluation, stage transitions, mode routing, and action execution.
   - Respects mode boundaries: `STORY` mode proceeds through Story -> Storyboard -> Shots -> Video -> Complete, while `SHORT`, `LOOP`, and `SCENE` modes bypass Story generation/approval and start directly at Storyboard or Shots without forced story constraints.
   - Idempotent execution and approval: Re-approving or executing on already matched stages returns clean `NO_OP` status without raising errors.

2. **Stage Approval & Generic PATCH Guard**:
   - Generic `PATCH /projects/{id}` endpoint strictly rejects client attempts to mutate `status` with HTTP 400 Bad Request, directing clients to the orchestrator.
   - Server-side dispatches (`resume_project_jobs` and `batch_generate_project_shots`) transition project status to `VIDEO_IN_PROGRESS` server-side and log orchestration audits.
   - Explicit `POST /projects/{id}/orchestration/approve` endpoint evaluates validity of requested stage transition, enforces prerequisites, and commits status change atomically.

3. **Append-Only Orchestration Audit Ledger**:
   - Reversible Alembic migration `012_production_orchestrator_and_staged_approvals.py` creates `orchestration_audits` table with indexed `(project_id, created_at)` and adds `automation_mode` to `projects`.
   - `OrchestrationAudit` model and endpoints (`GET /projects/{id}/orchestration/history`) record transition details: `from_status`, `to_status`, `action`, `trigger`, `actor`, `reason`, and JSON payload.

4. **Automation Modes (MANUAL, ASSISTED, AUTO)**:
   - `automation_mode` configurable via `PATCH /projects/{id}/orchestration/settings`.
   - `AUTO` mode automatically advances eligible automated stages (e.g., advancing to shot planning / storyboard creation) but strictly stops at mandatory human review gates (e.g. `STORY_GENERATED` awaiting `STORY_APPROVED`), hard budget limits, active jobs, or reconciliation requirements.

5. **Frontend Orchestration Integration**:
   - `AutomationBar` component renders automation mode selector (`MANUAL`, `ASSISTED`, `AUTO`), dynamic primary recommended action button, and blocked reasons alerts.
   - `QCHistoryPanel` displays full Orchestration Stage Transition Audit History and wires approval actions to `approveStage`.
   - Removed direct `api.updateProject(..., { status })` mutations in frontend, routing all workflow actions and approvals through orchestrator API endpoints.

---

## Next Allowed Action

1. Antigravity: STOP / NONE after PR creation.
2. Codex: STOP.
3. Claude Code: STOP.
4. Await ChatGPT Independent Review on PR for Issue #31.
5. Do NOT merge without Owner approval.
6. Do NOT start WP013.
