"""Canonical structured AudioSpec schema and provider rendering."""
from typing import Optional, Dict, Any, Literal, List
from pydantic import BaseModel, Field
from app.models.audio_clip import (
    AudioSourceType,
    AudioType,
    AudioGenerationMode,
    AudioScope,
    DuckingRole,
)


class AudioSpec(BaseModel):
    clip_id: Optional[str] = None
    audio_type: AudioType
    source_type: AudioSourceType
    generation_mode: AudioGenerationMode
    scope: AudioScope
    prompt: str
    negative_prompt: Optional[str] = None
    language: Optional[str] = "en"
    speaker: Optional[str] = None
    duration_seconds: Optional[float] = 4.0
    start_time: float = 0.0
    intensity: Optional[str] = None
    ducking_role: DuckingRole = DuckingRole.BACKGROUND
    reference_context: Optional[Dict[str, Any]] = None
    provider_capability_hints: Optional[Dict[str, Any]] = None

    def to_video_prompt(self) -> str:
        """Render into prompt instructions for native video+audio generation."""
        if self.audio_type in (AudioType.VO, AudioType.DIALOGUE):
            spk = f"{self.speaker}: " if self.speaker else ""
            return f"[Native Audio / Dialogue] {spk}\"{self.prompt}\""
        elif self.audio_type == AudioType.BGM:
            return f"[Background Music] {self.prompt}"
        elif self.audio_type == AudioType.SFX:
            return f"[Sound Effect] {self.prompt}"
        elif self.audio_type == AudioType.AMBIENCE:
            return f"[Ambience] {self.prompt}"
        return f"[Audio] {self.prompt}"

    def to_tts_request(self) -> Dict[str, Any]:
        """Render into request parameters for TTS/voice provider."""
        return {
            "text": self.prompt,
            "voice_id": self.speaker,
            "language": self.language or "en",
            "duration_seconds": self.duration_seconds,
            "intensity": self.intensity,
        }

    def to_music_request(self) -> Dict[str, Any]:
        """Render into request parameters for AI music generation."""
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "duration_seconds": self.duration_seconds,
            "style": self.intensity,
        }

    def to_sfx_request(self) -> Dict[str, Any]:
        """Render into request parameters for SFX/ambience generation."""
        return {
            "prompt": self.prompt,
            "duration_seconds": self.duration_seconds,
            "audio_type": self.audio_type.value,
        }

    def to_copy_prompt(self) -> str:
        """Render human-readable copy/manual prompt."""
        header = f"=== Audio Spec: {self.audio_type.value} ({self.scope.value}) ==="
        mode_info = f"Generation Mode: {self.generation_mode.value} | Source: {self.source_type.value}"
        details = f"Duration: {self.duration_seconds}s | Start: {self.start_time}s"
        spk = f"Speaker: {self.speaker} | " if self.speaker else ""
        lang = f"Language: {self.language}" if self.language else ""
        return f"{header}\n{mode_info}\n{details}\n{spk}{lang}\nPrompt: {self.prompt}"
