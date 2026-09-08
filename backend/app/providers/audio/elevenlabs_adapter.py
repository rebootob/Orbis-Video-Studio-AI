"""ElevenLabs production AudioProvider adapter for Core V1.

One provider covers the bounded Core V1 audio surface:
- VO / DIALOGUE -> Text to Speech
- BGM -> Music
- SFX / AMBIENCE -> Sound Effects

All provider calls are synchronous at this boundary. Raw response bodies and
secret-bearing provider errors are never persisted.
"""
import math
import re
from typing import Any, Dict, Optional
from urllib.parse import quote, urlsplit

import httpx

from app.core.config import settings
from app.providers.audio.base import (
    AudioGenerationParams,
    AudioJobResult,
    AudioProviderCapabilities,
    IAudioProviderAdapter,
)
from app.providers.safety import contains_secret


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,255}$")
_VOICE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,255}$")
_ALLOWED_OUTPUT_FORMAT = "mp3_44100_128"
_SUPPORTED_TYPES = {"VO", "DIALOGUE", "BGM", "SFX", "AMBIENCE"}


class ElevenLabsAudioProviderAdapter(IAudioProviderAdapter):
    """Single-vendor capability router behind the canonical AudioProvider boundary."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        default_voice_id: Optional[str] = None,
        **_: Any,
    ) -> None:
        self._api_key = settings.ELEVENLABS_API_KEY if api_key is None else api_key
        self._base_url = (base_url or settings.ELEVENLABS_BASE_URL).rstrip("/")
        self._timeout_seconds = (
            settings.ELEVENLABS_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        )
        self._default_voice_id = (
            settings.ELEVENLABS_DEFAULT_VOICE_ID if default_voice_id is None else default_voice_id
        )
        self._tts_model = settings.ELEVENLABS_TTS_MODEL
        self._music_model = settings.ELEVENLABS_MUSIC_MODEL
        self._sfx_model = settings.ELEVENLABS_SFX_MODEL
        self._output_format = settings.ELEVENLABS_OUTPUT_FORMAT

    @property
    def provider_id(self) -> str:
        return "elevenlabs_audio"

    def get_capabilities(self) -> AudioProviderCapabilities:
        return AudioProviderCapabilities(
            provider_id=self.provider_id,
            supported_audio_types=["VO", "DIALOGUE", "BGM", "SFX", "AMBIENCE"],
            supports_tts=True,
            supports_music=True,
            supports_sfx=True,
            supports_voice_cloning=False,
            supported_formats=["audio/mpeg"],
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            key = config.get("api_key", self._api_key)
            parsed = urlsplit(self._base_url)
            rates = (
                settings.ELEVENLABS_TTS_COST_PER_1K_CHARS_USD,
                settings.ELEVENLABS_MUSIC_COST_PER_MINUTE_USD,
                settings.ELEVENLABS_SFX_COST_PER_MINUTE_USD,
            )
            return bool(
                isinstance(key, str)
                and key.strip()
                and "\n" not in key
                and "\r" not in key
                and parsed.scheme == "https"
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and not parsed.query
                and not parsed.fragment
                and isinstance(self._timeout_seconds, (int, float))
                and math.isfinite(self._timeout_seconds)
                and 0 < float(self._timeout_seconds) <= 120
                and self._tts_model == "eleven_v3"
                and self._music_model == "music_v2"
                and self._sfx_model == "eleven_text_to_sound_v2"
                and self._output_format == _ALLOWED_OUTPUT_FORMAT
                and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in rates)
            )
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _failure(
        code: str,
        *,
        status_code: Optional[int] = None,
        retryable: bool = False,
        uncertain: bool = False,
        job_id: str = "",
        cost_usd: Optional[float] = None,
    ) -> AudioJobResult:
        return AudioJobResult(
            provider_job_id=job_id,
            status="FAILED",
            error_code=code,
            error_message=code,
            status_code=status_code,
            retryable=retryable,
            submission_uncertain=uncertain,
            cost_usd=cost_usd,
        )

    @staticmethod
    def _request_id(response: httpx.Response, clip_id: str) -> str:
        for key in ("request-id", "x-request-id", "x-trace-id"):
            value = response.headers.get(key)
            if isinstance(value, str) and _SAFE_ID_RE.fullmatch(value):
                return value
        return f"eleven-sync-{clip_id}"

    @staticmethod
    def _prompt(params: AudioGenerationParams) -> Optional[str]:
        prompt = (params.prompt or "").strip()
        if not prompt or len(prompt) > 5000 or contains_secret(prompt):
            return None
        return prompt

    def _voice_id(self, params: AudioGenerationParams) -> Optional[str]:
        extras = params.provider_specific_params or {}
        voice_id = params.voice_id or extras.get("voice_id") or self._default_voice_id
        if not isinstance(voice_id, str) or not _VOICE_ID_RE.fullmatch(voice_id):
            return None
        return voice_id

    def estimate_cost(self, params: AudioGenerationParams) -> Optional[float]:
        prompt = self._prompt(params)
        if not prompt or params.audio_type not in _SUPPORTED_TYPES:
            return None

        if params.audio_type in ("VO", "DIALOGUE"):
            # Eleven v3 is billed per character. Use the exact request text for
            # pre-dispatch reservation; actual billed characters come from the
            # response header and are reconciled after completion.
            return round(
                (len(prompt) / 1000.0) * float(settings.ELEVENLABS_TTS_COST_PER_1K_CHARS_USD),
                6,
            )

        duration = params.duration_seconds
        if not isinstance(duration, (int, float)) or not math.isfinite(duration):
            return None
        duration = float(duration)
        if params.audio_type == "BGM":
            if not 3.0 <= duration <= 600.0:
                return None
            rate = float(settings.ELEVENLABS_MUSIC_COST_PER_MINUTE_USD)
        else:
            if not 0.5 <= duration <= 30.0:
                return None
            rate = float(settings.ELEVENLABS_SFX_COST_PER_MINUTE_USD)
        return round((duration / 60.0) * rate, 6)

    def _validate_extras(self, params: AudioGenerationParams) -> Optional[Dict[str, Any]]:
        extras = params.provider_specific_params or {}
        if params.audio_type in ("VO", "DIALOGUE"):
            allowed = {"voice_id"}
        elif params.audio_type == "AMBIENCE":
            allowed = {"loop", "prompt_influence"}
        elif params.audio_type == "SFX":
            allowed = {"prompt_influence"}
        else:
            allowed = set()
        if set(extras) - allowed:
            return None
        return extras

    async def _post_binary(
        self,
        path: str,
        *,
        params: AudioGenerationParams,
        payload: Dict[str, Any],
        query: Optional[Dict[str, Any]] = None,
    ) -> AudioJobResult:
        estimate = self.estimate_cost(params)
        if estimate is None:
            return self._failure("INVALID_PARAMETERS", cost_usd=0.0)

        headers = {"xi-api-key": self._api_key, "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=float(self._timeout_seconds)) as client:
                response = await client.post(
                    self._base_url + path,
                    json=payload,
                    headers=headers,
                    params=query,
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            return self._failure("CONNECTION_ERROR", retryable=True, cost_usd=0.0)
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.NetworkError):
            return self._failure("TRANSPORT_ERROR", retryable=True, uncertain=True)
        except Exception:
            return self._failure("TRANSPORT_ERROR", uncertain=True)

        request_id = self._request_id(response, params.clip_id)
        if response.status_code not in (200, 201):
            retryable = response.status_code == 429 or response.status_code in (500, 502, 503, 504)
            return self._failure(
                "HTTP_ERROR",
                status_code=response.status_code,
                retryable=retryable,
                uncertain=response.status_code >= 500,
                job_id=request_id,
                cost_usd=None if response.status_code >= 500 else 0.0,
            )

        audio = bytes(response.content or b"")
        if not audio:
            return self._failure("INVALID_RESPONSE", uncertain=True, job_id=request_id)

        content_type = str(response.headers.get("content-type") or "audio/mpeg").split(";", 1)[0].strip().lower()
        if content_type not in ("audio/mpeg", "audio/mp3"):
            return self._failure("UNSUPPORTED_AUDIO_FORMAT", uncertain=True, job_id=request_id)

        actual_cost = estimate
        billing_units: Dict[str, Any] = {}
        if params.audio_type in ("VO", "DIALOGUE"):
            raw_char_cost = response.headers.get("character-cost")
            try:
                billed_chars = int(raw_char_cost) if raw_char_cost is not None else -1
            except (TypeError, ValueError):
                billed_chars = -1
            if billed_chars < 0:
                return AudioJobResult(
                    provider_job_id=request_id,
                    status="COMPLETED",
                    audio_data=audio,
                    content_type="audio/mpeg",
                    cost_usd=None,
                    submission_uncertain=True,
                    error_code="COST_EVIDENCE_MISSING",
                    error_message="COST_EVIDENCE_MISSING",
                    raw_response={"provider": self.provider_id, "route": "tts", "request_id": request_id},
                )
            actual_cost = round(
                (billed_chars / 1000.0) * float(settings.ELEVENLABS_TTS_COST_PER_1K_CHARS_USD),
                6,
            )
            billing_units = {"billed_characters": billed_chars}
        else:
            billing_units = {"duration_seconds": float(params.duration_seconds or 0.0)}

        route = "music" if params.audio_type == "BGM" else (
            "tts" if params.audio_type in ("VO", "DIALOGUE") else "sound_effects"
        )
        return AudioJobResult(
            provider_job_id=request_id,
            status="COMPLETED",
            audio_data=audio,
            content_type="audio/mpeg",
            duration_seconds=(
                float(params.duration_seconds)
                if params.audio_type in ("BGM", "SFX", "AMBIENCE") and params.duration_seconds is not None
                else None
            ),
            cost_usd=actual_cost,
            raw_response={
                "provider": self.provider_id,
                "route": route,
                "request_id": request_id,
                "billing_units": billing_units,
            },
        )

    async def generate_audio(self, params: AudioGenerationParams) -> AudioJobResult:
        if not self.validate_config({}):
            return self._failure("INVALID_CONFIG", cost_usd=0.0)
        if params.audio_type not in _SUPPORTED_TYPES:
            return self._failure("UNSUPPORTED_AUDIO_TYPE", cost_usd=0.0)
        prompt = self._prompt(params)
        if not prompt:
            return self._failure("INVALID_PARAMETERS", cost_usd=0.0)
        extras = self._validate_extras(params)
        if extras is None:
            return self._failure("UNSUPPORTED_PROVIDER_PARAMETERS", cost_usd=0.0)

        if params.audio_type in ("VO", "DIALOGUE"):
            voice_id = self._voice_id(params)
            if not voice_id:
                return self._failure("VOICE_ID_REQUIRED", cost_usd=0.0)
            payload: Dict[str, Any] = {"text": prompt, "model_id": self._tts_model}
            # eleven_v3 supports Thai and other Core V1 languages; send language
            # only when the canonical value is a compact ISO-style tag.
            if isinstance(params.language, str) and re.fullmatch(r"[A-Za-z]{2,3}", params.language):
                payload["language_code"] = params.language.lower()
            return await self._post_binary(
                f"/text-to-speech/{quote(voice_id, safe='')}",
                params=params,
                payload=payload,
                query={"output_format": self._output_format},
            )

        if params.audio_type == "BGM":
            duration = float(params.duration_seconds or 0.0)
            payload = {
                "prompt": prompt,
                "music_length_ms": int(round(duration * 1000)),
                "model_id": self._music_model,
            }
            return await self._post_binary(
                "/music",
                params=params,
                payload=payload,
                query={"output_format": self._output_format},
            )

        duration = float(params.duration_seconds or 0.0)
        prompt_influence = extras.get("prompt_influence", 0.3)
        if not isinstance(prompt_influence, (int, float)) or not math.isfinite(prompt_influence) or not 0 <= float(prompt_influence) <= 1:
            return self._failure("INVALID_PARAMETERS", cost_usd=0.0)
        loop = bool(extras.get("loop", params.audio_type == "AMBIENCE"))
        payload = {
            "text": prompt,
            "duration_seconds": duration,
            "prompt_influence": float(prompt_influence),
            "model_id": self._sfx_model,
            "loop": loop,
        }
        return await self._post_binary(
            "/sound-generation",
            params=params,
            payload=payload,
            query={"output_format": self._output_format},
        )

    async def check_job_status(self, provider_job_id: str) -> AudioJobResult:
        # R4 uses synchronous ElevenLabs endpoints. Core only polls adapters that
        # return QUEUED/PROCESSING, which this implementation never does.
        return self._failure("ASYNC_STATUS_UNSUPPORTED", job_id=provider_job_id, cost_usd=0.0)
