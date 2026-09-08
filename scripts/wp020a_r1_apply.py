from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{rel}: expected exactly one match, found {count}: {old[:120]!r}")
    write(rel, text.replace(old, new, 1))


def replace_regex_once(rel: str, pattern: str, replacement: str) -> None:
    text = read(rel)
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{rel}: expected exactly one regex match, found {count}: {pattern[:120]!r}")
    write(rel, new_text)


# ---------------------------------------------------------------------------
# S1-A03: canonical STORY-linked scenes must participate in Assembly.
# ---------------------------------------------------------------------------
replace_once(
    "backend/app/services/assembly.py",
    """        # Fetch canonical project scenes & shots\n        db_scenes = db.query(Scene).filter(Scene.project_id == p_uuid).order_by(Scene.scene_number.asc()).all()\n        db_scene_map: Dict[str, Scene] = {str(s.id): s for s in db_scenes}\n        scene_ids = [s.id for s in db_scenes]\n\n        shots = []\n        if scene_ids:\n            shots = db.query(Shot).filter(Shot.scene_id.in_(scene_ids)).order_by(Shot.shot_number.asc()).all()\n""",
    """        # Fetch the canonical project graph through either direct project lineage\n        # or STORY lineage. Keep archived history out of the live assembly graph.\n        db_scenes = (\n            db.query(Scene)\n            .filter((Scene.project_id == p_uuid) | (Scene.story.has(project_id=p_uuid)))\n            .order_by(Scene.scene_number.asc(), Scene.id.asc())\n            .all()\n        )\n        db_scenes = [s for s in db_scenes if not (s.scene_config or {}).get(\"archived\")]\n        db_scene_map: Dict[str, Scene] = {str(s.id): s for s in db_scenes}\n        scene_ids = [s.id for s in db_scenes]\n\n        shots = []\n        if scene_ids:\n            shots = (\n                db.query(Shot)\n                .filter(Shot.scene_id.in_(scene_ids), Shot.status != \"ARCHIVED\")\n                .order_by(Shot.shot_number.asc(), Shot.id.asc())\n                .all()\n            )\n""",
)

# Production readiness must be backed by a durable generated output, not only a
# provider COMPLETED status.
replace_once(
    "backend/app/services/production_orchestrator.py",
    """                            GenerationJob.imported_historical.isnot(True),\n                            GenerationJob.status == \"COMPLETED\",\n""",
    """                            GenerationJob.imported_historical.isnot(True),\n                            GenerationJob.status == \"COMPLETED\",\n                            GenerationJob.output_asset_id.isnot(None),\n""",
)
replace_once(
    "backend/app/services/production_orchestrator.py",
    """                if (s.id in completed_job_shot_ids) or (\n""",
    """                if (s.id in completed_job_shot_ids and s.source_asset_id is not None) or (\n""",
)

# ---------------------------------------------------------------------------
# S1-A01: materialize completed provider VIDEO output into durable Orbis truth.
# ---------------------------------------------------------------------------
VIDEO_SERVICE = r'''"""Durable materialization of completed VideoProvider outputs.

Provider completion is not production completion until the media is safely
retrieved, persisted to Orbis object storage, represented by a VIDEO Asset, and
bound to both the GenerationJob and Shot. The operation is idempotent by job ID.
"""
import asyncio
import hashlib
import ipaddress
import os
import socket
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Tuple
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.story import Story
from app.providers.base import ProviderJobResult
from app.services.storage import ObjectStorageProvider, get_storage_provider

MAX_VIDEO_BYTES = 1024 * 1024 * 1024  # 1 GiB bounded Core V1 retrieval
DownloadFn = Callable[[str, str], Awaitable[Tuple[str, int, str]]]


class VideoMaterializationError(RuntimeError):
    pass


def _utc_now():
    return datetime.now(timezone.utc)


class VideoMaterializationService:
    @staticmethod
    def _resolve_project(db: Session, shot: Shot) -> Optional[Project]:
        scene = db.get(Scene, shot.scene_id) if shot and shot.scene_id else None
        if not scene:
            return None
        if scene.project_id:
            return db.get(Project, scene.project_id)
        if scene.story_id:
            story = db.get(Story, scene.story_id)
            if story and story.project_id:
                return db.get(Project, story.project_id)
        return None

    @staticmethod
    async def _validate_public_https_url(url: str) -> None:
        parsed = urlsplit(str(url or ""))
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise VideoMaterializationError("Completed provider output must use an HTTPS URL")
        host = parsed.hostname.strip().lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            raise VideoMaterializationError("Private/local provider output host is not allowed")

        def validate_ip(raw: str) -> None:
            ip = ipaddress.ip_address(raw)
            if not ip.is_global:
                raise VideoMaterializationError("Provider output resolved to a non-public address")

        try:
            validate_ip(host)
            return
        except ValueError:
            pass

        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                parsed.port or 443,
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise VideoMaterializationError("Provider output host could not be resolved") from exc
        addresses = {info[4][0] for info in infos if info and info[4]}
        if not addresses:
            raise VideoMaterializationError("Provider output host resolved to no addresses")
        for address in addresses:
            validate_ip(address)

    @staticmethod
    async def _download_video_to_file(url: str, target_file_path: str) -> Tuple[str, int, str]:
        await VideoMaterializationService._validate_public_https_url(url)
        timeout = httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=15.0)
        size = 0
        sha256 = hashlib.sha256()
        content_type = "application/octet-stream"
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            async with client.stream("GET", url, headers={"Accept": "video/*,application/octet-stream"}) as response:
                if response.status_code != 200:
                    raise VideoMaterializationError("Provider output download did not return HTTP 200")
                content_type = (response.headers.get("content-type") or "application/octet-stream").split(";", 1)[0].strip().lower()
                if not (content_type.startswith("video/") or content_type == "application/octet-stream"):
                    raise VideoMaterializationError("Provider output content type is not video media")
                length = response.headers.get("content-length")
                if length:
                    try:
                        if int(length) <= 0 or int(length) > MAX_VIDEO_BYTES:
                            raise VideoMaterializationError("Provider output size is outside the Core V1 bound")
                    except ValueError as exc:
                        raise VideoMaterializationError("Invalid provider output Content-Length") from exc
                with open(target_file_path, "wb") as output:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > MAX_VIDEO_BYTES:
                            raise VideoMaterializationError("Provider output exceeded the Core V1 size bound")
                        sha256.update(chunk)
                        output.write(chunk)
        if size <= 0:
            raise VideoMaterializationError("Provider completed without usable video bytes")
        return content_type, size, sha256.hexdigest()

    @staticmethod
    def _extension(content_type: str) -> str:
        return {
            "video/webm": "webm",
            "video/quicktime": "mov",
            "video/x-matroska": "mkv",
        }.get(content_type, "mp4")

    @classmethod
    async def materialize_completed_result(
        cls,
        db: Session,
        job_id: uuid.UUID,
        result: ProviderJobResult,
        *,
        storage_provider: Optional[ObjectStorageProvider] = None,
        downloader: Optional[DownloadFn] = None,
    ) -> Asset:
        job = db.get(GenerationJob, job_id)
        if not job or getattr(job, "job_type", "VIDEO") != "VIDEO":
            raise VideoMaterializationError("Video GenerationJob not found")
        if result.status != "COMPLETED" or not result.video_url:
            raise VideoMaterializationError("Provider result is not a materializable completed video")
        shot = db.get(Shot, job.shot_id)
        if not shot:
            raise VideoMaterializationError("GenerationJob Shot not found")
        project = cls._resolve_project(db, shot)
        if not project:
            raise VideoMaterializationError("GenerationJob Project could not be resolved")

        asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"orbis://video-generation/{job.id}")
        existing = db.get(Asset, asset_id)
        if existing:
            if existing.project_id != project.id or existing.asset_type != "VIDEO":
                raise VideoMaterializationError("Existing deterministic video Asset conflicts with GenerationJob")
            if shot.is_locked and shot.source_asset_id not in (None, existing.id):
                raise VideoMaterializationError("Shot became locked before completed output could be bound")
            job.output_asset_id = existing.id
            shot.source_asset_id = existing.id
            db.commit()
            return existing

        if shot.is_locked and shot.source_asset_id is not None:
            raise VideoMaterializationError("Shot became locked before completed output could be bound")

        storage = storage_provider or get_storage_provider()
        fetch = downloader or cls._download_video_to_file
        temp_path = None
        uploaded_bucket = None
        uploaded_key = None
        uploaded_new_object = False
        try:
            with tempfile.NamedTemporaryFile(prefix=f"orbis_video_{job.id}_", suffix=".media", delete=False) as tmp:
                temp_path = tmp.name
            content_type, size, checksum = await fetch(str(result.video_url), temp_path)
            if size <= 0 or not checksum:
                raise VideoMaterializationError("Downloaded provider output failed integrity checks")
            ext = cls._extension(content_type)
            bucket = str(getattr(settings, "OBJECT_STORAGE_BUCKET", "") or "orbis-assets")
            storage_key = f"projects/{project.id}/generated-video/{job.id}/{checksum[:16]}.{ext}"
            storage.ensure_bucket_exists(bucket)
            existed = storage.object_exists(bucket, storage_key)
            if not existed:
                storage.upload_file_object(bucket, storage_key, temp_path, content_type)
                uploaded_new_object = True
            uploaded_bucket = bucket
            uploaded_key = storage_key

            asset = Asset(
                id=asset_id,
                project_id=project.id,
                name=f"Generated Video Shot {shot.shot_number}",
                original_filename=f"generated_shot_{shot.shot_number}.{ext}",
                asset_type="VIDEO",
                content_type=content_type,
                file_size_bytes=size,
                checksum_sha256=checksum,
                storage_bucket=bucket,
                storage_key=storage_key,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            db.add(asset)
            db.flush()
            job.output_asset_id = asset.id
            shot.source_asset_id = asset.id
            shot.updated_at = _utc_now()
            db.commit()
            db.refresh(asset)
            return asset
        except Exception as exc:
            db.rollback()
            if uploaded_new_object and uploaded_bucket and uploaded_key:
                try:
                    storage.delete_object(uploaded_bucket, uploaded_key)
                except Exception:
                    pass
            if isinstance(exc, VideoMaterializationError):
                raise
            raise VideoMaterializationError("Completed provider video could not be durably materialized") from exc
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except FileNotFoundError:
                    pass
'''
write("backend/app/services/video_materialization.py", VIDEO_SERVICE)

# Synchronous provider completion: materialize before allowing COMPLETED state.
replace_once(
    "backend/app/services/job_dispatch.py",
    """        if res.provider_job_id and (not re.fullmatch(r\"[A-Za-z0-9_-]{1,255}\", res.provider_job_id) or contains_secret(res.provider_job_id)):\n            res = ProviderJobResult(provider_job_id=\"\", status=\"FAILED\", submission_uncertain=True)\n        now = now if supplied_now is not None else utc_now()\n""",
    """        if res.provider_job_id and (not re.fullmatch(r\"[A-Za-z0-9_-]{1,255}\", res.provider_job_id) or contains_secret(res.provider_job_id)):\n            res = ProviderJobResult(provider_job_id=\"\", status=\"FAILED\", submission_uncertain=True)\n\n        if res.status == \"COMPLETED\" and getattr(job, \"job_type\", \"VIDEO\") == \"VIDEO\":\n            try:\n                from app.services.video_materialization import VideoMaterializationService\n                await VideoMaterializationService.materialize_completed_result(db, job.id, res)\n            except Exception:\n                now = now if supplied_now is not None else utc_now()\n                failed_values = released()\n                failed_values.update(\n                    provider_job_id=res.provider_job_id or None,\n                    result=safe_result(res),\n                    status=\"RECONCILIATION_REQUIRED\",\n                    error_message=\"Provider completed but durable video materialization failed; manual reconciliation required\",\n                    next_retry_at=None,\n                    next_poll_at=None,\n                )\n                change(db, [\n                    Job.id == job_id,\n                    Job.status == \"SUBMITTING\",\n                    Job.claim_token == claim_token,\n                    Job.submission_attempt_id == attempt,\n                ], failed_values)\n                from app.services.cost_ledger import CostLedgerService\n                CostLedgerService.confirm_job_cost(\n                    db, job_id, actual_cost=res.cost_usd, provider_event_id=res.provider_job_id\n                )\n                return load(db, job_id)\n\n        now = now if supplied_now is not None else utc_now()\n""",
)

# Poll completion: same durable-output gate before COMPLETED state.
replace_once(
    "backend/app/services/job_dispatch.py",
    """        now = now if supplied_now is not None else utc_now()\n        values = {\n            **released(),\n            \"result\": safe_result(res),\n""",
    """        if res.status == \"COMPLETED\" and getattr(job, \"job_type\", \"VIDEO\") == \"VIDEO\":\n            try:\n                from app.services.video_materialization import VideoMaterializationService\n                await VideoMaterializationService.materialize_completed_result(db, job.id, res)\n            except Exception:\n                now = now if supplied_now is not None else utc_now()\n                failed_values = {\n                    **released(),\n                    \"provider_job_id\": job.provider_job_id,\n                    \"result\": safe_result(res),\n                    \"status\": \"RECONCILIATION_REQUIRED\",\n                    \"error_message\": \"Provider completed but durable video materialization failed; manual reconciliation required\",\n                    \"next_retry_at\": None,\n                    \"next_poll_at\": None,\n                }\n                change(db, [Job.id == job_id, Job.status == \"POLLING\", Job.claim_token == token], failed_values)\n                from app.services.cost_ledger import CostLedgerService\n                CostLedgerService.confirm_job_cost(\n                    db, job_id, actual_cost=res.cost_usd, provider_event_id=job.provider_job_id\n                )\n                return load(db, job_id)\n\n        now = now if supplied_now is not None else utc_now()\n        values = {\n            **released(),\n            \"result\": safe_result(res),\n""",
)

# ---------------------------------------------------------------------------
# S1-A02 plus the directly coupled canonical archive graph/schema drift exposed
# by the integrated FULL_SELF_CONTAINED roundtrip.
# ---------------------------------------------------------------------------
replace_once(
    "backend/app/services/archive/export_service.py",
    """        scenes = db.query(Scene).filter(Scene.project_id == p_id).order_by(Scene.scene_number).all()\n""",
    """        scenes = (\n            db.query(Scene)\n            .filter((Scene.project_id == p_id) | (Scene.story.has(project_id=p_id)))\n            .order_by(Scene.scene_number, Scene.id)\n            .all()\n        )\n""",
)
replace_once(
    "backend/app/services/archive/export_service.py",
    """            db.query(AudioClipHistory).filter(AudioClipHistory.audio_clip_id.in_(clip_ids)).all() if clip_ids else []\n""",
    """            db.query(AudioClipHistory).filter(AudioClipHistory.clip_id.in_(clip_ids)).all() if clip_ids else []\n""",
)

# Preflight accepts canonical clip_id, with legacy alias only for backward archive compatibility.
replace_once(
    "backend/app/services/archive/import_service.py",
    """        for ach in audio_data.get(\"audio_clip_histories\", []):\n            cid = parse_uuid(ach.get(\"audio_clip_id\"))\n            if not cid or cid not in self.audio_clip_ids:\n                raise ArchivePreflightError(f\"AudioClipHistory '{ach.get('id')}' references nonexistent AudioClip '{cid}'\")\n""",
    """        for ach in audio_data.get(\"audio_clip_histories\", []):\n            cid = parse_uuid(ach.get(\"clip_id\") or ach.get(\"audio_clip_id\"))\n            if not cid or cid not in self.audio_clip_ids:\n                raise ArchivePreflightError(f\"AudioClipHistory '{ach.get('id')}' references nonexistent AudioClip '{cid}'\")\n""",
)
replace_once(
    "backend/app/services/archive/import_service.py",
    """            if ac.get(\"asset_id\"):\n                aid = parse_uuid(ac[\"asset_id\"])\n                if not aid or aid not in self.asset_ids:\n                    raise ArchivePreflightError(f\"AudioClip '{ac.get('id')}' references nonexistent Asset '{aid}'\")\n""",
    """            if ac.get(\"asset_id\"):\n                aid = parse_uuid(ac[\"asset_id\"])\n                if not aid or aid not in self.asset_ids:\n                    raise ArchivePreflightError(f\"AudioClip '{ac.get('id')}' references nonexistent Asset '{aid}'\")\n            if ac.get(\"video_asset_id\"):\n                aid = parse_uuid(ac[\"video_asset_id\"])\n                if not aid or aid not in self.asset_ids:\n                    raise ArchivePreflightError(f\"AudioClip '{ac.get('id')}' references nonexistent video Asset '{aid}'\")\n""",
)
replace_once(
    "backend/app/services/archive/import_service.py",
    """            if asp.get(\"asset_id\"):\n                aid = parse_uuid(asp[\"asset_id\"])\n                if not aid or aid not in self.asset_ids:\n                    raise ArchivePreflightError(f\"AssemblyShotPlacement '{asp.get('id')}' references nonexistent Asset '{aid}'\")\n""",
    """            visual_asset_raw = asp.get(\"visual_asset_id\") or asp.get(\"asset_id\")\n            if visual_asset_raw:\n                aid = parse_uuid(visual_asset_raw)\n                if not aid or aid not in self.asset_ids:\n                    raise ArchivePreflightError(f\"AssemblyShotPlacement '{asp.get('id')}' references nonexistent Asset '{aid}'\")\n""",
)

# Preserve STORY lineage when importing scenes.
replace_once(
    "backend/app/services/archive/import_service.py",
    """                    db.add(Scene(\n                        id=new_scid,\n                        project_id=new_project_id,\n                        scene_number=sc.get(\"scene_number\", 1),\n""",
    """                    db.add(Scene(\n                        id=new_scid,\n                        story_id=remap.get_or_create(parse_uuid(sc.get(\"story_id\")), \"STORY\"),\n                        project_id=new_project_id if sc.get(\"project_id\") else None,\n                        scene_number=sc.get(\"scene_number\", 1),\n""",
)

OLD_AUDIO_IMPORT = '''                for ap in aud.get("audio_plans", []):
                    db.add(AudioPlan(
                        id=remap.get_or_create(parse_uuid(ap["id"]), "AUDIO_PLAN"),
                        project_id=new_project_id,
                        version_number=ap.get("version_number", 1),
                        status=ap.get("status", "DRAFT"),
                        created_at=parse_datetime(ap.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ap.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for apv in aud.get("audio_plan_versions", []):
                    db.add(AudioPlanVersion(
                        id=remap.get_or_create(parse_uuid(apv["id"]), "AUDIO_PLAN_VERSION"),
                        audio_plan_id=remap.get_or_create(parse_uuid(apv["audio_plan_id"]), "AUDIO_PLAN"),
                        version_number=apv.get("version_number", 1),
                        plan_data=apv.get("plan_data"),
                        created_at=parse_datetime(apv.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for ac in aud.get("audio_clips", []):
                    db.add(AudioClip(
                        id=remap.get_or_create(parse_uuid(ac["id"]), "AUDIO_CLIP"),
                        project_id=new_project_id,
                        scene_id=remap.get_or_create(parse_uuid(ac.get("scene_id")), "SCENE"),
                        shot_id=remap.get_or_create(parse_uuid(ac.get("shot_id")), "SHOT"),
                        asset_id=remap.get_or_create(parse_uuid(ac.get("asset_id")), "ASSET"),
                        audio_type=ac.get("audio_type", "VOICEOVER"),
                        name=ac.get("name", "clip"),
                        duration_seconds=ac.get("duration_seconds", 0.0),
                        timeline_start_seconds=ac.get("timeline_start_seconds", 0.0),
                        volume=ac.get("volume", 1.0),
                        is_muted=ac.get("is_muted", False),
                        ducking_role=ac.get("ducking_role"),
                        created_at=parse_datetime(ac.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ac.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for ach in aud.get("audio_clip_histories", []):
                    db.add(AudioClipHistory(
                        id=remap.get_or_create(parse_uuid(ach["id"]), "AUDIO_CLIP_HISTORY"),
                        audio_clip_id=remap.get_or_create(parse_uuid(ach["audio_clip_id"]), "AUDIO_CLIP"),
                        asset_id=remap.get_or_create(parse_uuid(ach.get("asset_id")), "ASSET"),
                        iteration_number=ach.get("iteration_number", 1),
                        change_reason=ach.get("change_reason"),
                        created_at=parse_datetime(ach.get("created_at")) or datetime.now(timezone.utc),
                    ))
'''
NEW_AUDIO_IMPORT = '''                for ap in aud.get("audio_plans", []):
                    db.add(AudioPlan(
                        id=remap.get_or_create(parse_uuid(ap["id"]), "AUDIO_PLAN"),
                        project_id=new_project_id,
                        status=ap.get("status", "DRAFT"),
                        plan_data=ap.get("plan_data"),
                        version=ap.get("version", ap.get("version_number", 1)),
                        created_at=parse_datetime(ap.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ap.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for apv in aud.get("audio_plan_versions", []):
                    db.add(AudioPlanVersion(
                        id=remap.get_or_create(parse_uuid(apv["id"]), "AUDIO_PLAN_VERSION"),
                        audio_plan_id=remap.get_or_create(parse_uuid(apv["audio_plan_id"]), "AUDIO_PLAN"),
                        project_id=new_project_id,
                        version_number=apv.get("version_number", 1),
                        status=apv.get("status", "DRAFT"),
                        plan_data=apv.get("plan_data"),
                        actor=apv.get("actor", "USER"),
                        action=apv.get("action", "CREATE"),
                        change_reason=apv.get("change_reason"),
                        created_at=parse_datetime(apv.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for ac in aud.get("audio_clips", []):
                    db.add(AudioClip(
                        id=remap.get_or_create(parse_uuid(ac["id"]), "AUDIO_CLIP"),
                        project_id=new_project_id,
                        scene_id=remap.get_or_create(parse_uuid(ac.get("scene_id")), "SCENE"),
                        shot_id=remap.get_or_create(parse_uuid(ac.get("shot_id")), "SHOT"),
                        video_asset_id=remap.get_or_create(parse_uuid(ac.get("video_asset_id")), "ASSET"),
                        asset_id=remap.get_or_create(parse_uuid(ac.get("asset_id")), "ASSET"),
                        audio_type=ac.get("audio_type", "VO"),
                        source_type=ac.get("source_type", "IMPORTED_AUDIO"),
                        generation_mode=ac.get("generation_mode", "SEPARATE_AUDIO"),
                        scope=ac.get("scope", "PROJECT"),
                        name=ac.get("name", "clip"),
                        prompt=ac.get("prompt"),
                        start_time=float(ac.get("start_time", ac.get("timeline_start_seconds", 0.0)) or 0.0),
                        duration_seconds=ac.get("duration_seconds"),
                        volume=float(ac.get("volume", 1.0) or 0.0),
                        mute=bool(ac.get("mute", ac.get("is_muted", False))),
                        fade_in=float(ac.get("fade_in", 0.0) or 0.0),
                        fade_out=float(ac.get("fade_out", 0.0) or 0.0),
                        ducking_role=ac.get("ducking_role", "BACKGROUND"),
                        ducking_amount_db=float(ac.get("ducking_amount_db", -12.0) or 0.0),
                        language=ac.get("language"),
                        speaker=ac.get("speaker"),
                        is_locked=bool(ac.get("is_locked", False)),
                        version=int(ac.get("version", 1) or 1),
                        provenance=ac.get("provenance"),
                        status=ac.get("status", "PENDING"),
                        created_at=parse_datetime(ac.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ac.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for ach in aud.get("audio_clip_histories", []):
                    raw_clip_id = ach.get("clip_id") or ach.get("audio_clip_id")
                    db.add(AudioClipHistory(
                        id=remap.get_or_create(parse_uuid(ach["id"]), "AUDIO_CLIP_HISTORY"),
                        clip_id=remap.get_or_create(parse_uuid(raw_clip_id), "AUDIO_CLIP"),
                        project_id=new_project_id,
                        version_number=int(ach.get("version_number", ach.get("iteration_number", 1)) or 1),
                        audio_type=ach.get("audio_type", "VO"),
                        source_type=ach.get("source_type", "IMPORTED_AUDIO"),
                        generation_mode=ach.get("generation_mode", "SEPARATE_AUDIO"),
                        scope=ach.get("scope", "PROJECT"),
                        name=ach.get("name", "clip"),
                        prompt=ach.get("prompt"),
                        start_time=float(ach.get("start_time", ach.get("timeline_start_seconds", 0.0)) or 0.0),
                        duration_seconds=ach.get("duration_seconds"),
                        volume=float(ach.get("volume", 1.0) or 0.0),
                        mute=bool(ach.get("mute", ach.get("is_muted", False))),
                        fade_in=float(ach.get("fade_in", 0.0) or 0.0),
                        fade_out=float(ach.get("fade_out", 0.0) or 0.0),
                        ducking_role=ach.get("ducking_role", "BACKGROUND"),
                        ducking_amount_db=float(ach.get("ducking_amount_db", -12.0) or 0.0),
                        language=ach.get("language"),
                        speaker=ach.get("speaker"),
                        is_locked=bool(ach.get("is_locked", False)),
                        status=ach.get("status", "PENDING"),
                        asset_id=remap.get_or_create(parse_uuid(ach.get("asset_id")), "ASSET"),
                        provenance=ach.get("provenance"),
                        actor=ach.get("actor", "USER"),
                        action=ach.get("action", "CREATE"),
                        change_reason=ach.get("change_reason"),
                        created_at=parse_datetime(ach.get("created_at")) or datetime.now(timezone.utc),
                    ))
'''
replace_once("backend/app/services/archive/import_service.py", OLD_AUDIO_IMPORT, NEW_AUDIO_IMPORT)

OLD_ASSEMBLY_IMPORT = '''                for tm in asm.get("timelines", []):
                    db.add(AssemblyTimeline(
                        id=remap.get_or_create(parse_uuid(tm["id"]), "TIMELINE"),
                        project_id=new_project_id,
                        version=tm.get("version", 1),
                        is_active=tm.get("is_active", False),
                        status=tm.get("status", "DRAFT"),
                        created_at=parse_datetime(tm.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(tm.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for asc in asm.get("assembly_scenes", []):
                    db.add(AssemblyScene(
                        id=remap.get_or_create(parse_uuid(asc["id"]), "ASSEMBLY_SCENE"),
                        timeline_id=remap.get_or_create(parse_uuid(asc["timeline_id"]), "TIMELINE"),
                        scene_id=remap.get_or_create(parse_uuid(asc["scene_id"]), "SCENE"),
                        scene_order=asc.get("scene_order", 1),
                        created_at=parse_datetime(asc.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(asc.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for asp in asm.get("assembly_shot_placements", []):
                    db.add(AssemblyShotPlacement(
                        id=remap.get_or_create(parse_uuid(asp["id"]), "ASSEMBLY_SHOT_PLACEMENT"),
                        timeline_id=remap.get_or_create(parse_uuid(asp["timeline_id"]), "TIMELINE"),
                        assembly_scene_id=remap.get_or_create(parse_uuid(asp["assembly_scene_id"]), "ASSEMBLY_SCENE"),
                        shot_id=remap.get_or_create(parse_uuid(asp["shot_id"]), "SHOT"),
                        asset_id=remap.get_or_create(parse_uuid(asp.get("asset_id")), "ASSET"),
                        placement_order=asp.get("placement_order", 1),
                        duration_seconds=asp.get("duration_seconds", 0.0),
                        start_time_seconds=asp.get("start_time_seconds", 0.0),
                        trim_in_seconds=asp.get("trim_in_seconds", 0.0),
                        trim_out_seconds=asp.get("trim_out_seconds", 0.0),
                        transition_type=asp.get("transition_type", "CUT"),
                        transition_duration_seconds=asp.get("transition_duration_seconds", 0.0),
                        is_locked=asp.get("is_locked", False),
                        created_at=parse_datetime(asp.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(asp.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for chk in asm.get("checkpoints", []):
                    db.add(TimelineCheckpoint(
                        id=remap.get_or_create(parse_uuid(chk["id"]), "TIMELINE_CHECKPOINT"),
                        timeline_id=remap.get_or_create(parse_uuid(chk["timeline_id"]), "TIMELINE"),
                        label=chk.get("label", "checkpoint"),
                        checkpoint_data=chk.get("checkpoint_data"),
                        created_at=parse_datetime(chk.get("created_at")) or datetime.now(timezone.utc),
                    ))
'''
NEW_ASSEMBLY_IMPORT = '''                for tm in asm.get("timelines", []):
                    db.add(AssemblyTimeline(
                        id=remap.get_or_create(parse_uuid(tm["id"]), "TIMELINE"),
                        project_id=new_project_id,
                        version=tm.get("version", 1),
                        is_active=tm.get("is_active", False),
                        status=tm.get("status", "DRAFT"),
                        subtitle_state=tm.get("subtitle_state"),
                        created_at=parse_datetime(tm.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(tm.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for asc in asm.get("assembly_scenes", []):
                    db.add(AssemblyScene(
                        id=remap.get_or_create(parse_uuid(asc["id"]), "ASSEMBLY_SCENE"),
                        timeline_id=remap.get_or_create(parse_uuid(asc["timeline_id"]), "TIMELINE"),
                        scene_id=remap.get_or_create(parse_uuid(asc["scene_id"]), "SCENE"),
                        scene_order=asc.get("scene_order", 0),
                        created_at=parse_datetime(asc.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(asc.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for asp in asm.get("assembly_shot_placements", []):
                    visual_raw = asp.get("visual_asset_id") or asp.get("asset_id")
                    db.add(AssemblyShotPlacement(
                        id=remap.get_or_create(parse_uuid(asp["id"]), "ASSEMBLY_SHOT_PLACEMENT"),
                        timeline_id=remap.get_or_create(parse_uuid(asp["timeline_id"]), "TIMELINE"),
                        assembly_scene_id=remap.get_or_create(parse_uuid(asp["assembly_scene_id"]), "ASSEMBLY_SCENE"),
                        scene_id=remap.get_or_create(parse_uuid(asp.get("scene_id")), "SCENE"),
                        shot_id=remap.get_or_create(parse_uuid(asp["shot_id"]), "SHOT"),
                        shot_order=int(asp.get("shot_order", asp.get("placement_order", 0)) or 0),
                        visual_asset_id=remap.get_or_create(parse_uuid(visual_raw), "ASSET"),
                        source_type=asp.get("source_type", "VIDEO"),
                        trim_in=float(asp.get("trim_in", asp.get("trim_in_seconds", 0.0)) or 0.0),
                        trim_out=asp.get("trim_out", asp.get("trim_out_seconds")),
                        effective_duration=float(asp.get("effective_duration", asp.get("duration_seconds", 4.0)) or 4.0),
                        still_duration=float(asp.get("still_duration", 4.0) or 4.0),
                        transition_to_next=asp.get("transition_to_next", asp.get("transition_type", "CUT")),
                        is_locked=bool(asp.get("is_locked", False)),
                        version=int(asp.get("version", 1) or 1),
                        created_at=parse_datetime(asp.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(asp.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for chk in asm.get("checkpoints", []):
                    db.add(TimelineCheckpoint(
                        id=remap.get_or_create(parse_uuid(chk["id"]), "TIMELINE_CHECKPOINT"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(chk["timeline_id"]), "TIMELINE"),
                        checkpoint_number=int(chk.get("checkpoint_number", 1) or 1),
                        label=chk.get("label", "checkpoint"),
                        snapshot_data=chk.get("snapshot_data", chk.get("checkpoint_data", {})),
                        actor=chk.get("actor", "system"),
                        created_at=parse_datetime(chk.get("created_at")) or datetime.now(timezone.utc),
                    ))
'''
replace_once("backend/app/services/archive/import_service.py", OLD_ASSEMBLY_IMPORT, NEW_ASSEMBLY_IMPORT)

OLD_QC_IMPORT = '''                for qf in qcd.get("qc_findings", []):
                    db.add(QCFinding(
                        id=remap.get_or_create(parse_uuid(qf["id"]), "QC_FINDING"),
                        qc_run_id=remap.get_or_create(parse_uuid(qf["qc_run_id"]), "QC_RUN"),
                        rule_code=qf.get("rule_code", ""),
                        severity=qf.get("severity", "WARNING"),
                        message=qf.get("message", ""),
                        entity_type=qf.get("entity_type"),
                        entity_id=remap.remap_polymorphic(qf.get("entity_type", ""), parse_uuid(qf.get("entity_id"))),
                        created_at=parse_datetime(qf.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for wd in qcd.get("warning_decisions", []):
                    db.add(WarningDecision(
                        id=remap.get_or_create(parse_uuid(wd["id"]), "WARNING_DECISION"),
                        finding_id=remap.get_or_create(parse_uuid(wd["finding_id"]), "QC_FINDING"),
                        decision=wd.get("decision", "ACCEPTED"),
                        reason=wd.get("reason"),
                        decided_by=wd.get("decided_by", "system"),
                        created_at=parse_datetime(wd.get("created_at")) or datetime.now(timezone.utc),
                    ))
'''
NEW_QC_IMPORT = '''                for qf in qcd.get("qc_findings", []):
                    target_type = qf.get("target_type") or qf.get("entity_type")
                    target_raw = qf.get("target_id") or qf.get("entity_id")
                    db.add(QCFinding(
                        id=remap.get_or_create(parse_uuid(qf["id"]), "QC_FINDING"),
                        project_id=new_project_id,
                        qc_run_id=remap.get_or_create(parse_uuid(qf["qc_run_id"]), "QC_RUN"),
                        timeline_id=remap.get_or_create(parse_uuid(qf.get("timeline_id")), "TIMELINE"),
                        rule_code=qf.get("rule_code", ""),
                        severity=qf.get("severity", "WARNING"),
                        message=qf.get("message", ""),
                        why_it_matters=qf.get("why_it_matters"),
                        recommended_fix=qf.get("recommended_fix"),
                        target_type=target_type,
                        target_id=remap.remap_polymorphic(target_type or "", parse_uuid(target_raw)),
                        target_label=qf.get("target_label"),
                        action_type=qf.get("action_type"),
                        created_at=parse_datetime(qf.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for wd in qcd.get("warning_decisions", []):
                    db.add(WarningDecision(
                        id=remap.get_or_create(parse_uuid(wd["id"]), "WARNING_DECISION"),
                        project_id=new_project_id,
                        qc_run_id=remap.get_or_create(parse_uuid(wd.get("qc_run_id")), "QC_RUN"),
                        finding_id=remap.get_or_create(parse_uuid(wd["finding_id"]), "QC_FINDING"),
                        timeline_id=remap.get_or_create(parse_uuid(wd.get("timeline_id")), "TIMELINE"),
                        decision=wd.get("decision", "ACCEPTED_WITH_REASON"),
                        reason=wd.get("reason"),
                        actor=wd.get("actor", wd.get("decided_by", "USER")),
                        decided_at=parse_datetime(wd.get("decided_at") or wd.get("created_at")) or datetime.now(timezone.utc),
                        decision_sequence=int(wd.get("decision_sequence", 1) or 1),
                    ))
'''
replace_once("backend/app/services/archive/import_service.py", OLD_QC_IMPORT, NEW_QC_IMPORT)

# ---------------------------------------------------------------------------
# Turn WP020-A evidence assertions into closure assertions for the corrected
# system while preserving the zero-billing HTTP denial guard.
# ---------------------------------------------------------------------------
replace_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    """from unittest.mock import patch\n""",
    """from unittest.mock import AsyncMock, patch\n""",
)
replace_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    """from app.services.archive.export_service import ProjectExportService\n""",
    """from app.services.archive.export_service import ProjectExportService\nfrom app.services.archive.import_service import ProjectImportService, ProjectCollisionError\n""",
)
replace_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    """from app.services.audio_production import AudioProductionService\n""",
    """from app.services.audio_production import AudioProductionService\nfrom app.services.budget import BudgetService\n""",
)
replace_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    """from app.services.subtitle_control import SubtitleService\n""",
    """from app.services.subtitle_control import SubtitleService\nfrom app.services.video_materialization import VideoMaterializationService\n""",
)

NEW_STORY_TEST = r'''def test_e2e_01_story_video_materialization_and_assembly_lineage_close(db_session, mock_storage):
    """Deep STORY path closes S1-A01/A03 without external provider/network use."""
    project, story, jobs = _run_story_to_video_jobs(db_session)

    async def fake_download(url, target_file_path):
        payload = ("WP020A_VIDEO:" + url).encode("utf-8")
        with open(target_file_path, "wb") as output:
            output.write(payload)
        return "video/mp4", len(payload), hashlib.sha256(payload).hexdigest()

    with (
        patch.object(ProviderFactory, "get_provider", return_value=CompletedFakeVideoProvider()),
        patch("app.services.video_materialization.get_storage_provider", return_value=mock_storage),
        patch.object(
            VideoMaterializationService,
            "_download_video_to_file",
            new=AsyncMock(side_effect=fake_download),
        ),
    ):
        for job in jobs:
            claimed = JobDispatchService.claim_next_job(
                db_session,
                worker_id="wp020a-video-worker",
                job_id=job.id,
            )
            assert claimed is not None
            completed = asyncio.run(
                JobDispatchService.process_job(
                    db_session,
                    job.id,
                    claim_token=claimed.claim_token,
                )
            )
            assert completed.status == "COMPLETED"
            assert completed.output_asset_id is not None
            asset = db_session.get(Asset, completed.output_asset_id)
            assert asset is not None
            assert asset.asset_type == "VIDEO"
            assert mock_storage.object_exists(asset.storage_bucket, asset.storage_key)

    state = ProductionOrchestrator.evaluate_state(db_session, project.id)
    assert state.current_stage == "VIDEO_IN_PROGRESS"
    assert state.recommended_action.action == "TRANSITION_TO_FINAL_REVIEW"
    assert ProductionOrchestrator.execute_action(
        db_session, project.id, "TRANSITION_TO_FINAL_REVIEW"
    ).to_stage == "FINAL_REVIEW"

    story_scenes = db_session.query(Scene).filter(Scene.story_id == story.id).all()
    assert story_scenes
    shots = (
        db_session.query(Shot)
        .join(Scene, Shot.scene_id == Scene.id)
        .filter(Scene.story_id == story.id)
        .all()
    )
    assert shots
    assert all(shot.source_asset_id is not None for shot in shots)

    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert len(timeline.shot_placements) == len(shots)
    assert all(p.source_type == "VIDEO" for p in timeline.shot_placements)
    assert all(p.visual_asset_id is not None for p in timeline.shot_placements)
'''
replace_regex_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    r"def test_e2e_01_story_completion_exposes_video_and_assembly_lineage_gaps\(db_session\):.*?\n\ndef _seed_materialized_video_project",
    NEW_STORY_TEST + "\n\ndef _seed_materialized_video_project",
)

NEW_DOWNSTREAM_TEST = r'''def test_e2e_10_to_14_downstream_archive_roundtrip_closes_audio_history_gap(db_session, mock_storage):
    """Audio -> render -> multi-output -> FULL_SELF_CONTAINED CLONE is integrated and fenced."""
    project, source_asset = _seed_materialized_video_project(db_session, mock_storage)

    audio_plan = AudioProductionService.generate_audio_plan(db_session, project.id)
    assert audio_plan.status == "DRAFT"
    AudioProductionService.approve_audio_plan(db_session, project.id)
    audio_result = AudioProductionService.execute_audio_batch(
        db=db_session,
        project_id=project.id,
        action="CONTINUE_INCOMPLETE_AUDIO",
        cost_authorized=True,
        actor="USER",
        provider_name="mock_audio",
    )
    assert audio_result["failed"] == 0
    assert audio_result["succeeded"] >= 1
    assert AudioProductionService.compute_auto_mix(db_session, project.id)["total_tracks"] >= 1

    project.status = "AUDIO_MIX_READY"
    db_session.commit()
    ProductionOrchestrator.approve_stage(db_session, project.id, stage="AUDIO_MIX_READY")
    ProductionOrchestrator.execute_action(db_session, project.id, "PROCEED_TO_ASSEMBLY")
    timeline = AssemblyService.auto_assemble_timeline(db_session, str(project.id))
    assert len(timeline.shot_placements) == 1
    assert timeline.shot_placements[0].source_type == "VIDEO"
    assert timeline.shot_placements[0].visual_asset_id == source_asset.id

    subtitle = SubtitleService.generate(db_session, project.id, timeline_id=str(timeline.id), language="th")
    assert subtitle["segments"]
    reviewed = SubtitleService.review(
        db_session, project.id, enabled=True, render_mode="BURN_IN", timeline_id=str(timeline.id)
    )
    assert reviewed["is_reviewed"] is True
    srt, srt_meta = SubtitleService.export_srt(db_session, project.id, str(timeline.id))
    assert "การทดสอบระบบแบบไม่เสียค่าใช้จ่าย" in srt
    assert srt_meta["sha256"] == hashlib.sha256(srt.encode("utf-8")).hexdigest()

    qc_run = QCService.run_qc(db_session, project.id)
    for finding in list(qc_run.findings):
        if finding.severity == "WARNING":
            QCService.record_warning_decision(
                db_session,
                project.id,
                finding.id,
                decision="ACCEPTED_WITH_REASON",
                reason="WP020-A deterministic evidence fixture",
                actor="WP020-A",
            )
    db_session.refresh(qc_run)
    assert qc_run.blocker_count == 0
    approval = ProductionOrchestrator.approve_final_production(
        db_session,
        project.id,
        timeline_id=timeline.id,
        qc_run_id=qc_run.id,
        notes="WP020-A zero-billing approval evidence",
        actor="WP020-A",
    )
    assert approval.status == "APPROVED"

    master = RenderJobService.submit_render_job(db_session, project.id)
    worker = CloudRenderWorker(
        worker_id="wp020a-render-worker",
        storage_provider=mock_storage,
        render_executor=MockRenderExecutor(),
        subtitle_burnin=CopySubtitleBurnIn(),
    )
    assert worker.process_one_job(db_session) is True
    db_session.refresh(master)
    assert master.status == RenderJobStatus.COMPLETED.value
    assert master.output_asset_id is not None

    batch = RenderJobService.submit_export_batch(
        db_session,
        project.id,
        preset_ids=["YT_STANDARD_1080P", "TIKTOK_REELS_9X16", "INSTAGRAM_SQUARE"],
    )
    for _ in range(3):
        assert worker.process_one_job(db_session) is True
    variants = db_session.query(RenderJob).filter(RenderJob.batch_id == batch.id).all()
    assert len(variants) == 3
    assert all(job.status == RenderJobStatus.COMPLETED.value for job in variants)

    exporter = ProjectExportService(storage_provider=mock_storage)
    archive_path, manifest = exporter.export_project(db=db_session, project_id=project.id)
    try:
        assert manifest["package_type"] == "FULL_SELF_CONTAINED"
        importer = ProjectImportService(storage_provider=mock_storage)
        validation = importer.validate_project_archive(archive_path, db_session)
        assert validation["valid"] is True
        clone = importer.execute_import(
            db=db_session,
            archive_path=archive_path,
            import_mode="CLONE",
            override_title="WP020-A Corrected Clone",
        )
        assert clone.id != project.id
        assert clone.source_project_id == project.id
        assert BudgetService.get_project_committed_cost(db_session, clone.id) == 0.0

        imported_jobs = db_session.query(RenderJob).filter(RenderJob.project_id == clone.id).all()
        assert imported_jobs
        assert all(job.imported_historical is True for job in imported_jobs)
        assert all(job.execution_disabled is True for job in imported_jobs)

        clone_timeline = AssemblyService.get_active_timeline(db_session, str(clone.id))
        assert clone_timeline is not None
        clone_subtitle = SubtitleService.get_active(
            db_session, clone.id, timeline_id=str(clone_timeline.id)
        )
        assert clone_subtitle is not None
        assert clone_subtitle["is_stale"] is False

        with pytest.raises(ProjectCollisionError):
            importer.execute_import(
                db=db_session,
                archive_path=archive_path,
                import_mode="RESTORE",
            )
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)
'''
replace_regex_once(
    "backend/tests/test_wp020a_zero_billing_e2e.py",
    r"def test_e2e_10_to_13_downstream_passes_until_audio_history_archive_gap\(db_session, mock_storage\):.*?\n\ndef test_e2e_02_to_05_mode_routing_and_project_isolation",
    NEW_DOWNSTREAM_TEST + "\n\ndef test_e2e_02_to_05_mode_routing_and_project_isolation",
)

FOCUSED_TEST = r'''import asyncio
import hashlib
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.asset import Asset
from app.models.generation_job import GenerationJob
from app.models.project import Project
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.usage_ledger import UsageLedger
from app.providers.base import ProviderJobResult
from app.providers.factory import ProviderFactory
from app.services.job_dispatch import JobDispatchService
from app.services.video_materialization import VideoMaterializationError, VideoMaterializationService


class CompletedProvider:
    @property
    def provider_id(self):
        return "vidu"

    def validate_config(self, config):
        return True

    async def submit_generation_job(self, params):
        return ProviderJobResult(
            provider_job_id=f"materialize-{params.shot_id}",
            status="COMPLETED",
            video_url=f"https://video.example.invalid/{params.shot_id}.mp4",
            cost_usd=0.123,
        )

    async def check_job_status(self, provider_job_id):
        return ProviderJobResult(
            provider_job_id=provider_job_id,
            status="COMPLETED",
            video_url=f"https://video.example.invalid/{provider_job_id}.mp4",
            cost_usd=0.123,
        )

    async def cancel_job(self, provider_job_id):
        return True


def seed(db):
    project = Project(
        id=uuid.uuid4(),
        title="Video materialization",
        video_mode="STORY",
        status="SHOT_PLAN_APPROVED",
        budget_limit=10.0,
    )
    db.add(project)
    db.flush()
    scene = Scene(id=uuid.uuid4(), project_id=project.id, scene_number=1)
    db.add(scene)
    db.flush()
    shot = Shot(
        id=uuid.uuid4(),
        scene_id=scene.id,
        shot_number=1,
        shot_type="AI_GENERATED",
        visual_prompt="safe prompt",
        duration_seconds=4.0,
    )
    db.add(shot)
    db.commit()
    return project, shot


async def fake_download(url, target_file_path):
    payload = b"ORBIT_VIDEO_MATERIALIZATION_TEST"
    with open(target_file_path, "wb") as output:
        output.write(payload)
    return "video/mp4", len(payload), hashlib.sha256(payload).hexdigest()


def test_completed_video_materializes_asset_and_is_idempotent(db_session, mock_storage):
    project, shot = seed(db_session)
    job = GenerationJob(
        id=uuid.uuid4(),
        shot_id=shot.id,
        job_type="VIDEO",
        provider_name="vidu",
        provider_job_id="already-complete",
        status="PROCESSING",
    )
    db_session.add(job)
    db_session.commit()
    result = ProviderJobResult(
        provider_job_id="already-complete",
        status="COMPLETED",
        video_url="https://video.example.invalid/out.mp4",
        cost_usd=0.123,
    )

    first = asyncio.run(VideoMaterializationService.materialize_completed_result(
        db_session, job.id, result, storage_provider=mock_storage, downloader=fake_download
    ))
    second = asyncio.run(VideoMaterializationService.materialize_completed_result(
        db_session, job.id, result, storage_provider=mock_storage, downloader=fake_download
    ))
    assert first.id == second.id
    db_session.refresh(job)
    db_session.refresh(shot)
    assert job.output_asset_id == first.id
    assert shot.source_asset_id == first.id
    assert db_session.query(Asset).filter(Asset.project_id == project.id, Asset.asset_type == "VIDEO").count() == 1
    assert mock_storage.object_exists(first.storage_bucket, first.storage_key)


def test_completed_provider_with_materialization_failure_requires_reconciliation(db_session, mock_storage):
    project, shot = seed(db_session)
    job = JobDispatchService.create_and_dispatch_job(
        db_session,
        shot.id,
        provider_name="vidu",
        idempotency_key="wp020-materialization-failure",
    )
    claimed = JobDispatchService.claim_next_job(db_session, worker_id="materialization-test", job_id=job.id)
    assert claimed is not None

    async def broken_download(url, target_file_path):
        raise VideoMaterializationError("synthetic local persistence failure")

    with (
        patch.object(ProviderFactory, "get_provider", return_value=CompletedProvider()),
        patch("app.services.video_materialization.get_storage_provider", return_value=mock_storage),
        patch.object(
            VideoMaterializationService,
            "_download_video_to_file",
            new=AsyncMock(side_effect=broken_download),
        ),
    ):
        settled = asyncio.run(JobDispatchService.process_job(
            db_session, job.id, claim_token=claimed.claim_token
        ))

    assert settled.status == "RECONCILIATION_REQUIRED"
    assert settled.output_asset_id is None
    db_session.refresh(shot)
    assert shot.source_asset_id is None
    ledger = db_session.query(UsageLedger).filter(UsageLedger.job_id == job.id).one()
    assert ledger.cost_status == "CONFIRMED"
    assert ledger.actual_cost == pytest.approx(0.123)


def test_materializer_rejects_private_or_non_https_urls():
    with pytest.raises(VideoMaterializationError):
        asyncio.run(VideoMaterializationService._validate_public_https_url("http://example.com/video.mp4"))
    with pytest.raises(VideoMaterializationError):
        asyncio.run(VideoMaterializationService._validate_public_https_url("https://127.0.0.1/video.mp4"))
'''
write("backend/tests/test_video_materialization.py", FOCUSED_TEST)

print("WP020-A-R1 bounded corrective patch applied")
