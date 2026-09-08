import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.subtitle import SubtitleGenerateRequest, SubtitleReviewRequest, SubtitleTrackRead
from app.services.subtitle import SubtitleService

router = APIRouter(prefix="/projects/{project_id}/subtitles")


@router.get("/active", response_model=Optional[SubtitleTrackRead])
def get_active_subtitles(
    project_id: uuid.UUID,
    timeline_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return SubtitleService.get_active(db, project_id, timeline_id)


@router.post("/generate", response_model=SubtitleTrackRead)
def generate_subtitles(
    project_id: uuid.UUID,
    payload: SubtitleGenerateRequest = SubtitleGenerateRequest(),
    db: Session = Depends(get_db),
):
    return SubtitleService.generate(
        db=db,
        project_id=project_id,
        timeline_id=payload.timeline_id,
        language=payload.language,
    )


@router.post("/review", response_model=SubtitleTrackRead)
def review_subtitles(
    project_id: uuid.UUID,
    payload: SubtitleReviewRequest,
    timeline_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return SubtitleService.review(
        db=db,
        project_id=project_id,
        enabled=payload.enabled,
        render_mode=payload.render_mode,
        timeline_id=timeline_id,
    )


@router.get("/srt")
def export_subtitles_srt(
    project_id: uuid.UUID,
    timeline_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    content, evidence = SubtitleService.export_srt(db, project_id, timeline_id)
    headers = {
        "Content-Disposition": f'attachment; filename="orbis_subtitles_v{evidence["timeline_version"]}.srt"',
        "X-Orbis-Subtitle-Track-Id": evidence["track_id"],
        "X-Orbis-Timeline-Version": evidence["timeline_version"],
        "X-Orbis-SRT-SHA256": evidence["sha256"],
    }
    return Response(content=content.encode("utf-8"), media_type="application/x-subrip; charset=utf-8", headers=headers)
