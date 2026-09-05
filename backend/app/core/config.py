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
