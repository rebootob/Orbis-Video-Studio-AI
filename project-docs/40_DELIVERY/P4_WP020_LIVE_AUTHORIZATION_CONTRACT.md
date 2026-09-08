# P4-WP020-LIVE — Bounded Live Provider UAT Authorization Contract

**Status:** PROPOSED / NOT AUTHORIZED  
**Base main:** `0ba933c23d244337af4bd5f7ce1188f22a091861`  
**Purpose:** minimum real-provider proof after P4-WP020-A zero-billing integration PASS.

## 1. Authorization boundary

This document does **not** authorize paid/live execution by itself.

Owner authorization must explicitly reference this contract (or restate equivalent bounds) before any live Creative/Image/Video/Audio provider request is dispatched.

No release tag or Core V1 release declaration is authorized by WP020-LIVE.

## 2. Allowed providers and exact bounded calls

Maximum chargeable provider requests for the initial LIVE UAT: **6**.

1. **OpenAI CreativeProvider — 1 request maximum**
   - model: `gpt-4o`
   - operation: one STORY generation only
   - profile: `FAST`
   - target duration: <= 30 seconds
   - source brief: <= 2,000 characters
   - no document/reference expansion for this first live creative call
   - `OPENAI_MAX_RETRIES=0` for this UAT call

2. **Gemini ImageProvider — 1 request maximum**
   - provider: `gemini_image`
   - model: `gemini-3.1-flash-image`
   - output size: 1K only
   - one keyframe/storyboard image only
   - no more than one small UAT continuity reference if a project-owned reference is used

3. **Vidu VideoProvider — 1 request maximum**
   - provider: `vidu`
   - model: `viduq2`
   - text-to-video only for the first live proof
   - duration: exactly 4 seconds
   - resolution: 720P
   - no off-peak assumption is used for the budget calculation
   - one idempotency key; no second generation after uncertain outcome

4. **ElevenLabs AudioProvider — 3 requests maximum**
   - provider: `elevenlabs_audio`
   - one Thai VO/TTS request, <= 150 characters
   - one BGM request, <= 10 seconds
   - one AMBIENCE/SFX-endpoint request, <= 3 seconds
   - no voice cloning
   - configured `ELEVENLABS_DEFAULT_VOICE_ID` is required for VO

No other paid provider, model, shot, regeneration, retry-after-uncertain, or extra audio/image/video generation is authorized in the initial LIVE run.

## 3. Hard cost boundary

Dedicated UAT project hard budget:

```text
budget_limit = USD 1.00
budget_currency = USD
budget_threshold_percentage = 80
```

Before dispatch, the UAT environment must load explicit pricing rules for all provider paths that rely on the generic pricing registry. The runtime pricing snapshot for this authorization is:

```text
OpenAI gpt-4o
  input  = USD 0.0025 / 1K tokens
  output = USD 0.0100 / 1K tokens

Gemini gemini-3.1-flash-image
  existing Core V1 1K reservation = USD 0.08 / generation
  actual cost reconciled from provider token usage

Vidu viduq2 text-to-video 720P
  exact bounded-scenario rule for 4s test:
  cost_per_generation = USD 0.05
  cost_per_second     = USD 0.025
  expected reservation = USD 0.15 for exactly 4 seconds

ElevenLabs
  TTS v3        = USD 0.10 / 1,000 characters
  Music         = USD 0.15 / minute
  Sound Effects = USD 0.12 / minute
```

If pricing cannot be loaded/validated before dispatch, LIVE execution must STOP before the first paid call.

The USD 1.00 Owner cap is a maximum authorization, not a target spend. Expected initial run spend is materially below the cap.

## 4. Required UAT environment preflight

Use a dedicated non-production UAT project/environment only.

Required credential presence checks (presence only; values must never be logged):

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `VIDU_API_KEY`
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_DEFAULT_VOICE_ID`
- database/object-storage credentials required by the selected UAT runtime

Preflight must also verify:

- current repository/app build is derived from canonical main at or after the authorized base SHA;
- UAT project committed cost starts at 0 or an explicitly reviewed known value;
- project hard budget is USD 1.00;
- provider defaults resolve to real adapters, never mock/fake adapters;
- OpenAI live retry count is zero;
- no active/reconciliation-required GenerationJob exists for the selected live shot;
- no secrets appear in logs, job payloads, archive evidence or screenshots.

Missing/invalid prerequisite => STOP with no paid call.

## 5. Live scenario sequence

Execute sequentially, never in parallel, so each paid call can be reviewed before the next provider is reached.

### LIVE-01 — Creative

Create one isolated STORY UAT project from the bounded brief and run one OpenAI story generation.

Evidence:
- provider/model audit;
- valid persisted Story/Scene/Shot lineage as applicable;
- UsageLedger entry with token-based cost evidence;
- no automatic paid retry.

### LIVE-02 — Image

Generate one 1K Gemini keyframe for one approved UAT shot.

Evidence:
- durable project-owned IMAGE Asset;
- provider usage/cost evidence;
- no raw provider response or credential persistence.

### LIVE-03 — Video

Generate exactly one 4-second 720P Vidu Q2 text-to-video shot.

Evidence:
- one provider task identity;
- durable VIDEO Asset materialized into Orbis object storage;
- GenerationJob -> Asset -> Shot lineage;
- no duplicate provider submission;
- UsageLedger/provider event evidence.

### LIVE-04 — Audio

Generate the three bounded ElevenLabs samples: Thai VO, short BGM, short ambience.

Evidence:
- durable AUDIO assets and canonical audio types;
- provider trace/cost evidence;
- missing/ambiguous cost becomes reconciliation rather than fabricated truth.

### LIVE-05 — Integrated downstream proof

Using the real provider assets above, complete the non-provider-paid downstream path:

`Assembly -> Subtitle/SRT -> QC -> Human Approval -> Render -> 16:9 / 9:16 / 1:1 -> .orbis export/validate/CLONE`

No additional paid generation is authorized for LIVE-05.

## 6. Mandatory STOP conditions

STOP immediately and do not dispatch another paid provider call if any occurs:

- project committed cost reaches or exceeds USD 1.00;
- pricing rule/estimate is UNKNOWN before a chargeable dispatch;
- credential/config validation fails;
- any provider submission becomes uncertain or `RECONCILIATION_REQUIRED`;
- unexpected second active job/idempotency conflict appears;
- paid request is retried after an ambiguous outcome;
- durable output materialization fails after provider success;
- UsageLedger cannot represent the provider event/cost truthfully;
- project isolation/history/approval gate fails;
- secret/API-key leakage is detected;
- any new S0/S1 release blocker is proven.

After STOP, only evidence/reconciliation review is authorized. A fresh Owner authorization is required before any additional paid generation.

## 7. Explicit exclusions

- no batch live generation;
- no provider breadth beyond OpenAI/Gemini/Vidu/ElevenLabs already accepted for Core V1;
- no second video shot;
- no regeneration for quality preference;
- no voice cloning;
- no ComfyUI/cloud GPU;
- no Post-Core-V1 modes/integrations;
- no production deployment/release tag;
- no cleanup that destroys UAT evidence before review.

## 8. PASS criteria

P4-WP020-LIVE can return PASS only when:

1. all authorized real-provider calls stay within the exact job/duration/input limits;
2. total committed UAT project cost remains <= USD 1.00;
3. every successful provider result becomes durable Orbis truth with correct lineage;
4. chargeable events are represented by auditable cost/UsageLedger evidence;
5. no ambiguous provider outcome is silently retried;
6. downstream Assembly/Subtitle/QC/Approval/Render/Multi-output/.orbis path succeeds with the live assets;
7. no S0/S1 blocker is found;
8. Owner-observable UAT evidence is retained for final review.

After PASS, STOP for P4-WP020-CLOSE / final Core V1 release review and Owner release decision.
