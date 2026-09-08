# P4-WP020-A-R2 — Post-Corrective Zero-Billing Confirmation

Status: **CONFIRMATION IN PROGRESS**

Base `main`: `7c54b9cae846c43f229203a408f529efd581ee18`

## Purpose

Re-run the merged deterministic zero-billing Core V1 evidence path after P4-WP020-A-R1 closed S1-A01, S1-A02 and S1-A03.

This confirmation stage does not authorize live/paid provider calls and does not introduce application-code changes.

## Confirmation scope

1. Deep STORY path including fake VideoProvider completion -> durable VIDEO Asset -> Shot lineage -> Assembly.
2. Core V1 mode routing for STORY / SHORT / LOOP / SCENE.
3. Multi-project isolation.
4. Audio -> Assembly -> Subtitle/SRT -> QC -> Human Approval -> Master Render.
5. Multi-output 16:9 / 9:16 / 1:1.
6. FULL_SELF_CONTAINED `.orbis` export/validate/CLONE and RESTORE collision handling.
7. Imported historical job fencing and live-budget exclusion.
8. Focused retry/reconciliation, locks/history, provider, archive/security and render regressions through the existing backend suite.
9. Frontend lint/typecheck/build/tests through the existing frontend workflow.

## Safety constraints

- ZERO-BILLING ONLY.
- No live Creative/Image/Video/Audio provider calls.
- Existing fake/mock providers and HTTP denial remain authoritative for this stage.
- No Post-Core-V1 features.
- Any new S0/S1 finding blocks WP020-LIVE and requires a separately bounded corrective.

## Required evidence before closure

- Exact-head Backend CI PASS, including `backend/tests/test_wp020a_zero_billing_e2e.py`.
- Exact-head Frontend CI PASS.
- No S0/S1 release blocker found in the confirmation delta/evidence.
- Independent Control Plane review tied to the exact PR HEAD.

## Gate after PASS

If all confirmation gates pass, P4-WP020-A may be closed as zero-billing integration-complete and the next gate becomes **P4-WP020-LIVE authorization decision**.

Live/paid UAT remains separately Owner-authorized.
