# Next Chat Resume Prompt

Copy/paste this block into a new ChatGPT conversation when continuing Orbis Video Studio AI.

```text
Continue Orbis Video Studio AI from repository truth.

Repository:
rebootob/Orbis-Video-Studio-AI

Canonical branch:
main

ACTIVE IMPLEMENTATION BRANCH:
ai/p4-wp019-orbis-archive

ACTIVE PR:
#50

CURRENT EXACT REVIEWED HEAD:
59596c0e21c6d685a160742fd498128a53b4682b

LATEST INDEPENDENT REVIEW:
Review ID: 5135776036
Verdict: CHANGES REQUIRED

LATEST PR COMMIT (AFTER CORRECTIVE):
632f70e9159413cb36ea4f767318c605c45497d1

CURRENT STATUS:
P4-WP019: IN_PROGRESS / CHANGES REQUIRED
ACTIVE_WORK_PACKAGE: P4-WP019
CURRENT_GATE: P4-WP019 / CORRECTIVE REQUIRED BEFORE MERGE
IMPLEMENTATION_AUTHORIZED: YES
P4-WP020: PROPOSED / NOT AUTHORIZED

IMPORTANT:
Fresh-fetch current GitHub/repository truth first.
Repository truth newer than documentation is authoritative.

Read in exact order:
1. project-docs/00_CONTROL/START_HERE.md
2. project-docs/00_CONTROL/CURRENT_STATE.md
3. project-docs/00_CONTROL/ACTIVE_TASK.md
4. project-docs/00_CONTROL/DOCUMENT_INDEX.md
5. project-docs/00_CONTROL/CHAT_HANDOFF.md
6. project-docs/40_DELIVERY/P4_WP019_PROPOSAL.md
7. project-docs/30_PRODUCT/PRODUCT_VISION.md
8. project-docs/30_PRODUCT/VIDEO_PRODUCTION_MODES.md
9. project-docs/30_PRODUCT/USER_WORKFLOW.md
10. project-docs/30_PRODUCT/V1_SCOPE.md
11. only other directly relevant routed documents

KNOWN COMPLETED STATE:
P0-WP001 = PASS / CLOSED / MERGED
P1-WP002 = PASS / CLOSED / MERGED
P1-WP003 = PASS / CLOSED / MERGED
P1-WP004 = PASS / CLOSED / MERGED
P1-WP005 = PASS / CLOSED / MERGED
P2-WP006 = PASS / CLOSED / MERGED
P2-WP007 = PASS / CLOSED / MERGED
P2-WP008 = PASS / CLOSED / MERGED
P2-WP009 = PASS / CLOSED / MERGED
P2-WP010 = PASS / CLOSED / MERGED
P2-WP011 = PASS / CLOSED / MERGED
P2-WP012 = PASS / CLOSED / MERGED
P2-WP013 = PASS / CLOSED / MERGED
P3-WP014 = PASS / CLOSED / MERGED
P3-WP015 = PASS / CLOSED / MERGED
P3-WP016 = PASS / CLOSED / MERGED
P3-WP017 = PASS / CLOSED / MERGED
P4-WP018 = PASS / CLOSED / MERGED
P4-WP019 PRE1 = PASS / CLOSED / MERGED (PR #49, merge commit: 5f3ccbbcd0ee528bb85501a32efb64c5b13fbce5)

P4-WP019 DELIVERED IMPLEMENTATION (PR #50):
1. .orbis ZIP-compatible archive subsystem with POSIX path safety.
2. Canonical manifest & checksum design (checksums.sha256 root trust, canonical RFC 8785 JSON).
3. Archive security validation (Zip Slip, bomb decompression ratio, size limits, absolute/UNC path guards).
4. Project graph export/import with full entity coverage.
5. FULL_SELF_CONTAINED asset packaging.
6. CLONE mode (fresh UUID remap, storage re-upload, source lineage).
7. RESTORE mode (original identity, fail-closed collision detection).
8. Phase-3 canonical in-memory preflight validation (ArchivePreflightValidator).
9. Historical execution fencing (imported_historical = True, execution_disabled = True, worker lease clearing).
10. RenderJob / GenerationJob active partial unique-index separation.
11. UsageLedger imported historical financial fencing.
12. Budget service exclusion of imported historical spend.
13. REST API endpoints (/export, /import/validate, /import/execute).
14. Frontend Export and Import modals integrated into ProjectDashboard.
15. Extensive archive, security, migration, and regression test suites (412 backend tests, 52 frontend tests).

REMAINING REVIEW BLOCKERS (Review ID 5135776036) & DELIVERED CORRECTION:
1. Migration 020 fail-closed downgrade preflight: Precheck UsageLedger (provider, provider_event_id) collisions before any schema change -> Delivered in commit 632f70e with test_020_usage_ledger_coexistence_and_fail_closed_downgrade.
2. Archive self-consistency: Enforce FULL_SELF_CONTAINED, disallow include_renders=False, assert actual_size == catalog size_bytes == Asset.file_size_bytes -> Delivered in commit 632f70e with test_export_with_render_output_asset_self_contained_round_trip and test_preflight_catalog_size_mismatch_rejected_independently.

ROLES:
Owner = final human authority / UAT / merge approval
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = STOP / NONE after documentation sync
Codex = STOP
Claude Code = STOP

NEXT ALLOWED ACTION:
Independent Review on PR #50 for the delivered corrective commit 632f70e9159413cb36ea4f767318c605c45497d1.
Do NOT merge without Owner approval.
Do NOT start WP020.
```
