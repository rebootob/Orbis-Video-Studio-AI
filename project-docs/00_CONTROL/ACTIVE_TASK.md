# Active Task Specification

> **Canonical Document Location:** [`project-docs/00_CONTROL/ACTIVE_TASK.md`](project-docs/00_CONTROL/ACTIVE_TASK.md)

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP019
```

Status:

```text
P4-WP019 IN PROGRESS / CHANGES REQUIRED
```

Current Work Tracking:

```text
Active Package: P4-WP019
Status: IN_PROGRESS / CHANGES REQUIRED
Canonical main HEAD: 5f3ccbbcd0ee528bb85501a32efb64c5b13fbce5
Branch: ai/p4-wp019-orbis-archive
PR: #50
Reviewed HEAD: 59596c0e21c6d685a160742fd498128a53b4682b
Latest Independent Review: Review ID 5135776036 (CHANGES REQUIRED)
Latest PR commit: 632f70e9159413cb36ea4f767318c605c45497d1
Gate: P4-WP019 / CORRECTIVE REQUIRED BEFORE MERGE
Implementation Authorized: YES
P4-WP020: PROPOSED / NOT AUTHORIZED
```

Execution Roles:

```text
Owner = final human authority / authorization / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane (STOP / NONE after doc sync)
Codex = STOP
Claude Code = STOP
```

---

## Prior Deliveries: WP018, WP017, WP016, WP015 & WP014 Closure Truth

- **P4-WP018**: PASS / CLOSED / MERGED
  - PR: #47
  - Branch: `ai/p4-wp018-multi-output-export-presets`
  - PRE1 Reviewed HEAD: `f51694643596acba54447cc0ab36bc8cbfd8dfd5`
  - PRE1 Merge commit: `96d53c30f0344dc84bb3d9205e5b7bbbde94885b`
  - Implementation Reviewed HEAD: `fd745def2235fdaa6accf82ea2cb037a4fa42390`
  - Merge commit: `09e62876543ee7990919beb43600a1c748be545d`
  - Final Independent Review: PASS / READY FOR OWNER MERGE DECISION (Review ID 5132040630)
  - Delivered Scope: Multi-output export presets (16:9, 9:16, 1:1), resolution/bitrate/quality presets, platform-oriented presets, RenderBatch grouping, durable render_variant_key, variant-aware idempotency, atomic batch budget authorization, immutable preset snapshot, WP017 worker reuse, FFmpeg output transformation, export Asset lineage, migration upgrade/downgrade safety, concurrent budget safety, full history retention.

- **P3-WP017**: PASS / CLOSED / MERGED
  - PR: #44
  - Branch: `ai/p3-wp017-cloud-render-workers`
  - Starting HEAD: `556ca1c2566c154e5f10559e74907896bbf3b797`
  - Reviewed HEAD: `72d842936a7812aabec8df6b948930a0e296a553`
  - Merge commit: `72065b9c29350e54dd7811a00d7198c6765004d1`
  - Final Independent Review: PASS / READY FOR OWNER MERGE DECISION (Review ID 5129832936)

- **P3-WP016**: PASS / CLOSED / MERGED
  - Issue: #40
  - PR: #41
  - Branch: `ai/p3-wp016-qc-approval`
  - Reviewed HEAD: `5def41c8bba9b3004b7007f671899e045438a8c4`
  - Merge commit: `43e5221e7f39a19e8c6fde54c450324aa8333059`
  - Final Independent Review: PASS / READY TO MERGE (Review ID 5127769635)

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

## P4-WP019 Implementation & Review History

### Delivered Scope (PR #50)
1. `.orbis` ZIP-compatible container subsystem with POSIX path safety.
2. Canonical manifest & checksum design (`checksums.sha256` root trust, canonical RFC 8785 JSON).
3. Archive security validation (Zip Slip, bomb decompression ratio, size limits, absolute/UNC path guards).
4. Project graph export/import with full entity coverage.
5. `FULL_SELF_CONTAINED` asset packaging.
6. CLONE mode (fresh UUID remap, storage re-upload, source lineage).
7. RESTORE mode (original identity, fail-closed collision detection).
8. Phase-3 canonical in-memory preflight validation (`ArchivePreflightValidator`).
9. Historical execution fencing (`imported_historical = True`, `execution_disabled = True`, worker lease clearing).
10. RenderJob / GenerationJob active partial unique-index separation.
11. UsageLedger imported historical financial fencing.
12. Budget service exclusion of imported historical spend.
13. REST API endpoints (`/export`, `/import/validate`, `/import/execute`).
14. Frontend Export and Import modals integrated into `ProjectDashboard`.
15. Extensive archive, security, migration, and regression test suites.

### Review Blockers & Resolution
- **Initial Review (5133420916)**: Historical truth mutation, missing Phase-3 graph preflight, asset completeness -> Addressed at HEAD `59596c0e21c6d685a160742fd498128a53b4682b`.
- **Latest Review (5135776036 - CHANGES REQUIRED)**:
  1. *Migration 020 fail-closed downgrade*: Precheck UsageLedger `(provider, provider_event_id)` collisions before any schema change.
  2. *Archive self-consistency*: Enforce `FULL_SELF_CONTAINED`, disallow `include_renders=False`, assert `actual_size == catalog size_bytes == Asset.file_size_bytes`.
  - Delivered in commit `632f70e9159413cb36ea4f767318c605c45497d1` with 412 backend tests and 52 frontend tests passing.

---

## Next Allowed Action

1. `ACTIVE_WORK_PACKAGE = P4-WP019`.
2. `CURRENT_GATE = P4-WP019 / CORRECTIVE REQUIRED BEFORE MERGE`.
3. `P4-WP019 = IN_PROGRESS / CHANGES REQUIRED` (PR #50, branch `ai/p4-wp019-orbis-archive`).
4. Reviewed implementation HEAD = `59596c0e21c6d685a160742fd498128a53b4682b` (Review ID 5135776036: CHANGES REQUIRED).
5. Latest PR commit = `632f70e9159413cb36ea4f767318c605c45497d1`.
6. Antigravity = STOP / NONE after documentation sync.
7. Codex = STOP.
8. Claude Code = STOP.
9. Next Step = ChatGPT Independent Review on PR #50.
10. Do NOT merge without Owner approval.
11. Do NOT start WP020 (PROPOSED / NOT AUTHORIZED).
