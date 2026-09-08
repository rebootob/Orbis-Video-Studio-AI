# P4-WP020 Proposal — End-to-End System Integration, UAT & Core V1 Release

> **Status:** PROPOSED / NOT AUTHORIZED  
> **Canonical proposal path:** `project-docs/40_DELIVERY/P4_WP020_PROPOSAL.md`

---

## 1. Purpose

P4-WP020 is the final planned Core V1 work package. Its purpose is to prove that the already-delivered Orbis Video Studio AI system works as an integrated product, identify and close only genuine Core V1 release blockers, execute Owner UAT, collect release evidence, and support the final Core V1 release decision.

WP020 is not a feature-expansion package. It must not silently absorb post-Core-V1 integrations, new providers, new production modes, heavyweight editing features, or unrelated cleanup.

Current repository truth at proposal creation:

```text
Canonical branch: main
Starting main HEAD: 215b6cdda4ac36c1f0682bebdb706c1d8aa3b2fd
Completed planned Core V1 WPs: 19 / 20
P4-WP019: PASS / CLOSED / MERGED
ACTIVE_WORK_PACKAGE: NONE
P4-WP020: PROPOSED / NOT AUTHORIZED
```

---

## 2. Locked Product Contract

Core V1 modes:

```text
STORY
SHORT
LOOP
SCENE
```

Product locks that WP020 must verify and must not weaken:

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
PROVIDER_INDEPENDENCE = REQUIRED
PERFORMANCE_AND_SCALABILITY = REQUIRED_PRODUCT_QUALITY_ATTRIBUTE
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
VENDOR_LOCK_IN = DISALLOWED
```

Provider-neutral boundaries remain:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Vidu remains the Core V1 default VideoProvider behind an adapter.

---

## 3. Execution Model — Mandatory Staged Gates

WP020 must be executed as staged gates. Passing one gate does not automatically authorize the next gate when the next gate would introduce code changes, paid provider usage, or release mutation.

### P4-WP020-PRE1 — Evidence-Only Release Readiness / Gap Review

**Default first gate. No application-code changes. No paid provider calls.**

Required output:

1. Map every Core V1 required capability to existing source, tests and runnable UI/API evidence.
2. Map the 18 canonical Core V1 acceptance rows in `ACCEPTANCE_CRITERIA.md` to current implementation evidence.
3. Add system-level verification requirements for `.orbis` export/import round-trip and historical fencing.
4. Verify all four Core V1 modes have a valid production path without assuming every Project has a Story.
5. Identify missing, placeholder-only, contradictory or untestable Core V1 behavior.
6. Identify test-environment prerequisites and isolated UAT data requirements.
7. Produce a release-gap register classified by severity.
8. Do not fix findings during PRE1.

Known candidate gap requiring explicit PRE1 verification:

- `V1_SCOPE.md` defines **Subtitle Generation / Export where applicable = REQUIRED FOR CORE V1**.
- Initial repository search at proposal creation found no `subtitle`, `caption`, `srt` or `vtt` implementation references on `main`.
- PRE1 must verify whether equivalent functionality exists under another name. If absent, classify it as a Core V1 release gap; do not silently remove the requirement and do not implement it during PRE1.

### P4-WP020-A — Deterministic Zero-Billing E2E / Integration Evidence

Only after Owner authorization following PRE1.

Allowed work:

- create or strengthen deterministic E2E/integration/product tests needed to exercise the integrated Core V1 path;
- add test fixtures/fakes/mocks and isolated test helpers;
- fix testability defects only when required to produce truthful system evidence;
- run the complete regression suite.

Default provider policy:

```text
LIVE_PAID_PROVIDER_CALLS = DISALLOWED
MOCK / FAKE PROVIDERS = REQUIRED BY DEFAULT
```

### P4-WP020-Rx — Release-Blocker Correctives

Corrective implementation is allowed only for a proven Core V1 release blocker found by PRE1/E2E/UAT and explicitly accepted into the corrective scope.

Rules:

- minimal change only;
- no unrelated refactor;
- no new provider unless the missing provider was already an explicit Core V1 requirement;
- no new production modes;
- no post-V1 integration work;
- preserve historical data, cost safety and provider abstraction;
- each corrective HEAD must be independently reviewed before progressing.

### P4-WP020-LIVE — Owner Live UAT

Live paid-provider execution is **not authorized by general WP020 authorization**.

Before any paid Vidu/Creative/Image/Audio call, obtain a separate explicit Owner authorization defining at minimum:

- provider(s) allowed;
- bounded scenario(s);
- maximum jobs/shots/duration;
- maximum approved spend or equivalent hard budget cap;
- target test project/environment.

Live UAT should be the minimum necessary to prove real provider integration after zero-billing E2E is green.

### P4-WP020-CLOSE — Core V1 Release Closure

No release tag or final Core V1 PASS declaration until all closure criteria in this proposal are satisfied and the Owner explicitly approves release closure.

---

## 4. E2E Scenario Matrix

The E2E strategy must avoid multiplying every scenario across every mode. Use one deep full-path scenario plus bounded mode-specific smoke/branch scenarios.

| ID | Scenario | Required Evidence |
| :--- | :--- | :--- |
| E2E-01 | **STORY deep path**: Create Project -> Brief/References -> Story/Script/Scenes/Shots -> approvals -> storyboard/keyframes -> video jobs -> audio -> assembly -> QC -> final approval -> render -> multi-output export | System-level state transitions, persisted lineage, output assets, cost/usage records, no silent history loss |
| E2E-02 | **SHORT mode path** without mandatory full Story | Correct compact structure, mode routing, 9:16 default/intention, subtitle requirement verification, downstream generation compatibility |
| E2E-03 | **LOOP mode path** without Story/Script requirement | Loop-specific structure/shot path, no invalid Story assumption, render/export compatibility |
| E2E-04 | **SCENE mode path** without Project Story requirement | Scene -> 1-N Shots valid end-to-end path |
| E2E-05 | Multi-project isolation | Two projects coexist; records/assets/history/costs do not cross project boundaries |
| E2E-06 | Approval/cost gate | Planning/review cannot silently trigger chargeable downstream work; final render blocked until explicit approval |
| E2E-07 | Batch/selective recovery | Generate Selected / Retry Failed / Continue Incomplete only affect eligible work; completed paid work is not duplicated |
| E2E-08 | Provider failure/reconciliation | Failed/uncertain external outcome is represented truthfully; retry/reconciliation remains idempotent |
| E2E-09 | Locks/history/versioning | Locked/approved assets cannot be silently overwritten; regeneration creates new evidence/lineage |
| E2E-10 | Audio integration | VO/BGM/SFX/Ambience plus basic volume/fade/mute/ducking survive assembly/render path |
| E2E-11 | QC/final approval | Blockers/warnings are surfaced truthfully; final render cannot bypass approval |
| E2E-12 | Multi-output | One approved project produces supported 16:9, 9:16 and 1:1 variants without recreating project truth |
| E2E-13 | `.orbis` portability | Export FULL_SELF_CONTAINED -> validate -> CLONE import -> verify remap/assets/history -> create new live work; RESTORE collision fails closed |
| E2E-14 | Historical fencing after import | Imported historical jobs/ledgers retain truth but are excluded from worker execution/live uniqueness/live budget counting as designed |
| E2E-15 | Security/secret safety | No provider secrets in archive, logs or user-visible evidence; unsafe archive paths remain rejected |
| E2E-16 | Browser-first / cloud-first usability | Core flow does not require local AI/GPU/runtime dependency |

---

## 5. Owner UAT Matrix

Owner UAT must validate user-observable truth, not only automated assertions.

| UAT ID | Owner Action | PASS Standard |
| :--- | :--- | :--- |
| UAT-01 | Open dashboard and manage multiple projects | Create/open/archive/search lifecycle is understandable and isolated |
| UAT-02 | Create one STORY project from a realistic brief/reference set | Clear recommended next action; no dead-end state |
| UAT-03 | Review/edit/approve Story before expensive generation | User can stop, revise and approve safely |
| UAT-04 | Review Storyboard and Shot Plan | No video generation starts merely because planning exists |
| UAT-05 | Generate selected/incomplete visual work | User can control scope; history remains inspectable |
| UAT-06 | Exercise one failure/retry path | Recovery guidance is understandable and completed work is not duplicated |
| UAT-07 | Produce/assign Core V1 audio | Basic audio controls are usable and represented truthfully |
| UAT-08 | Preview assembly and inspect QC | Missing/failed/continuity states are actionable and truthful |
| UAT-09 | Approve final production and render | Render is blocked before approval and allowed after approval |
| UAT-10 | Export multiple variants | Variants are generated from the same approved project |
| UAT-11 | Export `.orbis`, re-import as CLONE and reopen history | Project is portable, self-contained and usable after import |
| UAT-12 | Run bounded SHORT/LOOP/SCENE smoke paths | Each mode uses only applicable creative layers and has a clear production path |
| UAT-13 | Verify subtitle behavior where applicable | Required Core V1 subtitle/export behavior is actually usable or the release remains blocked |

Screenshots, short screen recordings, exported artifacts, DB/ledger evidence or structured UAT notes may be used as evidence depending on the scenario.

---

## 6. Release-Blocking Severity Rules

### S0 — STOP / Critical

Any of the following blocks all release progression:

- secret/API-key leakage;
- destructive data/history loss;
- unauthorized or duplicate chargeable provider execution;
- approval bypass allowing final render when approval is required;
- project isolation breach;
- corrupted archive/import causing silent loss or unsafe execution;
- unrecoverable migration/data-integrity defect.

### S1 — Core V1 Release Blocker

Blocks Core V1 PASS until corrected:

- deep STORY path cannot complete end to end;
- any required Core V1 mode has no valid usable path;
- required Core V1 capability is absent or placeholder-only (including subtitle/export if confirmed absent);
- retry/resume/idempotency behavior can duplicate completed paid work;
- lock/history/version guarantees fail;
- audio/QC/final approval/render/multi-output/archive integration fails materially;
- browser/cloud-first product cannot be operated as intended.

### S2 — Major but Potentially Releasable Only with Explicit Owner Acceptance

Examples:

- non-safety UX friction;
- confusing secondary action where a valid primary path still exists;
- performance degradation that remains bounded and does not corrupt state or cost.

S2 may remain only if documented, not misleading, and explicitly accepted by Owner for Core V1 release.

### S3 — Minor / Backlog

Cosmetic, copy or minor polish issues with no material impact on correctness, safety, cost, history or successful production flow.

---

## 7. Critical Regression Gates

At every corrective/release candidate HEAD:

1. Full backend regression PASS.
2. Full frontend tests PASS.
3. Frontend lint/typecheck/build PASS.
4. Focused E2E/integration suite PASS.
5. Migration lifecycle tests PASS if schema/migration changed.
6. Archive/security tests PASS if archive/import touched.
7. `git diff --check` PASS.
8. Exact-head GitHub Actions green.
9. No unauthorized live provider calls.
10. No scope leak into Post-Core-V1 work.

---

## 8. Evidence Requirements

Release evidence must be anchored to exact repository HEADs and include:

- exact commit SHA / PR / branch;
- changed files and scope statement;
- automated test counts/results;
- exact-head CI runs;
- E2E scenario results with PASS/FAIL and evidence reference;
- Owner UAT results with PASS/FAIL and notes;
- provider-live evidence only when separately authorized;
- cost/UsageLedger evidence for chargeable scenarios;
- output asset evidence for render/multi-output;
- `.orbis` round-trip evidence;
- release-gap register and final disposition;
- known accepted S2/S3 issues, if any;
- confirmation of zero exposed secrets.

CI green alone is not sufficient for Core V1 PASS.

---

## 9. Rollback / Recovery Requirements

WP020 testing and UAT must use isolated/non-production-safe test data by default.

- Never rely on destructive cleanup of real user projects.
- Use dedicated UAT project IDs/storage prefixes/database fixtures where possible.
- Preserve generated evidence until the review decision is complete.
- If a release-blocker corrective changes schema, require real migration upgrade/downgrade lifecycle tests and fail-closed behavior.
- If a corrective changes durable jobs/cost accounting, prove retry/resume/reconciliation and budget fencing again.
- If live provider UAT is authorized, enforce project budget/hard cap before execution and retain provider event/ledger evidence.

---

## 10. Core V1 Release Closure Criteria

Core V1 may be declared **PASS / RELEASE READY** only when all are true:

1. All 19 previously closed WPs remain regression-clean.
2. All required Core V1 acceptance rows are empirically verified.
3. STORY deep E2E passes.
4. SHORT, LOOP and SCENE bounded mode UAT/E2E paths pass.
5. Multi-project isolation, approvals, cost safety, history/locks and recovery pass.
6. Core V1 audio integration passes.
7. QC -> human approval -> cloud render path passes.
8. Multi-output variants pass.
9. `.orbis` export/import portability and historical fencing pass.
10. Subtitle Generation / Export requirement is proven usable where applicable; if absent it must be corrected before release or the Owner must formally amend Core V1 scope in a separate governance decision.
11. No open S0 or S1 issues.
12. Any remaining S2 issue is explicitly documented and accepted by Owner.
13. Exact release-candidate HEAD passes full CI and release gates.
14. ChatGPT Independent Final Review returns PASS / READY FOR OWNER RELEASE DECISION.
15. Owner explicitly approves Core V1 release closure.

A release tag such as `v1.0.0-core` (name to be confirmed at closure) must not be created before explicit Owner release approval.

---

## 11. Explicitly Out of Scope for WP020

Unless separately authorized by Owner, WP020 must not implement:

- Hermes / n8n / external-agent operational gateway;
- PRODUCT / EXPLAINER / PRESENTER / MONTAGE production modes;
- ComfyUI/cloud-GPU provider implementation;
- additional Creative/Image/Video/Audio providers merely for breadth;
- social publishing automation;
- marketplace/provider ecosystem;
- native mobile apps;
- realtime collaborative editing;
- Premiere-class NLE functionality;
- advanced DAW/audio plugin ecosystem;
- realtime cloud project replication/sync;
- unrelated dependency upgrades/refactors;
- cosmetic redesign unrelated to a UAT blocker.

---

## 12. Authorization Boundary

This proposal does **not** authorize WP020 implementation.

Recommended first authorization after this proposal is accepted:

```text
P4-WP020-PRE1 — EVIDENCE-ONLY Release Readiness / Gap Review
```

PRE1 must produce evidence and a classified release-gap register, then STOP for ChatGPT review / Owner decision before code changes.
