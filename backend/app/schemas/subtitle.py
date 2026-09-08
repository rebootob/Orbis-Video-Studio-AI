from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SubtitleGenerateRequest(BaseModel):
    timeline_id: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=50)


class SubtitleReviewRequest(BaseModel):
    enabled: bool = True
    render_mode: Literal["OFF", "BURN_IN"] = "OFF"


class SubtitleSegmentRead(BaseModel):
    id: str
    ordinal: int
    text: str
    start_time: float
    end_time: float
    language: str
    source_type: str
    source_ref: str


class SubtitleTrackRead(BaseModel):
    id: str
    version_number: int
    timeline_version: int
    timeline_fingerprint: str
    language: str
    enabled: bool
    render_mode: Literal["OFF", "BURN_IN"]
    review_status: str
    is_reviewed: bool
    is_stale: bool
    source_summary: Dict[str, Any]
    segments: List[SubtitleSegmentRead]
    srt_sha256: str
    created_at: str
    reviewed_at: Optional[str] = None
