# Core V1 Audio Production Model

> **Canonical Document Location:** [`project-docs/30_PRODUCT/AUDIO_EDITING_MODEL.md`](project-docs/30_PRODUCT/AUDIO_EDITING_MODEL.md)

---

## 1. Product Lock

Audio Production is a **Core V1 requirement**. Orbis must support useful end-to-end audio production without becoming a full DAW.

```text
VO = REQUIRED
BGM = REQUIRED
SFX = REQUIRED
AMBIENCE = REQUIRED
BASIC_AUTO_DUCKING = REQUIRED
BATCH_AUDIO_AUTOMATION = REQUIRED
ADVANCED_AUDIO_EDITING = OUT OF V1
```

---

## 2. Audio Production Flow

```text
Story / Scene / Shot
-> Analyze audio needs
-> VO script / dialogue plan
-> BGM suggestion / assignment
-> SFX / ambience plan
-> Generate and/or import audio assets
-> Basic auto mix / ducking
-> Preview
-> User review
-> Final assembly / render
```

The preferred UX is project-level automation such as `Generate Audio Plan`, `Generate All VO`, `Apply BGM`, `Assign SFX / Ambience` and `Auto Mix`, with selective correction when needed.

---

## 3. Audio Stem Categories

| Track Type | Typical Source | Core V1 Behavior |
| :--- | :--- | :--- |
| Dialogue / Dubbing | TTS / imported / recorded | assign to scene/shot, volume, mute, timing |
| Voice Over (VO) | TTS / imported / recorded | batch generate/assign, volume, timing |
| Original Clip Audio | imported video | retain/mute/basic volume |
| Background Music (BGM) | stock / AI music / import | assign by project/scene, volume, fade, ducking |
| Sound Effects (SFX) | library / AI / import | assign to scene/shot, volume, timing |
| Ambience | library / AI / import | assign to scene/shot, volume, fade |

Provider selection must remain behind an AudioProvider/service boundary rather than being hard-coded into core domain/UI logic.

---

## 4. Basic Mixing Requirements

Core V1 requires only practical production controls:

- volume
- mute/unmute
- fade in/out
- timing/placement per Scene/Shot where applicable
- basic speech-over-music auto-ducking
- preview before final render

Auto-ducking implementation details may vary by renderer/provider. The product contract should specify the desired outcome (speech remains intelligible and BGM returns smoothly), not lock V1 to one hard-coded compressor threshold or exact DSP algorithm unless separately validated.

---

## 5. Subtitle Support

Where applicable:

- generate subtitle timing from approved VO/dialogue timing
- export SRT/VTT sidecars
- support hard-burned subtitles in approved render/export presets
- preserve language/subtitle variants as project/output metadata

---

## 6. History, Cost & Safety

- Generated/imported audio assets belong to the Project and remain recoverable through history/version lineage.
- Regeneration must not silently destroy previously approved audio.
- Batch generation must use durable jobs/retry/resume where appropriate.
- Known provider cost should be surfaced before expensive batch work when available; unknown cost remains explicitly UNKNOWN.
- Locks/approval should protect accepted voice/music/timing choices from accidental overwrite.

---

## 7. Explicitly Outside Core V1

Core V1 does not require:

- advanced waveform editor
- deep EQ/compressor/limiter controls
- complex keyframe automation
- plugin ecosystem
- professional multi-bus routing
- advanced mastering suite
- 5.1 production workflow

These may be considered for V1.x or later without changing the Core V1 audio-production contract.
