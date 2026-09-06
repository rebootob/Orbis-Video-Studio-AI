# Acceptance Criteria & V1 Pass Verification

> **Canonical Document Location:** [`project-docs/40_DELIVERY/ACCEPTANCE_CRITERIA.md`](project-docs/40_DELIVERY/ACCEPTANCE_CRITERIA.md)

---

## 1. Work Package Acceptance Rule

Every Work Package must satisfy its exact authorized Issue/PR contract, tests, architecture locks, security/cost rules and independent review. A green CI result alone is not sufficient when product behavior or safety requirements remain unmet.

A WP is not PASS/CLOSED until:

- implementation stays within authorized scope
- repository tests/build/lint required by that WP pass
- no live paid provider call is used unless explicitly authorized
- product/architecture locks are preserved
- ChatGPT independent review returns PASS
- Project Owner explicitly approves merge
- merged repository truth is verified

---

## 2. Current P2-WP010 Acceptance Focus

P2-WP010 — Mode-Aware Web Workspace & Automation-First Storyboard UX is currently **CHANGES REQUIRED / NOT MERGE-READY** at reviewed HEAD `291ea773681831a0a68e585eb7e0664902102be3`.

Corrective acceptance requires at minimum:

- [ ] no unsafe normal-path hard deletion that violates full-history retention
- [ ] multi-project workspace with usable rename / duplicate / archive / search / sort / recent behavior
- [ ] staged workflow readiness: Story -> Storyboard -> Shot Plan -> Images -> Video
- [ ] user can stop/review/approve before expensive downstream generation
- [ ] clear Next Recommended Action / Guided Flexibility
- [ ] truthful QC/approval/readiness states; no fake completed capability
- [ ] real reference upload/management path rather than placeholder-only UX
- [ ] Generate Selected / Retry Failed / Continue Incomplete or equivalent safe batch behavior
- [ ] known-cost confirmation or clear UNKNOWN behavior before chargeable batch actions
- [ ] lightweight History / Version entry point and no-silent-history-loss behavior
- [ ] scene/shot reorder and safe autosave/unsaved-state handling where required by the WP contract
- [ ] safe CORS configuration
- [ ] frontend lint/build/tests and backend regression tests pass at exact corrective HEAD
- [ ] GitHub Actions pass at exact corrective HEAD

WP010 does not need to implement the full audio engine or final renderer; UI/readiness must remain truthful about deferred capability.

---

## 3. Core V1 Release PASS Verification Checklist

For the overall system to achieve **CORE V1 PASS**, the following capabilities require empirical UAT:

| Step | User / System Action | Verification Standard | Status |
| :--- | :--- | :--- | :--- |
| **1** | Open Multi-Project Workspace | Browser UI loads without local AI/GPU dependency; user can create/open/archive multiple projects. | PENDING |
| **2** | Create Project & Ingest References | User adds brief/docs/images/video references; project data remains isolated and persistent. | PENDING |
| **3** | Mode-Aware Creative Planning | STORY/SHORT/LOOP/SCENE create only appropriate creative layers. | PENDING |
| **4** | Review Story / Concept | User can edit and approve creative structure before detailed generation. | PENDING |
| **5** | Storyboard Review | System creates a reviewable storyboard/visual plan without automatically starting video generation. | PENDING |
| **6** | Detailed Shot Planning | AI creates/editable shot plan, prompts, duration/camera/reference mapping. | PENDING |
| **7** | Reference / Continuity Controls | Character/Location/Style/Brand/factual references are applied consistently and locks are respected. | PENDING |
| **8** | Image / Keyframe Generation | Provider-neutral image generation supports batch/selected/retry/continue behavior and preserves prior evidence. | PENDING |
| **9** | Video Generation | Vidu adapter/durable queue generates eligible shots with retry/reconciliation/idempotency and cost controls. | PENDING |
| **10** | Hybrid Shot Import | Imported video/image/recorded/stock assets can coexist with generated shots. | PENDING |
| **11** | Locks / History / Versioning | Approved assets are protected; regeneration does not silently erase prior versions/history. | PENDING |
| **12** | Core V1 Audio Production | VO, BGM, SFX and ambience can be generated/imported/assigned with basic mix/fade/mute/ducking. | PENDING |
| **13** | Selective / Incomplete Recovery | Only selected/failed/incomplete unlocked work is retried by default; completed chargeable work is not duplicated. | PENDING |
| **14** | Auto Assembly / Simplified Timeline | User can preview ordered shots, durations and basic audio layers without a Premiere-class editor. | PENDING |
| **15** | QC / Final Review | Missing/failed/continuity issues are surfaced truthfully with clear recovery actions. | PENDING |
| **16** | Human Final Approval | Final render cannot proceed without required human approval. | PENDING |
| **17** | Cloud Master Render | Approved sequence renders to final high-quality master. | PENDING |
| **18** | Multi-Output Export | One master project exports approved 16:9 / 9:16 / 1:1/platform variants without recreating the project. | PENDING |

---

## 4. UX Acceptance Principle

The end-to-end product should satisfy:

```text
Simple enough for first-time users
Powerful enough for advanced users
Consistent across every screen
Safe for costly AI actions
Beautiful but not distracting
```

A first-time user should normally understand what to do next without reading a manual, while advanced users retain access to detailed controls.
