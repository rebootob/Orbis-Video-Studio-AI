"""Deterministic Mock Audio Generation Provider Adapter."""
import uuid
import struct
from typing import Dict, Any, Optional
from app.providers.audio.base import (
    IAudioProviderAdapter,
    AudioGenerationParams,
    AudioJobResult,
    AudioProviderCapabilities,
)


def _generate_deterministic_wav_bytes(duration_sec: float, tag: str = "ORBIS") -> bytes:
    """Generate a valid standard 44-byte RIFF/WAV PCM audio file."""
    sample_rate = 8000
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    
    num_samples = int(sample_rate * max(0.5, min(duration_sec, 60.0)))
    data_size = num_samples * block_align
    chunk_size = 36 + data_size
    
    # 44-byte WAV header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size for PCM
        1,   # AudioFormat (1 = PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    
    # Embed deterministic pattern
    tag_bytes = tag.encode("utf-8")[:16].ljust(16, b"\x00")
    sample_data = bytearray(data_size)
    for i in range(min(len(tag_bytes), data_size)):
        sample_data[i] = tag_bytes[i]
        
    return header + bytes(sample_data)


class MockAudioProviderAdapter(IAudioProviderAdapter):
    """Deterministic, provider-neutral mock adapter for VO, BGM, SFX, and Ambience."""

    def __init__(self, provider_id: str = "mock_audio"):
        self._provider_id = provider_id
        self._jobs: Dict[str, Dict[str, Any]] = {}

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_capabilities(self) -> AudioProviderCapabilities:
        return AudioProviderCapabilities(
            provider_id=self._provider_id,
            supported_audio_types=["VO", "DIALOGUE", "BGM", "SFX", "AMBIENCE", "ORIGINAL_AUDIO"],
            supports_tts=True,
            supports_music=True,
            supports_sfx=True,
            supports_voice_cloning=True,
            supported_formats=["audio/wav", "audio/mpeg"],
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    async def generate_audio(self, params: AudioGenerationParams) -> AudioJobResult:
        job_id = f"mock-audio-job-{uuid.uuid4().hex[:12]}"
        duration = params.duration_seconds or 4.0
        
        cost = 0.05 if params.audio_type == "BGM" else 0.02

        # Check for simulated async
        extra = params.provider_specific_params or {}
        if extra.get("simulate_async"):
            self._jobs[job_id] = {
                "params": params,
                "polls": 0,
                "status": "QUEUED",
                "cost": cost,
            }
            return AudioJobResult(
                provider_job_id=job_id,
                status="QUEUED",
                audio_url=None,
                audio_data=None,
                content_type="audio/wav",
                duration_seconds=duration,
                cost_usd=cost,
                raw_response={"mock_provider": self._provider_id, "mode": "async"},
            )

        # Check for simulated provider failure
        if extra.get("simulate_failure"):
            return AudioJobResult(
                provider_job_id=job_id,
                status="FAILED",
                error_message=extra.get("error_message", "Simulated audio provider failure"),
                error_code="PROVIDER_ERROR",
                retryable=True,
                cost_usd=0.0,
            )

        # Check for simulated ambiguous submission
        if extra.get("simulate_uncertain"):
            return AudioJobResult(
                provider_job_id=job_id,
                status="PROCESSING",
                submission_uncertain=True,
                error_message="Ambiguous provider submission outcome",
                cost_usd=cost,
            )

        audio_bytes = _generate_deterministic_wav_bytes(duration, tag=f"{params.audio_type}:{params.clip_id[:8]}")

        return AudioJobResult(
            provider_job_id=job_id,
            status="COMPLETED",
            audio_url=f"https://mock-audio-cdn.internal/{job_id}.wav",
            audio_data=audio_bytes,
            content_type="audio/wav",
            duration_seconds=duration,
            cost_usd=cost,
            raw_response={
                "mock_provider": self._provider_id,
                "audio_type": params.audio_type,
                "duration": duration,
                "prompt": params.prompt,
            },
        )

    async def check_job_status(self, provider_job_id: str) -> AudioJobResult:
        if provider_job_id not in self._jobs:
            return AudioJobResult(
                provider_job_id=provider_job_id,
                status="FAILED",
                error_message="Job not found",
                error_code="JOB_NOT_FOUND",
            )
        job_info = self._jobs[provider_job_id]
        job_info["polls"] += 1
        params = job_info["params"]
        duration = params.duration_seconds or 4.0
        cost = job_info["cost"]

        if job_info["polls"] >= 1:
            audio_bytes = _generate_deterministic_wav_bytes(duration, tag=f"{params.audio_type}:{params.clip_id[:8]}")
            return AudioJobResult(
                provider_job_id=provider_job_id,
                status="COMPLETED",
                audio_url=f"https://mock-audio-cdn.internal/{provider_job_id}.wav",
                audio_data=audio_bytes,
                content_type="audio/wav",
                duration_seconds=duration,
                cost_usd=cost,
                raw_response={"mock_provider": self._provider_id, "polls": job_info["polls"]},
            )
        
        return AudioJobResult(
            provider_job_id=provider_job_id,
            status="PROCESSING",
            cost_usd=cost,
            progress_percentage=50.0,
        )
