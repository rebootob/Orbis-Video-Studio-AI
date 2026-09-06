# Video Production Modes

> Canonical definition of Orbis production modes. Video Mode is a provider-neutral orchestration concept, not a provider selection or output preset.

---

## 1. Core V1 Modes

```text
STORY
SHORT
LOOP
SCENE
```

### STORY

Full narrative production:

```text
Brief / Documents -> Story -> Script -> Scenes -> Shots
```

Use for corporate storytelling, training narratives, brand films, mini movies and other continuity-heavy productions.

Default characteristics:
- Story required
- multi-scene supported
- screenplay supported
- dialogue / VO supported
- high continuity priority

### SHORT

Compact short-form production:

```text
Brief / Concept -> Hook / Compact Structure -> Scene -> Shots
```

Typical use: Shorts, Reels, TikTok-style vertical content, short campaigns and internal communication.

Default characteristics:
- Story optional
- typical duration 15-60 seconds
- preferred default aspect ratio 9:16
- strong hook
- fast pacing
- subtitle priority high

SHORT is not inherently tied to a specific platform.

### LOOP

Seamless-loop production:

```text
Prompt / References -> Loop Specification -> Shot(s)
```

Default characteristics:
- Story optional
- Script optional
- typical duration 4-15 seconds
- seamless start/end required
- continuity priority very high
- dialogue normally off

Use for ambience, LED/display backgrounds, website motion and social loops.

### SCENE

Standalone scene production:

```text
Brief / Scene Description -> Scene -> 1-N Shots
```

Use when a creator needs a single logical scene or shot sequence without constructing a full Story.

---

## 2. Architecture-Ready Future Modes

```text
PRODUCT
EXPLAINER
PRESENTER
MONTAGE
```

These modes must be possible without redesigning the core platform, but they are not authorized for implementation merely by appearing in architecture documentation.

Possible later extensions include MUSIC_VIDEO, SLIDESHOW, BROLL_PACK and SOCIAL_AD_TEMPLATE.

---

## 3. Domain Rule

`Project -> Story` is optional.

The selected `video_mode` determines which creative layers are required. Core code must not assume that every Project has a Story or Script.

Suggested Project-level mode fields:

```text
video_mode
purpose
target_platform
target_duration_seconds
preferred_aspect_ratio
mode_config
```

Configuration inheritance remains:

```text
Project -> Scene -> Shot
```

---

## 4. Video Mode vs Output Intent

Keep these independent:

### Video Mode
Defines production structure.

### Purpose
Examples: TRAINING, MARKETING, SOCIAL, PRESENTATION, BACKGROUND, PRODUCT, INTERNAL_COMMS, CUSTOM.

### Target Platform
Examples: YOUTUBE, TIKTOK, REELS, FACEBOOK, LINKEDIN, DISPLAY, INTERNAL, CUSTOM.

### Output Properties
Examples: aspect ratio, language, subtitle profile, bitrate/resolution and render preset.

A STORY project may export 16:9, 9:16 and 1:1 variants from the same project.

---

## 5. Shared Architecture Across Modes

All modes reuse the same platform capabilities where applicable:

- Reference Library and continuity rules
- Scene / Shot entities
- hybrid imported/generated assets
- provider abstraction
- durable generation queue
- asset locking
- selective regeneration safety
- cost/usage controls
- audio/timeline/render layers
- human approval
- multi-output export

No mode may directly call Vidu or another provider.

---

## 6. Work Package Routing

P2-WP007 is closed and remains provider/queue scope only.

Earliest planned base Video Mode implementation is P2-WP008, together with Hybrid Shot Engine and Asset Lock Machine.

P2-WP008 remains PROPOSED / NOT AUTHORIZED until explicit Owner approval.
