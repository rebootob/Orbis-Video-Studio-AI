# P4-WP020-R3 Provider Decision — Production ImageProvider

**Status:** ACCEPTED FOR R3 IMPLEMENTATION EVIDENCE  
**Scope:** GAP-S1-02 only  
**Live/Paid calls:** DISALLOWED

## Decision

Select **Gemini API / `gemini-3.1-flash-image`** as the single Core V1 production ImageProvider adapter behind the existing `IImageGenerationProviderAdapter` boundary.

This is an adapter-level implementation choice. Core Project / Scene / Shot semantics remain provider-neutral and `mock_image` remains available for deterministic tests.

## Capability fit

| Existing ImageProvider need | Gemini fit | R3 mapping |
|---|---|---|
| Cloud API + API-key auth | Supported over HTTPS Interactions API | `GEMINI_API_KEY`, base URL/model/timeouts via env/config |
| Storyboard/keyframe generation | Native image generation | synchronous `ImageJobResult(COMPLETED)` with inline bytes |
| 16:9 / 9:16 / 1:1 / 4:3 / 3:4 | Natively supported | pass canonical aspect ratio without crop approximation |
| Multiple continuity references | Supported by Gemini 3 image family, up to bounded reference counts | canonical Orbis asset refs materialized from object storage at dispatch; no base64/presigned URL persisted |
| Sync/async semantics | R3 uses synchronous Interactions path | no fake polling; `check_job_status` explicitly unsupported for this adapter |
| Retry / uncertainty | HTTP/transport classified at adapter boundary | server/ambiguous transport -> `submission_uncertain`; caller reconciliation fencing remains authoritative |
| Output handling | Inline image data | canonical bytes + MIME type; no raw provider body persisted |
| Cost observability | Token usage / configurable pricing evidence | keep core reservation/ledger; do not expose secrets/provider payloads |

## Safety and operational rules

1. Production default resolves to `gemini_image`, never silently to `mock_image`.
2. Missing/invalid credentials return `INVALID_CONFIG`; no fake image fallback.
3. Canonical reference URLs are resolved only through Orbis object storage with project ownership checks; arbitrary URL fetching is not allowed.
4. Reference payload size/count are bounded before provider submission.
5. Unsupported seed/provider-specific fields fail closed rather than being ignored.
6. Raw provider response bodies and API keys are never placed in durable job result data.
7. Provider POST is not automatically retried after an uncertain submission; core `RECONCILIATION_REQUIRED` remains the authority.
8. R3 verification uses mocked HTTP responses only. No paid image generation is authorized.

## Explicit exclusions

- second production ImageProvider;
- ComfyUI / GPU runtime;
- provider model picker UI;
- live provider proof;
- ImageProvider-specific core domain fields;
- changes to R4 AudioProvider scope.

## Evidence sources used for the decision

Verified against current Google Gemini API documentation during R3 implementation on 2026-09-08:

- Interactions API supports image response aspect ratios including 16:9, 9:16, 1:1, 4:3 and 3:4.
- Gemini 3 image generation supports multiple input/reference images.
- `gemini-3.1-flash-image` is a stable image-generation model with image input/output support.
- Current pricing is token-based and therefore runtime cost evidence must remain distinguishable from pre-dispatch estimates.

## Closure condition

This decision alone does not close GAP-S1-02. R3 closes only after adapter/config/factory/reference handling + focused fake-HTTP tests + full exact-head CI + independent review + Owner merge.
