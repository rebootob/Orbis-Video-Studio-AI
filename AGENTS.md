# Orbis Video Studio AI — Agent Operating Policy

## Repository Authority

GitHub repository truth is authoritative.

Canonical branch: `main`.

`main` is protected by the active repository ruleset `Protect main`.

## Roles

- Owner = final human authority / UAT / merge approval
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = primary bounded Execution Plane when explicitly authorized
- Codex = STOP by default; use only for necessary local-only inspection, reproduction, or final verification that GitHub/Antigravity cannot perform efficiently
- Claude Code = STOP by default

## Mandatory Startup

Before project work:

1. Read this `AGENTS.md`.
2. Fresh-fetch live `main` and the active feature branch / PR.
3. Read `project-docs/00_CONTROL/START_HERE.md`.
4. Read `project-docs/00_CONTROL/CURRENT_STATE.md`.
5. Read `project-docs/00_CONTROL/ACTIVE_TASK.md`.
6. Read `project-docs/00_CONTROL/DOCUMENT_INDEX.md`.
7. Read `project-docs/00_CONTROL/CHAT_HANDOFF.md`.
8. Read only directly relevant routed documents and the exact active WP contract.

Repository truth newer than documentation is authoritative.

## Git Rules

- Never implement directly on `main`.
- Never force push `main`.
- Never delete `main`.
- One Work Package = one feature branch.
- One Work Package = one Pull Request.
- Corrective work stays on the same WP branch and PR.
- Do not create replacement PRs unless explicitly authorized.
- Do not merge without Owner approval.
- Do not start the next Work Package automatically.
- One writer per working tree. Do not run multiple implementation agents against the same checkout concurrently.
- Prefer a dedicated Git worktree for Antigravity when another local agent/tool may inspect the repository at the same time.

## CI / Merge Rules

- `backend-tests` is a required GitHub status check for PRs targeting `main`.
- Frontend changes must also pass `frontend-tests` whenever that workflow is present in the PR/repository.
- CI green is necessary but not sufficient: ChatGPT independent review must also be PASS before Owner merge approval.
- Unresolved review conversations must be resolved before merge.

## Low-Credit Execution Rules

Antigravity should handle bounded implementation, repetitive edits, focused tests, migration work, and corrective cycles.

During implementation/corrective rounds:
- run focused tests relevant to changed code
- avoid repeatedly running full regression suites
- do not expand scope

At the final gate:
- run required full regression once
- run required migration lifecycle once when schema changed
- run any environment-specific validation required by the WP

Codex should not duplicate Antigravity implementation/test loops by default.

## Completion

Execution agent must report:

- Work Package
- Issue / PR
- Branch
- Start HEAD
- End HEAD
- Files changed
- Tests run
- Test results
- CI status
- Scope deviations
- Blockers
- Ready for ChatGPT review

Antigravity output is evidence, not authority. Repository truth is authoritative.
