import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectExportRequest(BaseModel):
    package_type: str = Field(default="FULL_SELF_CONTAINED", description="FULL_SELF_CONTAINED or REFERENCE_ONLY")
    include_history: bool = Field(default=True, description="Whether to include historical jobs, audits, and ledgers")
    include_renders: bool = Field(default=True, description="Whether to include rendered video/audio binaries")

    @field_validator("include_renders")
    @classmethod
    def validate_include_renders(cls, v: bool) -> bool:
        if not v:
            raise ValueError("include_renders=False is not supported in V1 FULL_SELF_CONTAINED archives. All assets must be included.")
        return v


class ProjectValidationResponse(BaseModel):
    valid: bool
    archive_format_version: str
    source_project_id: uuid.UUID
    title: str
    video_mode: str
    entity_counts: Dict[str, int]
    collision_detected: bool
    allowed_modes: List[str]
    total_uncompressed_bytes: int = 0
    manifest_summary: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)


class ProjectImportRequest(BaseModel):
    import_mode: str = Field(default="CLONE", description="CLONE or RESTORE")
    override_title: Optional[str] = Field(default=None, min_length=1, max_length=255)


class ProjectImportResponse(BaseModel):
    project_id: uuid.UUID
    title: str
    status: str
    import_mode: str
    source_project_id: uuid.UUID
    imported_asset_count: int
    created_at: datetime
