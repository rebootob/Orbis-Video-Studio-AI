# Active Task Specification

> Canonical location: `project-docs/00_CONTROL/ACTIVE_TASK.md`
>
> Fresh repository truth overrides stale text.

---

## Active Work Package

```text
ACTIVE_WORK_PACKAGE = NONE
STATUS = WAITING FOR OWNER NEXT-GATE AUTHORIZATION
P4-WP020 = ACTIVE / NOT CLOSED
CORE_V1_RELEASE = NOT DECLARED
PAID_LIVE_EXECUTION = NOT AUTHORIZED
```

PRE1 is complete. Completion does not auto-authorize R3 execution tooling or paid/live execution.

---

## Most Recent Completed Gate

`P4-WP020-LIVE-R3-PRE1 — Gemini Access Probe + Resume Contract + Control-Truth Sync`

```text
Status: PASS / COMPLETED
PR: #75
Reviewed PRE1 HEAD: 28f8095d581556b27feed67e27f82c004ea07bbc
Merge commit: dcb831e14b5ece6e56bd7e3c9a61370977c0ca1b
Metadata probe run: 34291500281
Probe result: ACCESS_PROBE_PASS
HTTP status: 200
Model: gemini-3.1-flash-image
generation_request_sent: false
paid_generation_calls: 0
PRE1 spend: USD 0.00
```

The probe proves metadata-level authentication/model visibility only. It does not authorize generation and does not prove that the Gemini image-generation submission path will succeed.

---

## Immutable Prior LIVE Truth

### R1

- consumed / immutable;
- bounded OpenAI request returned HTTP 429;
- never rerun R1.

### R2

- execution ID `LIVE-20260909-BB75-R2`;
- run `34287696335`;
- execution fence consumed;
- OpenAI STORY succeeded;
- Gemini IMAGE returned non-success HTTP surfaced as `HTTP_ERROR`;
- exact historical Gemini HTTP status unavailable;
- conservative chargeable requests consumed = 2/6;
- last known confirmed/committed UAT cost at STOP = USD 0.0072;
- Vidu / ElevenLabs / downstream live proof not executed;
- never rerun R2.

### R2-C1

- PASS / MERGED / CLOSED via PR #74;
- merge commit `d706acacd1f51224c955fb9c8d0d9eab3deda186`;
- future Gemini non-2xx evidence now retains sanitized HTTP status/classification;
- C1 provider calls = 0;
- C1 spend = USD 0.00.

---

## Proposed Next Gate — Not Authorized

The next proposed work is **R3 paid one-shot execution-tooling preparation**, not R3 execution itself.

Draft R3 bounds remain:

```text
OpenAI x1 -> Gemini x1 -> Vidu x1 -> ElevenLabs x3
Maximum chargeable requests: 6
Hard cap: USD 1.00
Sequential only
OpenAI retries: 0
```

Before any R3 tooling implementation, ChatGPT must fresh-review canonical `main` and present a bounded tooling contract for explicit Owner authorization.

R3 execution identity and exact binding main SHA remain unassigned.

---

## Explicitly Forbidden Without a New Owner Gate

- no R3 execution-tooling implementation;
- no OpenAI/Gemini/Vidu/ElevenLabs generation request;
- no R3 paid workflow dispatch;
- no R3 execution fence;
- no R3 paid authorization marker;
- no R1/R2 rerun;
- no release tag;
- no production deployment;
- no Core V1 release declaration.

---

## Roles

```text
Owner = final human authority / authorization / merge / paid-live gates
ChatGPT = Control Plane / Project Lead / Architect / Independent Reviewer
Antigravity = bounded low-credit Execution Plane only when explicitly authorized
Codex = STOP
Claude Code = STOP
```

Contracts:
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_PRE1.md`
- `project-docs/40_DELIVERY/P4_WP020_LIVE_R3_RESUME_CONTRACT.md`
