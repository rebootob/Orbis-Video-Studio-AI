import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AssetBase(BaseModel):
    name: str
    asset_type: str = Field(default="REFERENCE", description="REFERENCE, DOCUMENT, IMAGE, VIDEO, AUDIO, IMPORTED, GENERATED, etc.")


class AssetCreate(AssetBase):
    project_id: uuid.UUID


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    original_filename: str
    asset_type: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    storage_bucket: str
    storage_key: str
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    download_url: Optional[str] = None


class AssetDownloadResponse(BaseModel):
    asset_id: uuid.UUID
    download_url: str
    expires_in: int = 3600
