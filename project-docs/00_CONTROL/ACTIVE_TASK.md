# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = P4-WP020-LIVE-R3-TOOL1
TITLE = Bounded One-Shot Execution Tooling Preparation
TYPE = NO-PAID / CODE + TEST + CONTROL-DOC
STATUS = OWNER AUTHORIZED / IMPLEMENTATION + CI REVIEW
BRANCH = ai/p4-wp020-live-r3-tool1
BASE_MAIN = 363ffe6a0bd325c7c557b80daa665ee3575df6f8
R3_EXECUTION_ID = LIVE-20260909-363F-R3
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
PAID_LIVE_EXECUTION = NOT AUTHORIZED
TOOL1_PROVIDER_CALLS = 0
TOOL1_SPEND_AUTHORIZATION = USD 0.00
```

---

## Authorized TOOL1 Scope

1. Manual-only R3 no-paid preflight workflow and script.
2. Manual-only R3 one-shot paid workflow, inert until later exact Owner paid/live authorization.
3. Exact Owner marker + unused identity + one-shot fence controls.
4. New R3 runner for the locked six-call full chain.
5. Exact sequential call counter and USD 1.00 fail-closed budget guard.
6. Durable sanitized failure evidence before ephemeral runtime teardown.
7. Tests for identity/SHA/fence/call order/call ceiling/budget/non-success/reconciliation/secret-leak behavior.
8. Control-document synchronization only.

Locked future paid sequence:

```text
1 OpenAI STORY
2 Gemini IMAGE
3 Vidu VIDEO
4 ElevenLabs Thai TTS
5 ElevenLabs BGM
6 ElevenLabs Ambience
```

No regeneration, quality retry, second shot, provider expansion, release, deploy, or R1/R2 reuse is authorized.

---

## Immutable Prior Truth

- R1 = consumed / HTTP 429 / never rerun.
- R2 = consumed / OpenAI PASS / Gemini `HTTP_ERROR` STOP / 2/6 conservative calls / last known committed cost USD 0.0072 / never rerun.
- R2-C1 = PASS / merged PR #74 / sanitized Gemini HTTP evidence path added / zero provider calls.
- R3-PRE1 = PASS / completed / probe run `34291500281` / HTTP 200 / `generation_request_sent=false` / zero provider calls.

---

## TOOL1 Stop / Review Rule

TOOL1 must stop after implementation + exact-head CI + independent review and wait for Owner merge decision.

Even if TOOL1 is merged:

- do not dispatch R3 no-paid preflight without the next operational gate;
- do not record `FRESH_OWNER_AUTHORIZED_R3` automatically;
- do not write `EXECUTION_STARTED: LIVE-20260909-363F-R3` automatically;
- do not dispatch the paid R3 workflow;
- do not declare P4-WP020 or Core V1 closed/released.

Required later sequence:
`Owner merge -> fresh no-paid preflight -> fresh exact-SHA Owner paid authorization -> separate Owner run authorization -> R3 LIVE`.

Contracts:
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_TOOL1.md`
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`
