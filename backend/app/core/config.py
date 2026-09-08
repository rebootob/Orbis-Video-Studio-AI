import os
from typing import Optional
from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Orbis Video Studio AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "orbis_user"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "orbis_db"

    # Object Storage Settings (S3-compatible)
    OBJECT_STORAGE_ENDPOINT: Optional[str] = None
    OBJECT_STORAGE_REGION: str = "us-east-1"
    OBJECT_STORAGE_BUCKET: str = "orbis-assets"
    OBJECT_STORAGE_ACCESS_KEY: str = ""
    OBJECT_STORAGE_SECRET_KEY: str = ""
    OBJECT_STORAGE_SECURE: bool = False
    MAX_UPLOAD_SIZE_BYTES: int = 524288000  # 500 MB

    # Document Extraction Limits
    MAX_DOCUMENT_BYTES: int = 52428800  # 50 MB
    MAX_DOCUMENT_PAGES: int = 500  # 500 pages/slides
    MAX_EXTRACTED_CHARACTERS: int = 2000000  # 2M characters

    # OpenAI Creative Generation Settings
    OPENAI_API_KEY: str = ""
    OPENAI_CREATIVE_MODEL: str = "gpt-4o"
    OPENAI_TIMEOUT_SECONDS: float = 30.0
    OPENAI_MAX_RETRIES: int = 2
    DEFAULT_CREATIVE_PROFILE: str = "BALANCED"

    # Reference Library Context Limit
    MAX_REFERENCE_CONTEXT_CHARACTERS: int = 50000

    # Gemini production ImageProvider settings (Core V1 R3)
    GEMINI_API_KEY: str = ""
    GEMINI_IMAGE_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_IMAGE_MODEL: str = "gemini-3.1-flash-image"
    GEMINI_IMAGE_TIMEOUT_SECONDS: float = 60.0
    # Core V1 R3 is intentionally bounded to 1K. Larger image outputs are a
    # separate product/cost decision rather than a hidden per-shot override.
    GEMINI_IMAGE_SIZE: str = "1K"
    GEMINI_IMAGE_MAX_REFERENCE_COUNT: int = 14
    GEMINI_IMAGE_MAX_INLINE_REFERENCE_BYTES: int = 18874368  # 18 MiB under API inline request limit
    # Current Gemini Developer API rates are configurable, not hard-coded in domain logic.
    # Defaults reflect the provider decision evidence captured for R3 on 2026-09-08.
    GEMINI_IMAGE_INPUT_COST_PER_MILLION_USD: float = 0.50
    GEMINI_IMAGE_OUTPUT_TEXT_COST_PER_MILLION_USD: float = 3.00
    GEMINI_IMAGE_OUTPUT_IMAGE_COST_PER_MILLION_USD: float = 60.00

    # ElevenLabs production AudioProvider settings (Core V1 R4)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"
    ELEVENLABS_TIMEOUT_SECONDS: float = 60.0
    # Speech requires an explicitly configured voice. BGM/SFX/Ambience can run
    # with only the API key; VO/DIALOGUE fail closed when no voice is configured.
    ELEVENLABS_DEFAULT_VOICE_ID: str = ""
    ELEVENLABS_TTS_MODEL: str = "eleven_v3"
    ELEVENLABS_MUSIC_MODEL: str = "music_v2"
    ELEVENLABS_SFX_MODEL: str = "eleven_text_to_sound_v2"
    ELEVENLABS_OUTPUT_FORMAT: str = "mp3_44100_128"
    # Current ElevenAPI pay-as-you-go rates are configurable rather than hidden
    # in domain logic. Defaults reflect provider evidence captured 2026-09-08.
    ELEVENLABS_TTS_COST_PER_1K_CHARS_USD: float = 0.10
    ELEVENLABS_MUSIC_COST_PER_MINUTE_USD: float = 0.15
    ELEVENLABS_SFX_COST_PER_MINUTE_USD: float = 0.12

    # Vidu Video Generation Provider Settings
    VIDU_API_KEY: str = ""
    VIDU_BASE_URL: str = "https://api.vidu.com/ent/v2"
    VIDU_DEFAULT_MODEL: str = "viduq2"
    VIDU_TIMEOUT_SECONDS: float = 30.0
    VIDU_MAX_RETRIES: int = 3

    # Provider Routing Configuration
    # Production defaults must never silently resolve to deterministic fake providers.
    DEFAULT_IMAGE_PROVIDER: str = "gemini_image"
    DEFAULT_AUDIO_PROVIDER: str = "elevenlabs_audio"
    DEFAULT_VIDEO_PROVIDER: str = "vidu"

    # Provider Pricing Configuration (Replaceable / Configurable via settings).
    # $0.08 is a conservative 1K pre-dispatch reservation: current 1K image
    # output is about $0.067 before input/reference tokens. Actual cost is later
    # reconciled from provider-reported token usage by the adapter.
    PROVIDER_PRICING_CONFIG: Optional[dict] = {
        "gemini_image:IMAGE_GENERATION": {
            "provider": "gemini_image",
            "operation": "IMAGE_GENERATION",
            "cost_per_generation": 0.08,
            "currency": "USD",
        }
    }

    SQLALCHEMY_DATABASE_URI_OVERRIDE: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI_OVERRIDE:
            return self.SQLALCHEMY_DATABASE_URI_OVERRIDE
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
