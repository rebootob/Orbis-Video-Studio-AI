import uuid
import time
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.asset import Asset
from app.models.document_extraction import DocumentExtraction
from app.services.storage.base import ObjectStorageProvider
from app.services.document_extraction.base import ExtractionResult
from app.services.document_extraction.detector import DocumentTypeDetector
from app.services.document_extraction.registry import default_extractor_registry


class DocumentExtractionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class DocumentExtractionService:
    """Service orchestrating document text extraction and database persistence."""

    def __init__(self, db: Session, storage: ObjectStorageProvider):
        self.db = db
        self.storage = storage

    def extract_asset_document(self, asset_id: uuid.UUID, force: bool = False) -> DocumentExtraction:
        # 1. Fetch Asset
        asset = self.db.get(Asset, asset_id)
        if not asset:
            raise DocumentExtractionError("ASSET_NOT_FOUND", f"Asset with ID '{asset_id}' not found.")

        # Check existing extraction
        existing = self.db.query(DocumentExtraction).filter(DocumentExtraction.asset_id == asset_id).first()
        if existing and not force:
            return existing

        # Check Asset file_size_bytes metadata before downloading object payload
        if asset.file_size_bytes and asset.file_size_bytes > settings.MAX_DOCUMENT_BYTES:
            raise DocumentExtractionError(
                "DOCUMENT_TOO_LARGE",
                f"Document metadata size ({asset.file_size_bytes} bytes) exceeds maximum limit ({settings.MAX_DOCUMENT_BYTES} bytes).",
            )

        # 2. Verify object storage payload existence
        try:
            content = self.storage.get_object(asset.storage_bucket, asset.storage_key)
        except KeyError:
            raise DocumentExtractionError(
                "STORAGE_OBJECT_MISSING",
                f"Object storage payload missing for Asset '{asset_id}'.",
            )
        except Exception as e:
            err_code = str(getattr(e, "response", {}).get("Error", {}).get("Code", ""))
            status_code = str(getattr(e, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode", ""))
            if err_code in ("404", "NoSuchKey", "NotFound") or status_code == "404":
                raise DocumentExtractionError(
                    "STORAGE_OBJECT_MISSING",
                    f"Object storage payload missing for Asset '{asset_id}'.",
                )
            raise DocumentExtractionError(
                "STORAGE_ACCESS_FAILED",
                f"Failed to access object storage payload: {type(e).__name__}",
            )

        # 3. Defensive check on retrieved payload length
        if len(content) > settings.MAX_DOCUMENT_BYTES:
            raise DocumentExtractionError(
                "DOCUMENT_TOO_LARGE",
                f"Document size ({len(content)} bytes) exceeds maximum limit ({settings.MAX_DOCUMENT_BYTES} bytes).",
            )

        # 4. Detect document type
        doc_type = DocumentTypeDetector.detect(
            filename=asset.original_filename,
            content_type=asset.content_type,
            content=content,
        )

        if not doc_type:
            raise DocumentExtractionError(
                "UNSUPPORTED_DOCUMENT_TYPE",
                f"Unsupported document format for file '{asset.original_filename}'. Supported types: PDF, DOCX, PPTX, TXT, MD.",
            )

        extractor = default_extractor_registry.get_extractor(doc_type)
        if not extractor:
            raise DocumentExtractionError(
                "UNSUPPORTED_DOCUMENT_TYPE",
                f"No extractor registered for document type '{doc_type}'.",
            )

        # 5. Execute extraction
        metadata = {"document_type": doc_type, "original_filename": asset.original_filename}
        result: ExtractionResult = extractor.extract(asset_id=asset.id, content=content, metadata=metadata)

        # 6. Persist/Update DocumentExtraction in PostgreSQL DB
        if existing:
            extraction_record = existing
            extraction_record.document_type = result.document_type
            extraction_record.status = result.extraction_status
            extraction_record.extracted_text = result.extracted_text
            extraction_record.segment_count = result.segment_count
            extraction_record.character_count = result.character_count
            extraction_record.extraction_method = result.extraction_method
            extraction_record.extraction_duration_ms = result.extraction_duration_ms
            extraction_record.segments = result.segments
            extraction_record.warnings = result.warnings
            extraction_record.error_message = result.error_message
        else:
            extraction_record = DocumentExtraction(
                id=uuid.uuid4(),
                asset_id=asset.id,
                document_type=result.document_type,
                status=result.extraction_status,
                extracted_text=result.extracted_text,
                segment_count=result.segment_count,
                character_count=result.character_count,
                extraction_method=result.extraction_method,
                extraction_duration_ms=result.extraction_duration_ms,
                segments=result.segments,
                warnings=result.warnings,
                error_message=result.error_message,
            )
            self.db.add(extraction_record)

        self.db.commit()
        self.db.refresh(extraction_record)
        return extraction_record
