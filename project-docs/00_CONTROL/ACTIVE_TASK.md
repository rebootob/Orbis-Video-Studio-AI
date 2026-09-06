# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
```

Status:

```text
WP010 PASS / CLOSED / MERGED
CURRENT_GATE = OWNER DECISION FOR NEXT WORK PACKAGE
```

Last Completed Work Package:

```text
P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX
Issue: #24
PR: #25
Final Reviewed HEAD: 0f0a16fa95c8110bc8ab7a0c52d45351eaa82182
Merge Commit: 639e61fb69b6abee8598074add458035db906ceb
Final ChatGPT Independent Review: PASS / READY TO MERGE (Review ID 5124386306)
```

Execution Engine:

```text
Antigravity = STOP / NONE
Codex = STOP
Claude Code = STOP
```

No active execution engine is authorized for application-code implementation.

---

## Next Candidate Work Package (Proposed Only)

```text
P2-WP011 — Selective / Batch Regeneration & Resume Service
Status: PROPOSED / NOT AUTHORIZED
```

Do NOT implement WP011 without explicit Owner authorization.

### Planning Note for Future WP011 Consideration

`PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE`

For WP011 planning specifically consider:
- selective/batch operations must avoid unbounded loading
- avoid N+1 database behavior
- pagination/chunking for large job/shot sets
- required DB indexes for batch/resume paths
- bounded concurrency
- truthful progress for large batches
- performance/load regression tests

*(Do not implement these items during documentation closure).*

### Future-Performance Backlog Note (Preserved)

- server-side Project pagination
- Asset/Job history pagination
- media thumbnail/lazy-loading
- streaming/multipart large-file upload
- media preview streaming
- frontend virtualization where needed

---

## Current Execution Roles

```text
Owner = final human authority / UAT / next WP authorization
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = STOP / NONE
Codex = STOP by default
Claude Code = STOP
```

The local GitHub watcher/dispatcher remains PAUSED and must not be treated as a production execution dependency.

---

## Next Allowed Action

1. Keep WP001-WP010 closed unless a proven regression exists.
2. `ACTIVE_WORK_PACKAGE = NONE`.
3. Wait for Owner decision and authorization for the next Work Package.
4. Do not start WP011 or any later WP automatically.
