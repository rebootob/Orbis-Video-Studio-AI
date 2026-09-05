import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ExtractionResult:
    asset_id: uuid.UUID
    document_type: str  # pdf, docx, pptx, txt, md
    extracted_text: str
    character_count: int
    segment_count: int
    segments: List[Dict[str, Any]] = field(default_factory=list)
    extraction_status: str = "SUCCESS"  # SUCCESS, NO_TEXT_LAYER, TOO_LARGE, UNSUPPORTED, FAILED
    extraction_method: str = "unknown"
    extraction_duration_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class DocumentExtractor(ABC):
    """Abstract base class for document format extractors."""

    @abstractmethod
    def supports(self, document_type: str) -> bool:
        """Check if this extractor handles the given document type."""
        pass

    @abstractmethod
    def extract(self, asset_id: uuid.UUID, content: bytes, metadata: Dict[str, Any]) -> ExtractionResult:
        """Extract text content from raw bytes payload."""
        pass
