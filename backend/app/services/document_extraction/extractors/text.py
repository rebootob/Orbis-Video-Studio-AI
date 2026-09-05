import time
import uuid
from typing import Dict, Any, List
from app.core.config import settings
from app.services.document_extraction.base import DocumentExtractor, ExtractionResult


class TextDocumentExtractor(DocumentExtractor):
    """Fast, lightweight extractor for plain text (.txt) and Markdown (.md) documents."""

    def supports(self, document_type: str) -> bool:
        return document_type in ("txt", "md")

    def extract(self, asset_id: uuid.UUID, content: bytes, metadata: Dict[str, Any]) -> ExtractionResult:
        start_time = time.perf_counter()
        doc_type = metadata.get("document_type", "txt")
        warnings: List[str] = []

        # 1. Decode text preserving Unicode (Thai, English, Japanese, etc.)
        raw_text = ""
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                raw_text = content.decode(encoding)
                break
            except (UnicodeDecodeError, ValueError):
                continue

        if not raw_text and content:
            raw_text = content.decode("utf-8", errors="replace")
            warnings.append("Used lossy UTF-8 decoding fallback for invalid byte sequences.")

        # 2. Normalize text: line endings & control chars
        normalized_text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")

        # 3. Check character limits
        if len(normalized_text) > settings.MAX_EXTRACTED_CHARACTERS:
            normalized_text = normalized_text[: settings.MAX_EXTRACTED_CHARACTERS]
            warnings.append(f"Text truncated at maximum limit of {settings.MAX_EXTRACTED_CHARACTERS} characters.")

        # 4. Segment by paragraph
        paragraphs = [p.strip() for p in normalized_text.split("\n\n") if p.strip()]
        segments = [
            {"index": idx + 1, "type": "paragraph", "text": p}
            for idx, p in enumerate(paragraphs)
        ]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status = "SUCCESS" if normalized_text.strip() else "NO_TEXT_LAYER"

        return ExtractionResult(
            asset_id=asset_id,
            document_type=doc_type,
            extracted_text=normalized_text,
            character_count=len(normalized_text),
            segment_count=len(segments),
            segments=segments,
            extraction_status=status,
            extraction_method="text-decoder",
            extraction_duration_ms=duration_ms,
            warnings=warnings,
        )
