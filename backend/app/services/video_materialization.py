"""Durable materialization of completed VideoProvider outputs.

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
