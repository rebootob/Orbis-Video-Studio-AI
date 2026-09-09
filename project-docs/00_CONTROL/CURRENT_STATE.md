# Current Project State

> Canonical location: `project-docs/00_CONTROL/CURRENT_STATE.md`
>
> Fresh repository/workflow/Issue #63 truth overrides stale text.

---

## State Flags

```yaml
PHASE: P4 — Multi-Output, Export & Core V1 Release
CANONICAL_BRANCH: main
CANONICAL_MAIN: 1c63045497eb7ee708cd81876f6bf7a011907f77

P0-WP001_THROUGH_P4-WP019: PASS / CLOSED / MERGED
P4-WP020: ACTIVE / NOT CLOSED
P4-WP020_LIVE_STATE: R3 STOPPED / CONSUMED / GEMINI HTTP 429
P4-WP020-LIVE-R3-C1: PASS / MERGED / CLOSED
P4-WP020-LIVE-R3-C1-CLOSE: CONTROL-DOC ONLY / OWNER AUTHORIZED / PR #79

ACTIVE_WORK_PACKAGE: NONE
CURRENT_GATE: C1-CLOSE DOC SYNC -> EXACT-HEAD REVIEW -> OWNER MERGE DECISION

COMPLETED_WORK_PACKAGES: 19 / 20
CORE_V1_DELIVERY_PROGRESS: 95_PERCENT_BY_WP_COUNT
CORE_V1_RELEASE_DECLARED: false

ANTIGRAVITY: BOUNDED ONLY WHEN EXPLICITLY AUTHORIZED
CODEX: STOP
CLAUDE_CODE: STOP
PAID_LIVE_EXECUTION: STOP / NOT AUTHORIZED
R4: NOT AUTHORIZED
```

---

## C1 Closure Evidence

- PR #78 merged exact reviewed HEAD `b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6`.
- Merge commit / canonical main = `1c63045497eb7ee708cd81876f6bf7a011907f77`.
- Backend CI run `34298997460` = SUCCESS.
- Backend tests = 511 passed / 2 skipped / 3 warnings.
- PostgreSQL migration paths `fresh-head` and `from-revision-010` = PASS.
- Frontend CI run `34298997360` = SUCCESS.
- Independent review = PASS before Owner merge.
- C1 provider calls = 0.
- C1 spend = USD 0.00.
- No model/endpoint/pricing/retry-policy change.
- No provider generation request, paid workflow dispatch, release, tag, or deploy.

C1 now provides strict sanitized Gemini HTTP 429 structured evidence and a second nested allowlist for STOP artifacts. Raw provider message/body/headers, credentials, prompts, arbitrary project dimensions, and unknown debug/help data remain excluded.

---

## External Gemini Billing / Quota Remediation Evidence

Owner-supplied Google AI Studio evidence after C1 merge confirms the account-side corrective:

```text
Gemini project: Orbis-Video-Production
Billing tier: Tier 1 / Prepay
Credit balance observed: USD 5.00
Nano Banana 2 (Gemini 3.1 Flash Image):
  RPM: 100
  TPM: 200K
  RPD: 1K
Prior Free-tier observation for the image model: 0 / 0 / 0
```

The prior R3 Gemini HTTP 429 is therefore consistent with the old Free-tier image quota-zero condition, not a proven Orbis code defect.

Owner also reported updating the repository GitHub Actions `GEMINI_API_KEY` secret to the new Orbis project key. The secret value is intentionally not readable or recorded in repository evidence. Runtime adoption of the new secret has **not yet been validated**; that requires a separately authorized NO-PAID preflight.

This external remediation evidence does not authorize R4 or any provider request.

---

## Immutable LIVE History

### R1
- consumed and immutable;
- bounded OpenAI request returned HTTP 429;
- never rerun R1.

### R2
```text
Execution ID: LIVE-20260909-BB75-R2
Run ID: 34287696335
Main SHA: 570acda49245ecae7ae48e1e66ed8839e4bfc2e2
Execution fence: CONSUMED
```
- OpenAI STORY = SUCCESS;
- Gemini IMAGE = non-success surfaced as `HTTP_ERROR`;
- conservative chargeable requests = 2/6;
- last known confirmed/committed UAT cost = USD 0.0072;
- Vidu / ElevenLabs / downstream = NOT EXECUTED;
- never rerun R2.

### R2-C1
- PR #74 merged at `d706acacd1f51224c955fb9c8d0d9eab3deda186`;
- future Gemini non-2xx status/classification became durable;
- provider calls 0 / spend USD 0.00.

### R3-PRE1
- PR #75 merged;
- metadata probe run `34291500281` = PASS / HTTP 200;
- model `gemini-3.1-flash-image` visible;
- generation calls 0 / spend USD 0.00.

### R3 TOOL1 / PF1
- TOOL1 merged via PR #77;
- paid tooling main at R3 execution = `82ce42116e3f866227dd598814cf79c0b9c640c4`;
- PF1 run `34296382370` = `PREFLIGHT_PASS`;
- estimated reservation USD 0.2739 < USD 1.00;
- PF1 generation calls 0 / fence false.

### R3 LIVE
```text
Execution ID: LIVE-20260909-363F-R3
Run ID: 34297314995
Execution Main SHA: 82ce42116e3f866227dd598814cf79c0b9c640c4
Execution fence comment: 5594141834
STOP evidence comment: 5594143482
Execution fence: CONSUMED
Status: STOPPED
Phase: LIVE-02-GEMINI-IMAGE
```

Observed:
- immediate pre-fence no-paid preflight = PASS;
- OpenAI STORY = SUCCESS;
- OpenAI usage = 546 prompt / 513 completion tokens;
- last known committed/actual Orbis UAT cost at STOP = USD 0.0065;
- Gemini IMAGE = HTTP 429;
- retryable true / submission_uncertain false;
- conservative calls = 2/6;
- Vidu / ElevenLabs / downstream = NOT EXECUTED;
- R3 MUST NEVER BE RERUN.

USD 0.0065 is known Orbis UAT cost evidence only; failed Gemini external billing is not proven either way.

---

## Next Gate

There is no active implementation package after C1 closure.

After C1-CLOSE merges, the next candidate is a separately Owner-authorized `P4-WP020-LIVE-R4-PRE1` NO-PAID runtime readiness check to prove credential/config presence and runtime adoption without image generation, spend, or execution fence.

R4 paid/live execution remains NOT AUTHORIZED.

Any future paid execution requires a new execution identity, fresh exact-main authorization, fresh no-paid preflight, a new one-shot fence, and separate Owner run authorization.

No gate auto-authorizes the next one.
