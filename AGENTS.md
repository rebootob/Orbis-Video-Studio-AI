# Orbis Video Studio AI — Agent Operating Policy

## Repository Authority

GitHub repository truth is authoritative.

Canonical branch:

main

## Roles

- Owner = final human authority / UAT / merge approval
- ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
- Antigravity = bounded Execution Plane when explicitly authorized
- Codex = STOP by default; use only for necessary local inspection or validation
- Claude Code = STOP by default

## Mandatory Startup

Before project work, read:

1. project-docs/00_CONTROL/START_HERE.md
2. project-docs/00_CONTROL/CURRENT_STATE.md
3. project-docs/00_CONTROL/ACTIVE_TASK.md
4. project-docs/00_CONTROL/DOCUMENT_INDEX.md
5. project-docs/00_CONTROL/CHAT_HANDOFF.md

Fresh-fetch repository truth before stating status.

## Git Rules

- Never implement directly on main.
- Never force push main.
- Never delete main.
- One Work Package = one feature branch.
- One Work Package = one Pull Request.
- Corrective work stays on the same WP branch and PR.
- Do not create replacement PRs unless explicitly authorized.
- Do not merge without Owner approval.
- Do not start the next Work Package automatically.

## Execution Rules

Antigravity may implement only the explicitly authorized bounded Work Package.

During implementation:
- run focused tests
- avoid repeated full regression runs
- do not expand scope

At the final gate:
- run required full regression once
- run required migration validation once

## Completion

Execution agent must report:

- Work Package
- Branch
- Start HEAD
- End HEAD
- Files changed
- Tests run
- Test results
- Scope deviations
- Blockers
- PR
- Ready for ChatGPT review

Antigravity output is evidence, not authority.

Repository truth is authoritative.
