# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
```

Current status:

```text
P4-WP019 = PASS / CLOSED / MERGED
P4-WP020 = PROPOSED / NOT AUTHORIZED
CURRENT_GATE = POST-WP019 / READY FOR OWNER WP020 AUTHORIZATION DECISION
IMPLEMENTATION_AUTHORIZED = NONE
```

Canonical repository truth:

```text
Canonical branch: main
Canonical main HEAD: a09fcab835515679bf4f0bbfce8aec84f7e15062
P4-WP019 PR: #50 (MERGED / CLOSED)
P4-WP019 branch: ai/p4-wp019-orbis-archive
P4-WP019 final reviewed HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
P4-WP019 final review: PASS / READY FOR OWNER MERGE DECISION
P4-WP019 final review ID: 5135969695
P4-WP019 merge commit: a09fcab835515679bf4f0bbfce8aec84f7e15062
```

Execution roles:

```text
Owner = final human authority / authorization / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = STOP / NONE; bounded low-credit Execution Plane only when explicitly authorized
Codex = STOP
Claude Code = STOP
```

---

## P4-WP019 Closure

P4-WP019 is complete and must not be reopened without a proven regression.

Delivered and accepted scope:

1. `.orbis` ZIP-compatible archive package.
2. Canonical manifest/checksum trust root and canonical JSON.
3. Archive security validation and bounded extraction limits.
4. `FULL_SELF_CONTAINED` Core V1 archive contract.
5. Full project graph serialization and import.
6. CLONE import with fresh UUID/FK remapping and source lineage.
7. RESTORE import with collision-safe fail-closed semantics.
8. Phase-3 graph and referential-integrity preflight.
9. Asset completeness and payload/catalog/database size consistency.
10. Historical RenderJob/GenerationJob truth preservation with execution fencing.
11. Historical UsageLedger truth preservation, partial-index fencing and budget exclusion.
12. Transaction rollback and storage compensation.
13. API export/import endpoints.
14. Frontend Export/Import flow using the canonical Core V1 contract.

Final review evidence:

```text
Reviewed HEAD: df691035f54c1a9ffea4934b6f43134fde35d391
Review ID: 5135969695
Verdict: PASS / READY FOR OWNER MERGE DECISION
Backend CI: PASS — 412 passed, 2 skipped
Frontend CI: PASS — 52/52 tests; build PASS; lint 0 errors
PR #50 merge commit: a09fcab835515679bf4f0bbfce8aec84f7e15062
```

---

## Delivery Progress

```text
Completed work packages: 19 / 20
WP-count completion: 95%
Core V1 remaining package: P4-WP020 only
```

P4-WP020 is intended to cover End-to-End System Integration, UAT and Core V1 Release. Its implementation is **not authorized** by completion of P4-WP019.

---

## Next Allowed Action

Allowed without implementation authorization:

1. Maintain control-document truth.
2. Inspect current system/repository evidence for WP020 planning.
3. Define/verify P4-WP020 scope, UAT matrix, release gates and acceptance criteria.
4. Present the bounded P4-WP020 authorization contract to the Owner.

Not allowed:

- Do not start P4-WP020 code or test implementation until the Owner explicitly authorizes it.
- Do not silently expand WP020 into post-Core-V1 integrations.
- Do not reopen P4-WP019 absent a proven regression.
- Do not merge any future implementation without Owner approval.

---

## Locked Product Direction

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Architecture-ready later only:

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

Product locks remain:

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
HUMAN_REVIEW_NOT_HUMAN_MICROMANAGEMENT = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION_CORE_V1 = REQUIRED
PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
VENDOR_LOCK_IN = DISALLOWED
```
