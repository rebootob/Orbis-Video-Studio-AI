# P4-WP020 S1 Corrective Plan — Bounded Release-Blocker Closure

> **Status:** PLAN ONLY / IMPLEMENTATION NOT AUTHORIZED  
> **Source evidence:** `P4_WP020_PRE1_EVIDENCE.md`  
> **Canonical planning base:** `main` at/after PRE1 merge `0f3ff326913e29cc0def14db5195ded90d8d7ff3`

---

## 1. Purpose

This document converts the four S1 Core V1 release blockers confirmed by P4-WP020-PRE1 into small, reviewable corrective packages.

The plan is intentionally bounded. It does **not** authorize application-code implementation, provider calls, paid UAT, release tagging, unrelated refactors, dependency upgrades or Post-Core-V1 feature expansion.

```text
CORRECTIVE_IMPLEMENTATION_AUTHORIZED = NONE
PAID_PROVIDER_CALLS = NONE
WP020_A_AUTHORIZED = NO
WP020_LIVE_AUTHORIZED = NO
CORE_V1_PASS = NOT DECLARED
```

Confirmed PRE1 blockers:

```text
GAP-S1-01 = Subtitle generation/export absent
GAP-S1-02 = Production ImageProvider missing / mock-only
GAP-S1-03 = Production AudioProvider missing / mock-only
GAP-S1-04 = Cloud render runtime not operationally deployable
```

---

## 2. Governing Rules

Every corrective package below follows these rules:

1. Separate branch/PR per corrective package unless the Owner explicitly changes the contract.
2. No corrective package auto-authorizes the next package.
3. Minimal change only; do not redesign accepted core architecture.
4. Preserve provider-neutral boundaries: CreativeProvider / ImageProvider / VideoProvider / AudioProvider.
5. Preserve multi-project isolation, full history, lock/version safety, approvals, idempotency, cost/ledger safety and `.orbis` portability.
6. Mock/fake provider tests are mandatory before any live call.
7. No live or paid provider call is authorized by implementation approval alone.
8. Full backend regression, frontend checks when affected, focused corrective tests, `git diff --check`, exact-head Actions and Independent Review are mandatory before merge.
9. Owner merge approval is required for each corrective PR.
10. If a corrective reveals a new S0/S1 outside its bounded scope, STOP and return to Owner for scope decision.

---

## 3. Recommended Execution Order

```text
R1 — Cloud Render Runtime Operability       closes GAP-S1-04
R2 — Minimum Core V1 Subtitle Capability    closes GAP-S1-01
R3 — Production ImageProvider Adapter       closes GAP-S1-02
R4 — Production AudioProvider Routing       closes GAP-S1-03
THEN — P4-WP020-A Zero-Billing E2E
THEN — separately authorized P4-WP020-LIVE
THEN — P4-WP020-CLOSE
```

### Why this order

- **R1 first:** it has no paid-provider dependency and creates the runnable final-output path needed by subtitle burn-in and later E2E.
- **R2 second:** subtitle can be implemented deterministically from authoritative project/VO/dialogue text without introducing a new AI provider; final render integration can then bind to the working render path.
- **R3 third:** image generation is earlier in the production chain and the existing ImageProvider contract is already strong; one bounded production adapter can close the mock-only gap.
- **R4 fourth:** audio has the broadest capability surface (VO/BGM/SFX/Ambience), so provider capability selection must be evidence-driven and may require bounded routing rather than a rushed single-vendor assumption.

---

# 4. P4-WP020-R1 — Cloud Render Runtime Operability

**Maps to:** `GAP-S1-04`

## Goal

Make the already-implemented render job/worker architecture runnable in the supported containerized environment without replacing the accepted render design.

## Allowed implementation

1. Install FFmpeg runtime dependency in the supported render/backend image path.
2. Add an explicit render-worker process entrypoint/loop around the existing `CloudRenderWorker.process_one_job()` boundary.
3. Add bounded polling/backoff and graceful shutdown behavior appropriate for a worker process.
4. Wire a `render-worker` service/process into the supported Docker Compose/UAT path using the same DB/object-storage configuration as backend.
5. Reuse existing render job lease/fencing/claim/reconciliation behavior.
6. Add health/startup validation that fails clearly when FFmpeg or required runtime configuration is unavailable.
7. Add focused tests/smoke evidence proving worker operability with a fake/mock executor where external binaries or media would make CI nondeterministic.

## Explicit exclusions

- no new render architecture;
- no GPU renderer;
- no ComfyUI;
- no distributed scheduler platform;
- no new output presets;
- no unrelated container/dependency upgrades;
- no frontend redesign.

## Acceptance criteria

R1 may PASS only when all are true:

1. Supported image/container path contains a usable FFmpeg binary or an explicitly separate render-worker image does.
2. A documented command/service starts a persistent render worker.
3. Worker claims eligible live jobs and never executes `imported_historical` / `execution_disabled` jobs.
4. Worker preserves exact approved timeline binding and existing fail-closed missing-asset behavior.
5. Success path produces output Asset lineage and settles render job/ledger as designed.
6. Failure/retry/reconciliation/lease fencing remain regression-clean.
7. Compose/UAT configuration starts backend + dependencies + render-worker without hardcoded secrets.
8. Full regression and exact-head CI pass.

## STOP condition

After reviewed R1 HEAD is pushed and CI is green, STOP for Independent Review and Owner merge decision. Do not begin R2 automatically.

---

# 5. P4-WP020-R2 — Minimum Core V1 Subtitle Capability

**Maps to:** `GAP-S1-01`

## Goal

Implement the smallest truthful subtitle/caption capability required by Core V1, especially for SHORT/social output, without expanding into a captioning platform.

## Locked V1 minimum

The V1 subtitle implementation should support:

1. A project/timeline-bound subtitle track with ordered subtitle segments.
2. Segment fields sufficient for deterministic export: text, start time, end time, language and source/lineage reference.
3. Deterministic subtitle generation from authoritative existing text where available, such as VO/dialogue/script/shot text; no paid speech-to-text provider is required for this corrective.
4. User-visible enable/disable and review of generated subtitle content at a minimal level sufficient to prevent silent incorrect output.
5. SRT sidecar export as the minimum portable subtitle artifact.
6. Final-render integration for a simple `OFF` / `BURN_IN` choice once R1 render runtime is operational.
7. Subtitle state/version binding so later timeline edits cannot silently reuse stale timing as current truth.

## Explicit exclusions

- no translation platform;
- no multi-language localization workflow;
- no ASR/transcription provider;
- no karaoke/word-level animation;
- no advanced styling editor;
- no speaker diarization;
- no subtitle marketplace/publishing integration.

## Acceptance criteria

R2 may PASS only when all are true:

1. Subtitle segments are persisted and project/timeline isolated.
2. Deterministic generation creates valid non-overlapping timing for supported authoritative text sources.
3. A valid SRT artifact can be exported and is linked to project/timeline/revision evidence.
4. SHORT path can truthfully use subtitle output where applicable.
5. Burn-in mode, when selected, is rendered through the provider-neutral render path and does not bypass final approval.
6. Timeline/revision changes make stale subtitle timing detectable/reviewable rather than silently current.
7. No provider key or paid service is introduced.
8. Full regression and exact-head CI pass.

## STOP condition

After reviewed R2 HEAD is pushed and CI is green, STOP for Independent Review and Owner merge decision. Do not begin R3 automatically.

---

# 6. P4-WP020-R3 — Production ImageProvider Adapter

**Maps to:** `GAP-S1-02`

## Goal

Add exactly one production-capable cloud ImageProvider behind the existing `IImageGenerationProviderAdapter` contract while keeping the mock provider for deterministic tests.

## Mandatory provider-selection subgate

Before implementation code, R3 must document a small capability decision against the existing interface. The selected provider must be evaluated for:

- cloud API availability and authentication model;
- supported image generation suitable for storyboard/keyframe use;
- requested aspect-ratio handling or safe deterministic mapping;
- reference-image capability and truthful fallback/unsupported behavior;
- synchronous vs asynchronous job semantics and how they map to `ImageJobResult`;
- retryable vs uncertain submission semantics;
- output URL/bytes/content type handling;
- usage/cost observability;
- current operational constraints/terms relevant to the implementation.

The decision may choose a provider candidate already consistent with product architecture, but provider choice remains an adapter implementation detail and must not leak into core domain/UI semantics.

## Allowed implementation

1. Add one real cloud adapter implementing the existing ImageProvider interface.
2. Add configuration/env settings for provider selection and credentials without hardcoding secrets.
3. Register production provider in `ImageProviderFactory` while preserving `mock_image` for tests.
4. Map provider success/failure/async status into canonical `ImageJobResult` fields.
5. Preserve asset lineage, lock/version checks, budget/idempotency/retry/reconciliation behavior already owned by core services.
6. Add HTTP/provider contract tests using fakes/mocks only.
7. Fail closed for unsupported request combinations instead of silently dropping critical continuity/reference intent.

## Explicit exclusions

- no second ImageProvider for breadth;
- no ComfyUI/cloud GPU;
- no provider-specific fields added to core Project/Scene/Shot semantics unless already supported through `provider_specific_params`;
- no provider model picker redesign;
- no paid generation during implementation verification.

## Acceptance criteria

R3 may PASS only when all are true:

1. At least one real cloud ImageProvider adapter is registered and configuration-selectable.
2. Missing/invalid credentials fail clearly without falling back silently to fake production output.
3. Mock provider remains available for deterministic tests.
4. Provider response/error/status maps truthfully to canonical state.
5. Reference inputs are honored where supported; unsupported critical inputs fail explicitly.
6. Generated image asset lineage and cost/usage evidence remain auditable.
7. Retry/idempotency/uncertain-submission behavior cannot duplicate known-completed paid work.
8. No live paid call is used to claim implementation PASS.
9. Full regression and exact-head CI pass.

## STOP condition

After reviewed R3 HEAD is pushed and CI is green, STOP for Independent Review and Owner merge decision. Do not begin R4 automatically.

---

# 7. P4-WP020-R4 — Production AudioProvider Routing

**Maps to:** `GAP-S1-03`

## Goal

Replace mock-only production audio generation with the minimum real cloud capability needed for Core V1 VO/BGM/SFX/Ambience, without turning Orbis into a DAW or hard-wiring one vendor into core logic.

## Mandatory provider-capability subgate

Before implementation code, R4 must produce a capability matrix for the existing AudioProvider contract:

```text
VO / DIALOGUE -> TTS capability
BGM           -> music generation capability
SFX           -> sound-effect generation capability
AMBIENCE      -> ambience / sound-effect generation capability
```

Provider selection rules:

1. Prefer one provider if it truthfully covers all required types at acceptable operational complexity.
2. If one provider cannot cover all required Core V1 types, bounded capability-based routing across **no more than two production providers** is allowed without redesigning the core interface.
3. `ORIGINAL_AUDIO` remains imported/attached media, not a generation requirement.
4. Voice cloning is not required for Core V1.

## Allowed implementation

1. Add the minimum production AudioProvider adapter(s) required by the capability decision.
2. Preserve `MockAudioProviderAdapter` for deterministic tests.
3. Configure credentials/provider routing through environment/config only.
4. Map provider outputs into canonical `AudioJobResult` including content type, duration, error/retry/uncertain semantics and cost where available.
5. Preserve existing audio plan/history/lock/version/budget/idempotency/reconciliation and mix/ducking workflow.
6. Add provider contract tests using mocked HTTP/provider responses only.
7. Fail explicitly when an audio type is unsupported by the configured provider route.

## Explicit exclusions

- no voice cloning requirement;
- no advanced EQ/compressor/limiter;
- no waveform editor;
- no plugin ecosystem;
- no more than two production providers under this corrective without separate Owner scope amendment;
- no live paid audio generation during implementation verification.

## Acceptance criteria

R4 may PASS only when all are true:

1. Configured production routing can service VO, BGM, SFX and Ambience through the canonical AudioProvider boundary.
2. Missing/invalid credentials fail clearly and never silently substitute mock audio in production mode.
3. Provider capabilities are explicit and unsupported types fail closed.
4. Output audio assets preserve project/clip lineage and existing history/version safety.
5. Usage/cost evidence remains auditable and retry/reconciliation remains idempotent.
6. Existing basic volume/mute/fade/ducking assembly behavior remains regression-clean.
7. No live paid call is used to claim implementation PASS.
8. Full regression and exact-head CI pass.

## STOP condition

After reviewed R4 HEAD is pushed and CI is green, STOP for Independent Review and Owner merge decision. Do not start WP020-A automatically.

---

## 8. Cross-Corrective Test Matrix

Every corrective must preserve these existing behaviors, with focused reruns where touched:

| Area | Required regression truth |
| :--- | :--- |
| Multi-project | No cross-project data/asset/job/ledger leakage |
| History/version | No silent overwrite; stale revision evidence remains distinguishable |
| Locks | Locked/approved work cannot be mutated silently |
| Approval | Final render remains impossible before explicit final approval |
| Cost | Estimates/actuals/unknowns remain truthful; hard budget gates preserved |
| Jobs | Idempotency, retry/resume and reconciliation prevent duplicate known-completed paid work |
| Archive | `.orbis` remains secret-safe and historical jobs stay execution fenced |
| Provider abstraction | Core/UI do not depend directly on provider SDK payloads |
| Cloud-first | No local AI/GPU requirement introduced |

If schema/migrations change, migration upgrade/downgrade lifecycle tests become mandatory for that corrective.

---

## 9. Authorization Matrix

| Gate | Current state after this plan is accepted | Who may authorize next |
| :--- | :--- | :--- |
| Corrective plan | DOCUMENTATION ONLY | Owner accepts/merges plan |
| R1 implementation | NOT AUTHORIZED | Owner explicit authorization |
| R2 implementation | NOT AUTHORIZED | Owner explicit authorization after R1 review/merge unless Owner changes order |
| R3 implementation | NOT AUTHORIZED | Owner explicit authorization |
| R4 implementation | NOT AUTHORIZED | Owner explicit authorization |
| WP020-A zero-billing E2E | NOT AUTHORIZED | Owner after all accepted S1 corrective merges |
| WP020-LIVE | NOT AUTHORIZED | Owner separate bounded paid-provider authorization |
| WP020-CLOSE / release tag | NOT AUTHORIZED | Owner after final evidence + Independent Review |

---

## 10. Definition of Corrective Closure

The four PRE1 blockers are considered closed only after all four corrective packages are independently merged with accepted evidence:

```text
GAP-S1-04 -> CLOSED by R1
GAP-S1-01 -> CLOSED by R2
GAP-S1-02 -> CLOSED by R3
GAP-S1-03 -> CLOSED by R4
```

Closing these four blockers does **not** itself declare Core V1 PASS. The corrected system must still pass P4-WP020-A zero-billing E2E, separately authorized live UAT where necessary, and P4-WP020-CLOSE release gates.

---

## 11. Next Decision After Plan Merge

Recommended next Owner authorization:

```text
P4-WP020-R1 — Cloud Render Runtime Operability
```

R1 should be implemented as a bounded corrective on its own branch/PR, then independently reviewed and stopped for Owner merge decision.
