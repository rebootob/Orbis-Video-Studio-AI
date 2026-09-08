import copy
import uuid
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.project import Project
from app.models.render_job import RenderJob, RenderJobStatus
from app.services.subtitle import SubtitleService as DeterministicSubtitleService


PORTABLE_SUBTITLE_NAMESPACE = "core_v1_subtitles"
ACTIVE_RENDER_STATUSES = (
    RenderJobStatus.QUEUED.value,
    RenderJobStatus.CLAIMED.value,
    RenderJobStatus.RUNNING.value,
    RenderJobStatus.RECONCILIATION_REQUIRED.value,
)


class SubtitleService(DeterministicSubtitleService):
    """Safety/portability wrapper around the deterministic Core V1 subtitle engine.

    Two repository contracts are enforced here without changing archive or render
    architecture:
    1. mirror subtitle state into Project.mode_config, which .orbis already
       exports/imports, so CLONE/RESTORE does not silently lose subtitle truth;
    2. serialize subtitle mutations against RenderJob submission using the same
       Project row authority, then reject mutation while a live render for the
       exact timeline is active.
    """

    @staticmethod
    def _project_for_update(db: Session, project_id: uuid.UUID) -> Project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id)
            .with_for_update()
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @staticmethod
    def _ensure_no_active_render(
        db: Session,
        project_id: uuid.UUID,
        timeline_id: uuid.UUID,
    ) -> None:
        active = (
            db.query(RenderJob)
            .filter(
                RenderJob.project_id == project_id,
                RenderJob.timeline_id == timeline_id,
                RenderJob.imported_historical.isnot(True),
                RenderJob.execution_disabled.isnot(True),
                RenderJob.status.in_(ACTIVE_RENDER_STATUSES),
            )
            .order_by(RenderJob.created_at.asc())
            .first()
        )
        if active:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Subtitle state is frozen while render job {active.id} is {active.status}. "
                    "Cancel/settle the render before changing subtitles."
                ),
            )

    @classmethod
    def _portable_state_for_timeline(
        cls,
        db: Session,
        timeline,
    ) -> Optional[Dict[str, Any]]:
        project = db.get(Project, timeline.project_id)
        if not project or not isinstance(project.mode_config, dict):
            return None
        namespace = project.mode_config.get(PORTABLE_SUBTITLE_NAMESPACE)
        if not isinstance(namespace, dict):
            return None
        tracks = namespace.get("tracks")
        if not isinstance(tracks, list):
            return None

        fingerprint = DeterministicSubtitleService.compute_timeline_fingerprint(db, timeline)
        for entry in reversed(tracks):
            if not isinstance(entry, dict):
                continue
            if int(entry.get("timeline_version", -1)) != int(timeline.version):
                continue
            if str(entry.get("timeline_fingerprint") or "") != fingerprint:
                continue
            state = entry.get("state")
            if isinstance(state, dict):
                return copy.deepcopy(state)
        return None

    @staticmethod
    def _resolve_timeline(db: Session, project_id: uuid.UUID, timeline_id: Optional[str] = None):
        timeline = DeterministicSubtitleService._resolve_timeline(db, project_id, timeline_id)
        if not isinstance(timeline.subtitle_state, dict):
            portable = SubtitleService._portable_state_for_timeline(db, timeline)
            if portable:
                # Hydrate the runtime copy in-memory. Mutation paths persist it
                # atomically; read paths need no write merely to inspect state.
                timeline.subtitle_state = portable
        return timeline

    @staticmethod
    def _store_state(db: Session, timeline, state: Dict[str, Any]) -> None:
        project = (
            db.query(Project)
            .filter(Project.id == timeline.project_id)
            .with_for_update()
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        active = state.get("active") if isinstance(state, dict) else None
        if not isinstance(active, dict):
            raise RuntimeError("Subtitle state missing active track")

        timeline.subtitle_state = copy.deepcopy(state)
        flag_modified(timeline, "subtitle_state")

        mode_config = copy.deepcopy(project.mode_config) if isinstance(project.mode_config, dict) else {}
        namespace = mode_config.get(PORTABLE_SUBTITLE_NAMESPACE)
        if not isinstance(namespace, dict):
            namespace = {"schema_version": 1, "tracks": []}
        existing = namespace.get("tracks")
        tracks = list(existing) if isinstance(existing, list) else []

        # Keep one portable current state per semantic timeline version. Prior
        # subtitle versions remain inside state's append-only history.
        tracks = [
            entry
            for entry in tracks
            if not (
                isinstance(entry, dict)
                and int(entry.get("timeline_version", -1)) == int(timeline.version)
            )
        ]
        tracks.append({
            "timeline_version": int(timeline.version),
            "timeline_fingerprint": str(active.get("timeline_fingerprint") or ""),
            "state": copy.deepcopy(state),
        })
        namespace["schema_version"] = 1
        namespace["tracks"] = tracks
        mode_config[PORTABLE_SUBTITLE_NAMESPACE] = namespace
        project.mode_config = mode_config
        flag_modified(project, "mode_config")

        db.add(timeline)
        db.add(project)
        db.commit()
        db.refresh(timeline)

    @classmethod
    def generate(
        cls,
        db: Session,
        project_id: uuid.UUID,
        timeline_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        cls._project_for_update(db, project_id)
        timeline = cls._resolve_timeline(db, project_id, timeline_id)
        cls._ensure_no_active_render(db, project_id, timeline.id)
        return super().generate(db, project_id, timeline_id, language)

    @classmethod
    def review(
        cls,
        db: Session,
        project_id: uuid.UUID,
        enabled: bool,
        render_mode: str,
        timeline_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cls._project_for_update(db, project_id)
        timeline = cls._resolve_timeline(db, project_id, timeline_id)
        cls._ensure_no_active_render(db, project_id, timeline.id)
        return super().review(db, project_id, enabled, render_mode, timeline_id)
