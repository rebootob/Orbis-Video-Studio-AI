import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    document_type: str
    status: str
    extracted_text: str
    segment_count: int
    character_count: int
    extraction_method: str
    extraction_duration_ms: float
    segments: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
