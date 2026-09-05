import time
import uuid
from typing import Dict, Any, List
import fitz  # PyMuPDF
from app.core.config import settings
from app.services.document_extraction.base import DocumentExtractor, ExtractionResult


class PdfDocumentExtractor(DocumentExtractor):
    """Fast, native PDF text-layer extractor using PyMuPDF (fitz)."""

    def supports(self, document_type: str) -> bool:
        return document_type == "pdf"

    def extract(self, asset_id: uuid.UUID, content: bytes, metadata: Dict[str, Any]) -> ExtractionResult:
        start_time = time.perf_counter()
        warnings: List[str] = []

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return ExtractionResult(
                asset_id=asset_id,
                document_type="pdf",
                extracted_text="",
                character_count=0,
                segment_count=0,
                extraction_status="FAILED",
                extraction_method="PyMuPDF",
                extraction_duration_ms=duration_ms,
                error_message=f"Failed to parse PDF document: {str(e)}",
            )

        total_pages = doc.page_count
        if total_pages > settings.MAX_DOCUMENT_PAGES:
            warnings.append(
                f"PDF page count ({total_pages}) exceeds maximum allowed limit ({settings.MAX_DOCUMENT_PAGES}). Extracted first {settings.MAX_DOCUMENT_PAGES} pages."
            )
            pages_to_read = settings.MAX_DOCUMENT_PAGES
        else:
            pages_to_read = total_pages

        segments: List[Dict[str, Any]] = []
        page_texts: List[str] = []
        total_chars = 0

        for page_num in range(pages_to_read):
            page = doc.load_page(page_num)
            page_text = page.get_text("text").replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
            page_text_trimmed = page_text.strip()

            if page_text_trimmed:
                page_texts.append(page_text_trimmed)
                segments.append({
                    "index": page_num + 1,
                    "type": "page",
                    "text": page_text_trimmed,
                })
                total_chars += len(page_text_trimmed)

                if total_chars >= settings.MAX_EXTRACTED_CHARACTERS:
                    warnings.append(f"Text extraction aborted at character limit ({settings.MAX_EXTRACTED_CHARACTERS}).")
                    break

        doc.close()

        combined_text = "\n\n".join(page_texts)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Check if PDF contains no extractable text layer (e.g. scanned image PDF)
        if not combined_text.strip():
            status = "NO_TEXT_LAYER"
            warnings.append("NO_TEXT_LAYER: PDF document contains no extractable text layer. OCR_REQUIRED for scanned images.")
        else:
            status = "SUCCESS"

        return ExtractionResult(
            asset_id=asset_id,
            document_type="pdf",
            extracted_text=combined_text,
            character_count=len(combined_text),
            segment_count=len(segments),
            segments=segments,
            extraction_status=status,
            extraction_method="PyMuPDF",
            extraction_duration_ms=duration_ms,
            warnings=warnings,
        )
