import os
import re
import tempfile
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.asset import Asset
from app.schemas.archive import (
    ProjectExportRequest,
    ProjectValidationResponse,
    ProjectImportResponse,
)
from app.services.archive.export_service import ProjectExportService, ArchiveExportError
from app.services.archive.import_service import (
    ProjectImportService,
    ArchiveImportError,
    ProjectCollisionError,
    VersionIncompatibilityError,
)
from app.services.archive.security import ArchiveSecurityError
from app.services.archive.checksums import ChecksumVerificationError

router = APIRouter()


def sanitize_filename(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "project"


def remove_temp_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@router.post(
    "/projects/{project_id}/export",
    status_code=status.HTTP_200_OK,
    summary="Export project archive (.orbis)",
)
def export_project_archive(
    project_id: uuid.UUID,
    export_req: ProjectExportRequest = ProjectExportRequest(),
    db: Session = Depends(get_db),
):
    """Exports a self-contained .orbis project archive package."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    export_service = ProjectExportService()
    try:
        archive_path, manifest = export_service.export_project(
            db=db,
            project_id=project_id,
            package_type=export_req.package_type,
            include_history=export_req.include_history,
            include_renders=export_req.include_renders,
        )
    except ArchiveExportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {str(e)}")

    filename = f"{sanitize_filename(project.title)}_{str(project.id)[:8]}.orbis"
    return FileResponse(
        path=archive_path,
        media_type="application/octet-stream",
        filename=filename,
        background=BackgroundTask(remove_temp_file, archive_path),
        headers={
            "X-Archive-Checksum": manifest.get("archive_checksum", ""),
            "X-Archive-Version": manifest.get("archive_format_version", "1.0.0"),
        },
    )


@router.post(
    "/projects/import/validate",
    response_model=ProjectValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Pre-flight validation of an .orbis archive",
)
async def validate_import_archive(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Validates an .orbis archive's security, checksums, and DB collision without mutating state."""
    if not file.filename.lower().endswith(".orbis") and not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid archive format. File must have a .orbis or .zip extension.",
        )

    with tempfile.NamedTemporaryFile(suffix=".orbis", delete=False) as tmp:
        tmp_path = tmp.name
        try:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                tmp.write(chunk)
            tmp.flush()
        except Exception as e:
            remove_temp_file(tmp_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read upload: {str(e)}")

    import_service = ProjectImportService()
    try:
        result = import_service.validate_project_archive(tmp_path, db)
        return ProjectValidationResponse(
            valid=result["valid"],
            archive_format_version=result["archive_format_version"],
            source_project_id=uuid.UUID(result["source_project_id"]),
            title=result.get("title") or "Untitled Project",
            video_mode=result.get("video_mode") or "STORY",
            entity_counts=result.get("entity_counts") or {},
            collision_detected=result["collision_detected"],
            allowed_modes=result["allowed_modes"],
            total_uncompressed_bytes=result.get("assets_summary", {}).get("total_bytes", 0),
            manifest_summary=result,
        )
    except (ArchiveSecurityError, ChecksumVerificationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except VersionIncompatibilityError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ArchiveImportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(e)}")
    finally:
        remove_temp_file(tmp_path)


@router.post(
    "/projects/import/execute",
    response_model=ProjectImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute import of an .orbis archive",
)
async def execute_import_archive(
    file: UploadFile = File(...),
    import_mode: str = Form("CLONE"),
    override_title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Executes atomic project import in CLONE or RESTORE mode."""
    mode_upper = import_mode.strip().upper()
    if mode_upper not in ("CLONE", "RESTORE"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid import_mode '{import_mode}'. Must be 'CLONE' or 'RESTORE'.")

    with tempfile.NamedTemporaryFile(suffix=".orbis", delete=False) as tmp:
        tmp_path = tmp.name
        try:
            while chunk := await file.read(1024 * 1024):
                tmp.write(chunk)
            tmp.flush()
        except Exception as e:
            remove_temp_file(tmp_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read upload: {str(e)}")

    import_service = ProjectImportService()
    try:
        project = import_service.execute_import(
            db=db,
            archive_path=tmp_path,
            import_mode=mode_upper,
            override_title=override_title.strip() if override_title else None,
        )
        # Count imported assets
        asset_count = db.query(Asset).filter(Asset.project_id == project.id).count()
        return ProjectImportResponse(
            project_id=project.id,
            title=project.title,
            status=project.status,
            import_mode=mode_upper,
            source_project_id=project.source_project_id or project.id,
            imported_asset_count=asset_count,
            created_at=project.created_at,
        )
    except ProjectCollisionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (ArchiveSecurityError, ChecksumVerificationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except VersionIncompatibilityError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ArchiveImportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import execution failed: {str(e)}")
    finally:
        remove_temp_file(tmp_path)
