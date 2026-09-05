import os
from typing import Optional


class DocumentTypeDetector:
    """Detects document type conservatively from filename, content_type, and magic signature."""

    _EXTENSION_MAP = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".pptx": "pptx",
        ".txt": "txt",
        ".md": "md",
        ".markdown": "md",
    }

    _CONTENT_TYPE_MAP = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "text/plain": "txt",
        "text/markdown": "md",
        "text/x-markdown": "md",
    }

    @classmethod
    def detect(cls, filename: str, content_type: Optional[str] = None, content: Optional[bytes] = None) -> Optional[str]:
        # 1. Magic Signature check (highest priority if content provided)
        if content:
            if content.startswith(b"%PDF-"):
                return "pdf"
            if content.startswith(b"PK\x03\x04"):
                # Could be docx or pptx zip archive
                _, ext = os.path.splitext(filename.lower())
                if ext == ".docx":
                    return "docx"
                if ext == ".pptx":
                    return "pptx"

        # 2. Extension check
        _, ext = os.path.splitext(filename.lower())
        if ext in cls._EXTENSION_MAP:
            return cls._EXTENSION_MAP[ext]

        # 3. Content-Type check
        if content_type:
            ct = content_type.split(";")[0].strip().lower()
            if ct in cls._CONTENT_TYPE_MAP:
                return cls._CONTENT_TYPE_MAP[ct]

        return None
