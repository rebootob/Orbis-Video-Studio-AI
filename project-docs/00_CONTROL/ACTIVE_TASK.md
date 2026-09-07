# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P3-WP016
```

Status:

```text
ACTIVE / AUTHORIZED
```

Current Work Tracking:

```text
Active Package: P3-WP016 (QC / Approval Pipeline)
Issue: #40
PR: To be opened
Branch: ai/p3-wp016-qc-approval
Start HEAD: a8eef74792f037466b5f366c76a961c1610a85da
Canonical main HEAD: a8eef74792f037466b5f366c76a961c1610a85da
Gate: IMPLEMENTATION / IN PROGRESS
```

Execution Roles:

```text
Owner = final human authority / authorization
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = Bounded Low-Credit Execution Plane (when authorized)
Codex = STOP
Claude Code = STOP
```

---

## Prior Deliveries: WP015 & WP014 Closure Truth

- **P3-WP015**: PASS / CLOSED / MERGED
  - Issue: #37
  - PR: #38
  - Reviewed HEAD: `640212f71182ba3f6a5024a442beb363868eabc1`
  - Merge commit: `35b31c3c41834209fcb9d63ad7ac52e9632d63d2`
  - Final Independent Review: PASS / READY TO MERGE (Review ID 5127082342)

- **P3-WP014**: PASS / CLOSED / MERGED
  - Issue: #35
  - PR: #36
  - Reviewed HEAD: `fb425feaec2dede3201e054d0b842b68820473d8`
  - Merge commit: `f50e2568d197b3c4bab5e4303f31af817db6e1bf`
  - Final Independent Review: PASS / READY TO MERGE

- **P2-WP013**: PASS / CLOSED / MERGED
  - Issue: #33
  - PR: #34
  - Reviewed HEAD: `f9fd46b917390224a5ab58bad0d3be238edbd7b3`
  - Merge commit: `c5412c7f3f45d11e27b5a9ac8d1567b8b098a0bd`
  - Final Independent Review: PASS / READY TO MERGE

---

## Next Allowed Action

1. `ACTIVE_WORK_PACKAGE = NONE`.
2. `CURRENT_GATE = POST-WP015 / READY FOR OWNER NEXT-WP AUTHORIZATION`.
3. Wait for explicit Owner authorization before starting P3-WP016 or any implementation work.
4. Antigravity: STOP / NONE.
5. Codex: STOP.
6. Claude Code: STOP.
7. Do NOT start WP016.
