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
    GEMINI_IMAGE_SIZE: str = "1K"
    GEMINI_IMAGE_MAX_REFERENCE_COUNT: int = 14
    GEMINI_IMAGE_MAX_INLINE_REFERENCE_BYTES: int = 18874368  # 18 MiB under API inline request limit
    # Current Gemini Developer API rates are configurable, not hard-coded in domain logic.
    # Defaults reflect the provider decision evidence captured for R3 on 2026-09-08.
    GEMINI_IMAGE_INPUT_COST_PER_MILLION_USD: float = 0.50
    GEMINI_IMAGE_OUTPUT_TEXT_COST_PER_MILLION_USD: float = 3.00
    GEMINI_IMAGE_OUTPUT_IMAGE_COST_PER_MILLION_USD: float = 60.00

    # Vidu Video Generation Provider Settings
    VIDU_API_KEY: str = ""
    VIDU_BASE_URL: str = "https://api.vidu.com/ent/v2"
    VIDU_DEFAULT_MODEL: str = "viduq2"
    VIDU_TIMEOUT_SECONDS: float = 30.0
    VIDU_MAX_RETRIES: int = 3

    # Provider Routing Configuration
    # Production defaults must never silently resolve to deterministic fake providers.
    DEFAULT_IMAGE_PROVIDER: str = "gemini_image"
    DEFAULT_VIDEO_PROVIDER: str = "vidu"

    # Provider Pricing Configuration (Replaceable / Configurable via settings)
    PROVIDER_PRICING_CONFIG: Optional[dict] = None

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
