import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.document_extraction import DocumentExtraction
from app.schemas.document_extraction import DocumentExtractionResponse
from app.services.storage.factory import get_storage_provider
from app.services.storage.base import ObjectStorageProvider
from app.services.document_extraction.service import DocumentExtractionService, DocumentExtractionError

router = APIRouter()


@router.post("/assets/{asset_id}/extract", response_model=DocumentExtractionResponse, status_code=status.HTTP_200_OK)
def extract_asset_document(
    asset_id: uuid.UUID,
    force: bool = Query(False, description="Force re-extraction even if already extracted"),
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    """Extract normalized text payload from an uploaded document Asset."""
    service = DocumentExtractionService(db=db, storage=storage)

    try:
        extraction = service.extract_asset_document(asset_id=asset_id, force=force)
        return extraction
    except DocumentExtractionError as e:
        if e.code == "ASSET_NOT_FOUND" or e.code == "STORAGE_OBJECT_MISSING":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
        elif e.code in ("UNSUPPORTED_DOCUMENT_TYPE", "DOCUMENT_TOO_LARGE"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


@router.get("/assets/{asset_id}/extraction", response_model=DocumentExtractionResponse)
def get_asset_extraction(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieve existing DocumentExtraction result for an Asset."""
    extraction = db.query(DocumentExtraction).filter(DocumentExtraction.asset_id == asset_id).first()
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction record not found for Asset '{asset_id}'.",
        )
    return extraction
