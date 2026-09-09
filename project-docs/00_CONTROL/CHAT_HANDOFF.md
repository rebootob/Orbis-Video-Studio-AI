# Chat Session Handoff

> Canonical location: `project-docs/00_CONTROL/CHAT_HANDOFF.md`
>
> Repository/workflow/Issue #63 truth newer than this file is authoritative.

Repository: `rebootob/Orbis-Video-Studio-AI`
Canonical branch: `main`

---

## Delivery Baseline

```text
P0-WP001 through P4-WP019 = PASS / CLOSED / MERGED
Completed planned Core V1 work packages = 19 / 20
P4-WP020 = ACTIVE / NOT CLOSED
Core V1 release = NOT DECLARED
ACTIVE_WORK_PACKAGE = NONE
LAST_CLOSED_WORK_PACKAGE = P4-WP020-LIVE-R3-C1
C1_CLOSURE_SYNC = PR #79 / CONTROL-DOC ONLY
R4 = NOT AUTHORIZED
```

---

## Current Canonical Truth

```text
Canonical main after C1 merge:
1c63045497eb7ee708cd81876f6bf7a011907f77

C1:
PR: #78
Exact reviewed head: b3bc2e3c3300ec2959d6eabfb54ae21e3d461af6
Status: PASS / MERGED / CLOSED
Backend CI: 34298997460 SUCCESS
Backend tests: 511 passed / 2 skipped / 3 warnings
Migrations: fresh-head PASS / from-revision-010 PASS
Frontend CI: 34298997360 SUCCESS
Provider calls: 0
Spend: USD 0.00
```

C1 added strict sanitized Gemini HTTP 429 structured evidence classification and a second nested allowlist for STOP artifacts. It did not change model, endpoint, pricing, retry policy, provider routing, or paid workflow behavior.

---

## Confirmed External Gemini Remediation

Owner-provided Google AI Studio evidence now shows:

```text
Project: Orbis-Video-Production
Billing tier: Tier 1 / Prepay
Credit balance observed: USD 5.00
Nano Banana 2 (Gemini 3.1 Flash Image):
  RPM: 100
  TPM: 200K
  RPD: 1K
Prior Free-tier image quota observation: 0 / 0 / 0
```

This supports the prior R3 Gemini HTTP 429 as an account/quota condition caused by Free-tier image quota zero, rather than a proven application-code defect.

Owner also reported replacing the GitHub Actions `GEMINI_API_KEY` secret with the new Orbis project key. The secret value must never be exposed or persisted. Runtime adoption of the new secret is not yet proven.

No provider request or R4 execution is authorized by this evidence.

---

## Immutable R3 Truth

```text
Execution ID: LIVE-20260909-363F-R3
Run: 34297314995
Execution main: 82ce42116e3f866227dd598814cf79c0b9c640c4
Status: STOPPED / CONSUMED
STOP phase: LIVE-02-GEMINI-IMAGE
OpenAI STORY: SUCCESS
OpenAI usage: 546 prompt / 513 completion
Known committed/actual Orbis UAT cost at STOP: USD 0.0065
Gemini IMAGE: HTTP 429
Gemini retryable: true
Gemini submission_uncertain: false
Conservative calls: 2/6
Vidu: NOT CALLED
ElevenLabs: NOT CALLED
Downstream: NOT STARTED
R3 rerun: FORBIDDEN
```

Issue #63 evidence:
- execution fence comment `5594141834`;
- STOP evidence comment `5594143482`.

The failed Gemini request is counted conservatively as chargeable request #2. The repository does not prove whether Google externally billed that failed request.

---

## Closed Corrective — R3-C1

`P4-WP020-LIVE-R3-C1 — Gemini 429 Quota/Rate-Limit Evidence Corrective`

Closure facts:
- Owner-authorized NO-PAID only;
- PR #78 merged;
- canonical main advanced to `1c63045497eb7ee708cd81876f6bf7a011907f77`;
- exact-head CI and independent review passed;
- provider calls 0;
- spend USD 0.00;
- R3 remains consumed / never rerun;
- R4 remains NOT AUTHORIZED.

---

## Immutable Earlier History

- R1 consumed / HTTP 429 / never rerun.
- R2 consumed / OpenAI PASS / Gemini generic HTTP_ERROR / 2/6 / USD 0.0072 known cost / never rerun.
- R2-C1 merged PR #74, adding durable sanitized HTTP status evidence.
- R3-PRE1 metadata probe run `34291500281` PASS / HTTP 200 / zero generation calls.
- R3 TOOL1 merged PR #77.
- R3 PF1 run `34296382370` PASS / zero provider calls / reservation USD 0.2739.

---

## Next Gate

No active implementation package exists after C1 closure.

After PR #79 C1-CLOSE merges, the next candidate is `P4-WP020-LIVE-R4-PRE1` — NO-PAID runtime readiness validation. It requires separate Owner authorization and must not perform image generation, paid execution, or fence consumption.

If R4-PRE1 later passes, a new R4 paid execution plan still requires a new identity, fresh exact-main authorization, new one-shot fence, and separate Owner run authorization.

No gate auto-authorizes the next one.

---

## Owner-Locked Product Direction

Orbis remains an AI Video Production Orchestrator / Production Control Plane with separate provider boundaries:

```text
CreativeProvider
ImageProvider
VideoProvider
AudioProvider
```

Core V1 modes: `STORY / SHORT / LOOP / SCENE`.
Later architecture only: `PRODUCT / EXPLAINER / PRESENTER / MONTAGE`.

```text
MULTI_PROJECT = REQUIRED
FULL_HISTORY_RETENTION = REQUIRED
AUDITABLE_CHANGES = REQUIRED
NO_SILENT_HISTORY_LOSS = REQUIRED
AUTOMATION_FIRST = REQUIRED
APPROVAL_GATED_AUTOMATION = REQUIRED
GUIDED_FLEXIBILITY = REQUIRED
AUDIO_PRODUCTION_CORE_V1 = REQUIRED
LOCAL_AI = DISALLOWED
CLOUD_AI = REQUIRED
VENDOR_LOCK_IN = DISALLOWED
```
