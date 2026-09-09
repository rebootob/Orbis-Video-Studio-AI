# P4-WP020-LIVE-R4-C1 — Vidu Failure Evidence & Billing Reconciliation (NO-PAID)

## 0. Completion Status

```text
Status: PASS / MERGED / COMPLETE
C1 PR: #85
C1 exact reviewed HEAD: c6f02fe56d4248011b0ef0cb96910d6997195e60
C1 merge commit: 4ff697c9cd0698406ce248e95ec4a69df8cd2fc5
C1-CLOSE PR: #86
C1-CLOSE exact reviewed HEAD: cb3498a7e7b3affe5b49ed96c0081e1e92621f3d
C1-CLOSE merge commit: 37bc4584eaa14bcf1d01243364548b2a3c39bcbb
Canonical main at R4-C1-CLOSE-R1 start: 37bc4584eaa14bcf1d01243364548b2a3c39bcbb
Active work package after C1 closure: NONE
R5 identity: NONE / NOT AUTHORIZED
C1 provider calls: 0
C1 spend added: USD 0.00
```

This document is now a historical contract/evidence record. It does not authorize any new provider request, billing adjustment, execution identity, fence, paid/live workflow, release, tag or deployment.

---

## 1. Authorization

Owner authorized:

```text
P4-WP020-LIVE-R4-C1 — Vidu Failure Evidence & Billing Reconciliation (NO-PAID)
```

This corrective was evidence-quality and implementation hardening only. It authorized no external provider request and no future LIVE execution identity.

```text
Repository: rebootob/Orbis-Video-Studio-AI
Canonical branch: main
Canonical main at C1 start: b1538f655bf526384845c1e8c536ad6fddc66ca7
C1 branch: ai/p4-wp020-live-r4-c1
R4 execution ID: LIVE-20260909-DE17-R4
C1 provider calls: 0
C1 spend added: USD 0.00
```

---

## 2. Immutable R4 Failure Evidence

R4 one-shot paid execution:

```text
Run: 34316188814
Workflow: WP020 LIVE R4 Paid One-Shot Execution
Head SHA: b1538f655bf526384845c1e8c536ad6fddc66ca7
Conclusion: FAILURE / STOP
Fence: CONSUMED
Fence Issue #63 comment: 5596464603
STOP Issue #63 comment: 5596467391
STOP phase: LIVE-03-VIDU-VIDEO
Conservative chargeable calls: 3 / 6
Last known committed/actual Orbis UAT cost: USD 0.0738
```

Provider sequence reached:

1. OpenAI Story — SUCCESS;
2. Gemini Image — SUCCESS;
3. Vidu Video — terminal provider state `FAILED`;
4. ElevenLabs TTS — NOT CALLED;
5. ElevenLabs Music — NOT CALLED;
6. ElevenLabs Ambience — NOT CALLED.

R4 is permanently consumed and MUST NEVER BE RERUN.

---

## 3. Evidence Gap Identified

The R4 sanitized failure artifact retained a Vidu `GenerationJob` with:

```text
status = FAILED
job_type = VIDEO
cost_usd = 0.15
```

Source inspection establishes that `GenerationJob.cost_usd` is populated from the pricing estimate when the job is created. It is not direct evidence that the external provider charged USD 0.15.

The previous Vidu failure boundary also lost provider-native reconciliation metadata because:
- terminal `state=failed` returned before preserving a returned task identity;
- raw provider bodies are correctly excluded for security, but the durable safe result boundary did not retain typed safe fields such as provider status/error code/credits.

Therefore the current billing truth remains:

```text
Internal Vidu job estimate: USD 0.15 / ESTIMATED
Last known committed/actual Orbis UAT cost at R4 STOP: USD 0.0738
External billing for failed Vidu task: UNKNOWN / RECONCILIATION REQUIRED
```

No statement that the failed task was free or charged USD 0.15 is supported without provider-side evidence.

---

## 4. Historical Corrective Contract

C1 was allowed to modify the existing provider-neutral evidence boundary only as needed to:

- extend `ProviderJobResult` with optional typed reconciliation metadata;
- preserve sanitized Vidu task/provider-job identity for explicit terminal failures when supplied by Vidu;
- preserve sanitized provider-native state, safe error code and numeric credits;
- keep raw provider bodies, nested error text, headers, prompts and credentials excluded;
- persist those typed safe fields through `safe_result()` into durable job evidence;
- make R4 generation-job failure evidence expose `estimated_cost_usd` + `cost_status=ESTIMATED` instead of ambiguous `cost_usd`;
- mark failed Vidu external billing as `UNKNOWN`;
- add mocked regression tests proving the security and reconciliation behavior;
- synchronize control/delivery documentation.

C1 was forbidden to:

- call OpenAI, Gemini, Vidu or ElevenLabs;
- use Vidu metadata endpoints or billing APIs;
- rerun R4;
- dispatch any LIVE workflow;
- create R5 or any later execution identity;
- create or consume a new execution fence;
- retrospectively change ledger/billing values without evidence;
- release, tag or deploy.

Those restrictions remain effective for any action not separately Owner-authorized after C1 closure.

---

## 5. Implementation Files

Bounded C1 implementation was allowed to touch:

```text
backend/app/providers/base.py
backend/app/providers/safety.py
backend/app/providers/vidu.py
.github/scripts/wp020_live_r4_contract.py
backend/tests/test_wp020_live_r4_c1.py
project-docs/00_CONTROL/* relevant control files
project-docs/40_DELIVERY/WORK_PACKAGES.md
project-docs/40_DELIVERY/P4_WP020_LIVE_R4_C1.md
```

The frozen R3 runner `.github/scripts/wp020_live_uat_r3.py` MUST NOT be modified. Its reviewed Git blob identity remains immutable. R4 itself is consumed; C1 improved future evidence behavior and recorded R4 truth, not R4 execution.

---

## 6. Security / Evidence Rules

Allowed durable provider metadata is non-content only:
- safe provider task/job identifier;
- normalized provider state;
- safe provider error code;
- numeric non-negative provider credits;
- existing typed HTTP/retry/uncertainty classifications.

Forbidden durable evidence includes:
- raw provider response body;
- provider headers;
- authorization/API keys/tokens/secrets;
- raw provider error message;
- prompts or generated text content added solely for failure evidence.

`provider_credits` is a provider-native usage value and MUST NOT be relabeled as USD cost unless a separately validated conversion/billing rule exists.

---

## 7. Billing Reconciliation State

Provider-side evidence remains required to resolve whether the failed R4 Vidu task created a charge.

Target execution interval:

```text
R4 run start: 2026-09-09T05:45:42Z
R4 STOP record: 2026-09-09T05:47:19Z
```

Acceptable future reconciliation evidence can include a sanitized Vidu Usage/Billing view or another provider-side record that can be matched to this execution interval/task identity without exposing credentials.

Until accepted:

```text
R4_VIDU_EXTERNAL_BILLING = UNKNOWN / RECONCILIATION REQUIRED
```

No billing adjustment is authorized by this historical C1 contract or by its closure.

---

## 8. Historical Acceptance Criteria — SATISFIED

C1 reached Owner merge readiness and completion with:

- no external provider call during C1;
- Vidu terminal failure preserving safe task identity when present;
- safe provider state/error-code/credits surviving durable evidence;
- unsafe/raw provider content remaining excluded;
- failed Vidu job amount explicitly labeled an estimate;
- external billing explicitly `UNKNOWN`, not guessed;
- focused regression tests passing;
- exact-head Backend CI `34323625029` = SUCCESS;
- backend suite = 538 passed / 2 skipped / 3 warnings;
- fresh-head and from-revision-010 migrations = SUCCESS;
- exact-head Frontend CI `34323625048` = SUCCESS;
- independent review = PASS;
- C1 merge via PR #85;
- C1 closure/control sync via PR #86;
- C1 provider calls = 0;
- C1 spend added = USD 0.00.

---

## 9. Historical Stop Rule — SATISFIED

The original C1 stop rule required exact-head CI, independent review and explicit Owner merge decision. Those gates were satisfied and C1 was merged through PR #85, followed by the Owner-authorized C1 closure sync through PR #86.

Current post-closure state:

```text
ACTIVE_WORK_PACKAGE = NONE
P4-WP020 = ACTIVE / NOT CLOSED
R4 = STOPPED / CONSUMED / NEVER RERUN
R4_VIDU_EXTERNAL_BILLING = UNKNOWN / RECONCILIATION REQUIRED
R5_IDENTITY = NONE / NOT AUTHORIZED
CORE_V1_RELEASE = NOT DECLARED
```

Any provider-side billing disposition, R5/readiness work, paid authorization marker, execution fence, provider call, paid/live workflow, release, tag or deploy requires a separate explicit Owner authorization. No completed C1/C1-CLOSE gate auto-authorizes the next one.
