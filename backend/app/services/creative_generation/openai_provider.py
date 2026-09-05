import time
import json
import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.services.creative_generation.base import (
    CreativeGenerationProvider,
    CreativeGenerationError,
    GenerationRequestOptions,
    GeneratedStoryDTO,
    GeneratedSceneDTO,
    GeneratedShotDTO,
    ProviderGenerationResult,
)


class OpenAICreativeGenerationProvider(CreativeGenerationProvider):
    """OpenAI (ChatGPT API) implementation of CreativeGenerationProvider interface."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    def _execute_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or not self.api_key.strip():
            raise CreativeGenerationError(
                "PROVIDER_AUTH_FAILED",
                "OpenAI API key is missing or not configured in environment.",
            )

        opts = options or GenerationRequestOptions()
        model = opts.model_override or settings.OPENAI_CREATIVE_MODEL
        timeout = opts.timeout_seconds or settings.OPENAI_TIMEOUT_SECONDS
        max_retries = opts.max_retries if opts.max_retries is not None else settings.OPENAI_MAX_RETRIES

        # Map speed profile to max tokens / temperature
        profile = opts.profile or settings.DEFAULT_CREATIVE_PROFILE
        if profile == "FAST":
            temperature = 0.5
            max_tokens = 2000
        elif profile == "QUALITY":
            temperature = 0.8
            max_tokens = 6000
        else:  # BALANCED
            temperature = 0.7
            max_tokens = 4000

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.perf_counter()
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)

                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if resp.status_code == 200:
                    res_json = resp.json()
                    choices = res_json.get("choices", [])
                    if not choices:
                        raise CreativeGenerationError(
                            "INVALID_PROVIDER_RESPONSE",
                            "OpenAI returned empty response choices.",
                        )
                    content_raw = choices[0].get("message", {}).get("content", "")
                    usage = res_json.get("usage", {})
                    return {
                        "content_raw": content_raw,
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "duration_ms": duration_ms,
                        "model": model,
                    }
                elif resp.status_code in (401, 403):
                    raise CreativeGenerationError(
                        "PROVIDER_AUTH_FAILED",
                        f"OpenAI authentication failed (HTTP {resp.status_code}). Check OPENAI_API_KEY.",
                    )
                elif resp.status_code == 429:
                    if attempt < max_retries:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    raise CreativeGenerationError(
                        "PROVIDER_UNAVAILABLE",
                        "OpenAI rate limit exceeded (HTTP 429).",
                    )
                elif resp.status_code >= 500:
                    if attempt < max_retries:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    raise CreativeGenerationError(
                        "PROVIDER_UNAVAILABLE",
                        f"OpenAI provider server error (HTTP {resp.status_code}).",
                    )
                else:
                    raise CreativeGenerationError(
                        "GENERATION_FAILED",
                        f"OpenAI returned HTTP error {resp.status_code}: {resp.text[:200]}",
                    )

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise CreativeGenerationError(
                    "PROVIDER_TIMEOUT",
                    f"OpenAI request timed out after {timeout} seconds.",
                )
            except httpx.RequestError as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise CreativeGenerationError(
                    "PROVIDER_UNAVAILABLE",
                    f"Failed to connect to OpenAI API: {type(e).__name__}",
                )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        raise CreativeGenerationError(
            "GENERATION_FAILED",
            f"OpenAI generation failed after {max_retries} retries: {str(last_exception)}",
        )

    def generate_story(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        system_prompt = (
            "You are an expert AI screenplay writer. Generate a complete story script matching this JSON schema:\n"
            "{\n"
            '  "title": "string",\n'
            '  "logline": "string",\n'
            '  "synopsis": "string",\n'
            '  "tone": "string",\n'
            '  "target_duration_seconds": 60.0,\n'
            '  "language": "th",\n'
            '  "scenes": [\n'
            "    {\n"
            '      "scene_number": 1,\n'
            '      "title": "INT. LAB - DAY",\n'
            '      "purpose": "string",\n'
            '      "setting": "string",\n'
            '      "duration_seconds": 15.0,\n'
            '      "narration": "string",\n'
            '      "dialogue": [{"speaker": "A", "text": "..."}],\n'
            '      "shots": [\n'
            "        {\n"
            '          "shot_number": 1,\n'
            '          "description": "string",\n'
            '          "camera": "string",\n'
            '          "subject": "string",\n'
            '          "action": "string",\n'
            '          "duration_seconds": 4.0,\n'
            '          "image_prompt": "string",\n'
            '          "video_prompt": "string"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Return ONLY valid JSON."
        )

        raw_res = self._execute_completion(system_prompt, prompt, options)
        content_raw = raw_res["content_raw"]

        try:
            parsed = json.loads(content_raw)
            story_dto = GeneratedStoryDTO.model_validate(parsed)
        except Exception as e:
            raise CreativeGenerationError(
                "INVALID_PROVIDER_RESPONSE",
                f"Failed to parse provider response into GeneratedStoryDTO: {str(e)}",
            )

        return ProviderGenerationResult(
            provider="openai",
            model=raw_res["model"],
            input_character_count=len(prompt),
            output_character_count=len(content_raw),
            prompt_tokens=raw_res["prompt_tokens"],
            completion_tokens=raw_res["completion_tokens"],
            duration_ms=raw_res["duration_ms"],
            data=story_dto,
        )

    def generate_scenes(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        system_prompt = (
            "You are an expert AI screenplay writer. Generate a list of scenes matching this JSON schema:\n"
            '{"scenes": [{ "scene_number": 1, "title": "INT. LAB - DAY", "purpose": "string", '
            '"setting": "string", "duration_seconds": 15.0, "narration": "string", '
            '"dialogue": [{"speaker": "A", "text": "..."}], '
            '"shots": [{ "shot_number": 1, "description": "...", "camera": "...", '
            '"subject": "...", "action": "...", "duration_seconds": 4.0, '
            '"image_prompt": "...", "video_prompt": "..." }] }]}\n'
            "Return ONLY valid JSON."
        )

        raw_res = self._execute_completion(system_prompt, prompt, options)
        content_raw = raw_res["content_raw"]

        try:
            parsed = json.loads(content_raw)
            scenes_raw = parsed.get("scenes", [])
            scenes_dto = [GeneratedSceneDTO.model_validate(s) for s in scenes_raw]
        except Exception as e:
            raise CreativeGenerationError(
                "INVALID_PROVIDER_RESPONSE",
                f"Failed to parse provider response into GeneratedSceneDTO list: {str(e)}",
            )

        return ProviderGenerationResult(
            provider="openai",
            model=raw_res["model"],
            input_character_count=len(prompt),
            output_character_count=len(content_raw),
            prompt_tokens=raw_res["prompt_tokens"],
            completion_tokens=raw_res["completion_tokens"],
            duration_ms=raw_res["duration_ms"],
            data=scenes_dto,
        )

    def generate_shots(
        self,
        prompt: str,
        options: Optional[GenerationRequestOptions] = None,
    ) -> ProviderGenerationResult:
        system_prompt = (
            "You are an expert AI video director. Generate a list of shots matching this JSON schema:\n"
            '{"shots": [{ "shot_number": 1, "description": "...", "camera": "...", '
            '"subject": "...", "action": "...", "duration_seconds": 4.0, '
            '"image_prompt": "...", "video_prompt": "..." }]}\n'
            "Return ONLY valid JSON."
        )

        raw_res = self._execute_completion(system_prompt, prompt, options)
        content_raw = raw_res["content_raw"]

        try:
            parsed = json.loads(content_raw)
            shots_raw = parsed.get("shots", [])
            shots_dto = [GeneratedShotDTO.model_validate(s) for s in shots_raw]
        except Exception as e:
            raise CreativeGenerationError(
                "INVALID_PROVIDER_RESPONSE",
                f"Failed to parse provider response into GeneratedShotDTO list: {str(e)}",
            )

        return ProviderGenerationResult(
            provider="openai",
            model=raw_res["model"],
            input_character_count=len(prompt),
            output_character_count=len(content_raw),
            prompt_tokens=raw_res["prompt_tokens"],
            completion_tokens=raw_res["completion_tokens"],
            duration_ms=raw_res["duration_ms"],
            data=shots_dto,
        )
