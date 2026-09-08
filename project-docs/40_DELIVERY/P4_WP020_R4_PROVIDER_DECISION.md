# P4-WP020-R4 Provider Capability Decision — Production Audio

> **Date:** 2026-09-08  
> **Scope:** Core V1 VO / DIALOGUE / BGM / SFX / AMBIENCE only  
> **Live paid calls:** NOT AUTHORIZED / NOT USED FOR IMPLEMENTATION PASS

## Decision

Select **one production provider: ElevenLabs** behind the existing provider-neutral `IAudioProviderAdapter` boundary.

Canonical provider id:

```text
elevenlabs_audio
```

The adapter performs capability routing internally by canonical `audio_type`; Project/Scene/Shot/UI semantics remain provider-neutral.

## Capability matrix

| Core V1 audio type | ElevenLabs production route | Decision |
|---|---|---|
| VO | Text to Speech `/v1/text-to-speech/{voice_id}` using `eleven_v3` | SUPPORTED |
| DIALOGUE | Text to Speech `/v1/text-to-speech/{voice_id}` using `eleven_v3` | SUPPORTED |
| BGM | Music `/v1/music` using `music_v2` | SUPPORTED |
| SFX | Sound Effects `/v1/sound-generation` using `eleven_text_to_sound_v2` | SUPPORTED |
| AMBIENCE | Sound Effects `/v1/sound-generation`, loop enabled by default | SUPPORTED |
| ORIGINAL_AUDIO | Existing imported/embedded media path | NOT A GENERATION REQUIREMENT |

Eleven v3 supports 70+ languages including Thai. Voice cloning remains intentionally out of Core V1 scope.

## Why one provider

The bounded R4 contract prefers one provider when it truthfully covers every required type. ElevenLabs currently exposes production APIs for TTS, music and sound effects, so a second production audio vendor would add secrets, routing, cost and failure surface without closing an additional Core V1 requirement.

## Bounded defaults

```text
TTS model     = eleven_v3
Music model   = music_v2
SFX model     = eleven_text_to_sound_v2
Output        = mp3_44100_128
```

Speech requires an explicitly configured voice id. Missing API key or missing voice for VO/DIALOGUE fails closed; runtime never falls back to `mock_audio`.

## Cost evidence and reservation

Current ElevenAPI public USD rates captured for this decision:

```text
Eleven v3 TTS     = USD 0.10 / 1,000 characters
Music             = USD 0.15 / minute
Sound Effects     = USD 0.12 / minute
```

Rates are stored as environment/config values, not domain constants. R4 adds a provider-neutral pre-dispatch `estimate_cost(params)` hook so the hard budget gate reserves against the exact canonical request instead of legacy fixed mock estimates.

For TTS, the adapter reconciles actual billed character count from the provider `character-cost` response header. For bounded Music/SFX/Ambience requests with explicit duration, actual cost is derived from configured current per-minute API pricing and exact requested duration. Missing required cost evidence fails into reconciliation rather than fabricating confirmed cost.

## Failure / uncertainty contract

- Local validation or deterministic provider rejection before accepted generation -> FAILED, non-uncertain, no invented charge.
- Connect failure before accepted response -> retryable FAILED, non-uncertain.
- Read/write/network timeout after POST or HTTP 5xx -> `submission_uncertain=true`; Core must keep reservation and require reconciliation.
- Raw provider error bodies, API keys and arbitrary response payloads are not persisted.
- Synchronous completion returns MP3 bytes and an allowlisted provider request/trace id when available.

## Explicit exclusions

- no voice cloning;
- no second production audio provider;
- no DAW/editor/plugin expansion;
- no advanced EQ/compressor/limiter;
- no paid/live generation for R4 implementation evidence;
- no WP020-A, WP020-LIVE or release declaration.

## Sources checked 2026-09-08

- ElevenAPI pricing: https://elevenlabs.io/pricing/api
- Text to Speech API: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- Music API: https://elevenlabs.io/docs/api-reference/music/compose
- Sound Effects API: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- ElevenLabs model languages: https://elevenlabs.io/docs/overview/models
- Music v2 changelog: https://elevenlabs.io/docs/changelog/2026/6/15

## R4 acceptance interpretation

R4 can claim implementation PASS without a live paid call only if deterministic mocked provider tests plus full regression prove:

1. production adapter is registered/configuration-selectable;
2. VO/DIALOGUE/BGM/SFX/Ambience all route through canonical AudioProvider boundary;
3. missing credentials/voice and unsupported inputs fail explicitly;
4. pre-dispatch budget reservation uses provider estimate;
5. completed production responses preserve asset lineage and auditable cost;
6. ambiguous submission remains fenced for reconciliation;
7. existing mock provider and audio mix/history/lock/version behavior remain regression-clean.
