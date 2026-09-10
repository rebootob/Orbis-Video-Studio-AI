# P4-WP020-LIVE-R5-VIDU2-PF1-COR1 — NO-PAID Workflow Registration Corrective

## Status

```text
GATE: P4-WP020-LIVE-R5-VIDU2-PF1-COR1
TYPE: NO-PAID Workflow Registration Corrective
OWNER_AUTHORIZED: YES (Issue #63 comment 5620461587)
AUTHORIZED_BASE_MAIN: 8bc2765a8b09d93340c3aada4f7deff46dc29144
AUTHORIZED_BRANCH: ai/p4-wp020-live-r5-vidu2-pf1-cor1

BLOCKED_GATE: P4-WP020-LIVE-R5-VIDU2-PF1 (AUTHORIZED / BLOCKED BEFORE EXECUTION)
PF1_OWNER_AUTH: Issue #63 comment 5619653050

LAST_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU2-PREP-CLOSE (PR #97, commit 8bc2765a8b09d93340c3aada4f7deff46dc29144)
PREV_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU2-PREP (PR #96)
PREV2_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1-CLOSE (PR #95)
PREV3_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-C1 (PR #94)
PREV4_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-COR1 (PR #93)
PREV5_COMPLETED_GATE: P4-WP020-LIVE-R5-VIDU1-PREP (PR #92)
PREV6_COMPLETED_GATE: P4-WP020-LIVE-R5-PRE1-CLOSE-R1 (PR #91)

COR1_PROVIDER_GENERATION_CALLS: 0
COR1_PAID_PROVIDER_CALLS: 0
COR1_VIDU_GENERATION_POSTS: 0
COR1_VIDU_CREDITS_CONSUMED: 0
COR1_PAID_FENCE_WRITTEN: false
COR1_PAID_LIVE_DISPATCH: false
CORE_V1_RELEASE: NOT DECLARED
```

## Historical Blocker & Diagnosed Defect

When Owner authorized PF1 dry-run execution on canonical main `8bc2765a8b09d93340c3aada4f7deff46dc29144`, workflow dispatch failed with:
```text
could not create workflow dispatch event: HTTP 422: Workflow does not have 'workflow_dispatch' trigger
```
GitHub Actions push validation on merge commit `8bc2765a8b09d93340c3aada4f7deff46dc29144` also failed immediately:
```text
Run 34483378872: event=push, conclusion=failure, jobs=0
```

### Root Cause Diagnosis

In `.github/workflows/wp020-live-r5-vidu2.yml` lines 76–77 and 81–82:
```yaml
if ! printf '%s
' "${COMMENTS}" | grep -Fx "${AUTH_MARKER}" >/dev/null; then
...
if printf '%s
' "${COMMENTS}" | grep -Fx "${FENCE_MARKER}" >/dev/null; then
```
Unintended literal newlines were inserted into `printf '%s\n'`, causing line 77 and line 82 to begin at column 1 without step block indentation.
This caused a YAML parsing syntax error:
```text
yaml.scanner.ScannerError: while scanning a simple key in ".github/workflows/wp020-live-r5-vidu2.yml", line 77, column 1 could not find expected ':' in line 81
```
Because the workflow file was syntactically invalid YAML, GitHub Actions could not parse the workflow schema or register the `workflow_dispatch` trigger.

## Delivered Corrective Changes

1. **Workflow Syntax Repair (`.github/workflows/wp020-live-r5-vidu2.yml`)**:
   - Replaced broken split statements with valid single-line `printf '%s\n' "${COMMENTS}" | grep -Fx "${AUTH_MARKER}" >/dev/null`.
   - Preserved all live safety fences, authentication marker verification, pagination, and failure reporting.
   - Validated complete YAML schema and parse tree using `yaml.safe_load`.
2. **Contract Test Suite Extension (`backend/tests/test_wp020_live_r5_vidu2_contract.py`)**:
   - Added automated test `test_req_w_workflow_yaml_syntax_and_registration_validity` asserting:
     - Workflow YAML parses cleanly into a mapping.
     - Name is `WP020 LIVE R5 Vidu2 1-Call Probe`.
     - `workflow_dispatch` trigger is registered with `mode` input choice (`dry-run`, `live`, default `dry-run`).
     - Zero `push`, `pull_request`, or `schedule` triggers exist.
3. **Safety Invariants**:
   - Zero provider calls.
   - Zero generation POSTs.
   - No paid authorization marker written.
   - No execution fence written.
   - Zero credits consumed by COR1.

## PF1 Authorization Expiry & Post-Merge Rule

PF1 Owner authorization (Issue #63 comment `5619653050`) was strictly bound to canonical base main SHA `8bc2765a8b09d93340c3aada4f7deff46dc29144`.

After PR #98 (COR1) merges to `main`, canonical `main` will advance to a NEW merge commit SHA.

**Authorization Expiry Rule**:
- The old PF1 authorization comment `5619653050` **MUST NOT BE REUSED** on post-COR1 canonical `main`.
- A fresh explicit Owner PF1 authorization bound to the new exact post-merge canonical `main` SHA is strictly required before any dry-run dispatch.
- This is a NO-PAID authorization refresh rule; it does NOT authorize paid or live execution.
