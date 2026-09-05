import os
import re
import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.models.project import Project
from app.models.asset import Asset
from app.schemas.asset import AssetResponse, AssetDownloadResponse
from app.services.storage.factory import get_storage_provider
from app.services.storage.base import ObjectStorageProvider

router = APIRouter()


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename to prevent path traversal and unsafe characters."""
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\.-]", "_", filename)
    return filename or "unnamed_file"


def generate_object_key(project_id: uuid.UUID, asset_id: uuid.UUID, filename: str) -> str:
    """Generate server-controlled deterministic object key."""
    sanitized = sanitize_filename(filename)
    return f"projects/{project_id}/assets/{asset_id}/{sanitized}"


@router.post("/assets/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: uuid.UUID = Form(...),
    name: Optional[str] = Form(None),
    asset_type: str = Form("REFERENCE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    """Upload a file asset into object storage and record metadata in DB."""
    # 1. Verify Project exists
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # 2. Read and validate file content
    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload an empty file.",
        )

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size} bytes) exceeds maximum limit ({settings.MAX_UPLOAD_SIZE_BYTES} bytes).",
        )

    # 3. Calculate SHA-256 checksum and metadata
    checksum = hashlib.sha256(contents).hexdigest()
    original_filename = sanitize_filename(file.filename or "unnamed_file")
    content_type = file.content_type or "application/octet-stream"
    asset_name = name or original_filename

    # 4. Generate asset_id and safe storage key
    asset_id = uuid.uuid4()
    storage_bucket = settings.OBJECT_STORAGE_BUCKET
    storage_key = generate_object_key(project_id, asset_id, original_filename)

    # 5. Store file object in storage provider
    try:
        storage.put_object(
            bucket=storage_bucket,
            key=storage_key,
            data=contents,
            content_type=content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store object in storage provider: {str(e)}",
        )

    # 6. Save Asset record in PostgreSQL (with rollback and storage cleanup on failure)
    asset = Asset(
        id=asset_id,
        project_id=project_id,
        name=asset_name,
        original_filename=original_filename,
        asset_type=asset_type,
        content_type=content_type,
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        is_locked=False,
    )

    try:
        db.add(asset)
        db.commit()
        db.refresh(asset)
    except Exception as db_err:
        db.rollback()
        # Attempt cleanup of orphaned storage object
        try:
            storage.delete_object(storage_bucket, storage_key)
        except Exception:
            pass  # Best-effort cleanup
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database persistence failed, uploaded object cleaned up: {str(db_err)}",
        )

    # 7. Generate presigned download URL
    download_url = storage.generate_presigned_url(storage_bucket, storage_key)

    response_data = AssetResponse.model_validate(asset)
    response_data.download_url = download_url
    return response_data


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    """Retrieve Asset metadata by asset_id."""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    download_url = storage.generate_presigned_url(asset.storage_bucket, asset.storage_key)
    response_data = AssetResponse.model_validate(asset)
    response_data.download_url = download_url
    return response_data


@router.get("/assets/{asset_id}/download", response_model=AssetDownloadResponse)
def get_asset_download_url(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    """Get presigned download access URL for an Asset."""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    if not storage.object_exists(asset.storage_bucket, asset.storage_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset object file missing from storage.",
        )

    download_url = storage.generate_presigned_url(asset.storage_bucket, asset.storage_key)
    return AssetDownloadResponse(asset_id=asset.id, download_url=download_url, expires_in=3600)


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    """Delete an Asset and its object storage payload."""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    # 1. Attempt object storage deletion
    try:
        storage.delete_object(asset.storage_bucket, asset.storage_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage object deletion failed: {str(e)}",
        )

    # 2. Delete DB record only after storage deletion succeeds
    db.delete(asset)
    db.commit()

    return {"status": "deleted", "asset_id": str(asset_id)}


@router.get("/projects/{project_id}/assets", response_model=List[AssetResponse])
def list_project_assets(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: ObjectStorageProvider = Depends(get_storage_provider),
):
    """List all assets for a project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    assets = db.query(Asset).filter(Asset.project_id == project_id).all()
    results = []
    for a in assets:
        resp = AssetResponse.model_validate(a)
        resp.download_url = storage.generate_presigned_url(a.storage_bucket, a.storage_key)
        results.append(resp)
    return results
