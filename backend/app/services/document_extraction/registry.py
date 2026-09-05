from typing import List, Optional
from app.services.document_extraction.base import DocumentExtractor
from app.services.document_extraction.extractors.text import TextDocumentExtractor
from app.services.document_extraction.extractors.pdf import PdfDocumentExtractor
from app.services.document_extraction.extractors.docx import DocxDocumentExtractor
from app.services.document_extraction.extractors.pptx import PptxDocumentExtractor


class ExtractorRegistry:
    """Registry routing document types to native format extractors."""

    def __init__(self):
        self._extractors: List[DocumentExtractor] = [
            TextDocumentExtractor(),
            PdfDocumentExtractor(),
            DocxDocumentExtractor(),
            PptxDocumentExtractor(),
        ]

    def get_extractor(self, document_type: str) -> Optional[DocumentExtractor]:
        for extractor in self._extractors:
            if extractor.supports(document_type):
                return extractor
        return None


default_extractor_registry = ExtractorRegistry()
