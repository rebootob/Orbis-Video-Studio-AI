import os
import socket
import tempfile
import shutil
import logging
import hashlib
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.render import RenderExecutor, FFmpegRenderExecutor
from app.services.storage import get_storage_provider, ObjectStorageProvider
from app.services.render_job import RenderJobService
from app.models.render_job import RenderJob
from app.models.assembly import AssemblyTimeline, AssemblyShotPlacement
from app.models.asset import Asset
from app.models.audio_clip import AudioClip

logger = logging.getLogger(__name__)


class CloudRenderWorker:
    """
    Stateless worker component that claims, renders, uploads, and settles RenderJobs.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        storage_provider: Optional[ObjectStorageProvider] = None,
        render_executor: Optional[RenderExecutor] = None,
    ):
        self.worker_id = worker_id or f"worker-{socket.gethostname()}-{os.getpid()}"
        self.storage_provider = storage_provider or get_storage_provider()
        self.render_executor = render_executor or FFmpegRenderExecutor()

    def process_one_job(self, db: Session) -> bool:
        job = RenderJobService.claim_next_render_job(db, self.worker_id)
        if not job:
            return False

        logger.info(
            f"Worker {self.worker_id} claimed RenderJob {job.id} "
            f"(Project {job.project_id}, Timeline {job.timeline_id} v{job.timeline_version})"
        )

        scratch_dir = tempfile.mkdtemp(prefix=f"orbis_render_{job.id}_")
        output_file_path = os.path.join(scratch_dir, f"render_{job.id}.mp4")
        upload_succeeded = False

        try:
            # Load exact approved timeline revision from DB (FAIL CLOSED if exact version is missing)
            timeline = (
                db.query(AssemblyTimeline)
                .filter(
                    AssemblyTimeline.id == job.timeline_id,
                    AssemblyTimeline.version == job.timeline_version,
                )
                .first()
            )

            if not timeline:
                raise RuntimeError(
                    f"Exact AssemblyTimeline {job.timeline_id} version {job.timeline_version} not found in DB. Fail closed."
                )

            # Load shot placements and download visual assets
            placements = []
            total_duration = 0.0

            for placement in timeline.shot_placements:
                visual_asset = placement.visual_asset
                if not visual_asset and placement.shot:
                    visual_asset = placement.shot.keyframe_asset or placement.shot.source_asset

                if not visual_asset and placement.visual_asset_id:
                    visual_asset = db.get(Asset, placement.visual_asset_id)
                elif not visual_asset and placement.shot:
                    if placement.shot.keyframe_asset_id:
                        visual_asset = db.get(Asset, placement.shot.keyframe_asset_id)
                    elif placement.shot.source_asset_id:
                        visual_asset = db.get(Asset, placement.shot.source_asset_id)

                if not visual_asset:
                    raise RuntimeError(
                        f"Missing required visual source asset for placement {placement.id} "
                        f"(shot {placement.shot_id}). Fail closed."
                    )

                ext = os.path.splitext(visual_asset.original_filename or ".mp4")[1] or ".mp4"
                local_asset_path = os.path.join(scratch_dir, f"asset_{visual_asset.id}{ext}")

                # Streaming download to disk
                self.storage_provider.download_file_object(
                    bucket=visual_asset.storage_bucket,
                    key=visual_asset.storage_key,
                    file_path=local_asset_path,
                )

                if not os.path.exists(local_asset_path):
                    raise RuntimeError(
                        f"Downloaded asset {visual_asset.id} missing from scratch disk at {local_asset_path}"
                    )

                placement_duration = float(placement.effective_duration or 4.0)
                total_duration += placement_duration

                placements.append({
                    "id": str(placement.id),
                    "shot_id": str(placement.shot_id),
                    "local_asset_path": local_asset_path,
                    "file_path": local_asset_path,
                    "trim_in": float(placement.trim_in or 0.0),
                    "trim_out": float(placement.trim_out) if placement.trim_out is not None else None,
                    "effective_duration": placement_duration,
                    "still_duration": float(placement.still_duration or 4.0),
                    "transition_to_next": placement.transition_to_next,
                    "source_type": placement.source_type,
                })

            if total_duration <= 0.0:
                total_duration = 10.0

            # Resolve audio clips
            audio_clips_list = []
            db_audio_clips = db.query(AudioClip).filter(AudioClip.project_id == job.project_id).all()
            for ac in db_audio_clips:
                audio_asset = ac.asset or ac.video_asset
                if not audio_asset:
                    if ac.asset_id:
                        audio_asset = db.get(Asset, ac.asset_id)
                    elif ac.video_asset_id:
                        audio_asset = db.get(Asset, ac.video_asset_id)

                if audio_asset:
                    a_ext = os.path.splitext(audio_asset.original_filename or ".mp3")[1] or ".mp3"
                    local_audio_path = os.path.join(scratch_dir, f"audio_{ac.id}{a_ext}")
                    try:
                        self.storage_provider.download_file_object(
                            bucket=audio_asset.storage_bucket,
                            key=audio_asset.storage_key,
                            file_path=local_audio_path,
                        )
                        if os.path.exists(local_audio_path):
                            audio_clips_list.append({
                                "id": str(ac.id),
                                "local_asset_path": local_audio_path,
                                "file_path": local_audio_path,
                                "start_time": float(ac.start_time or 0.0),
                                "duration_seconds": (
                                    float(ac.duration_seconds) if ac.duration_seconds is not None else None
                                ),
                                "volume": float(ac.volume or 1.0),
                                "mute": bool(ac.mute),
                                "fade_in": float(ac.fade_in or 0.0),
                                "fade_out": float(ac.fade_out or 0.0),
                            })
                    except Exception as e:
                        logger.warning(f"Could not download audio clip asset {audio_asset.id}: {e}")

            timeline_spec = {
                "project_id": str(job.project_id),
                "timeline_id": str(job.timeline_id),
                "timeline_version": job.timeline_version,
                "render_profile": job.render_profile,
                "render_metadata": job.render_metadata or {},
                "preset_snapshot": (job.render_metadata or {}).get("preset_snapshot"),
                "total_duration": total_duration,
                "placements": placements,
                "audio_clips": audio_clips_list,
            }

            def progress_cb(pct: float):
                RenderJobService.update_progress(db, job.id, job.claim_token, pct)

            # Execute rendering
            render_meta = self.render_executor.render_timeline(
                timeline_spec=timeline_spec,
                scratch_dir=scratch_dir,
                output_file_path=output_file_path,
                progress_callback=progress_cb,
            )

            if not os.path.exists(output_file_path):
                raise RuntimeError(f"Render output file not found at {output_file_path}")

            # Compute real file SHA-256 hash and size streaming without loading entire file into RAM
            sha256_hash = hashlib.sha256()
            file_size = os.path.getsize(output_file_path)
            with open(output_file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(chunk)
            checksum_sha256 = sha256_hash.hexdigest()

            is_export_variant = bool(job.render_variant_key and job.render_variant_key != "MASTER")
            preset_id = (job.render_metadata or {}).get("preset_id", "export") if is_export_variant else None

            if is_export_variant:
                storage_key = f"projects/{job.project_id}/exports/v{job.timeline_version}/{preset_id}_{job.id}.mp4"
            else:
                storage_key = f"projects/{job.project_id}/renders/render_{job.id}_v{job.timeline_version}.mp4"

            bucket = getattr(settings, "OBJECT_STORAGE_BUCKET", "orbis-assets")
            self.storage_provider.ensure_bucket_exists(bucket)

            # Stream upload file object to object storage
            self.storage_provider.upload_file_object(
                bucket=bucket,
                key=storage_key,
                file_path=output_file_path,
                content_type="video/mp4",
            )
            upload_succeeded = True

            # Create output Asset row
            if is_export_variant:
                asset = RenderJobService.create_render_output_asset(
                    db=db,
                    project_id=job.project_id,
                    storage_bucket=bucket,
                    storage_key=storage_key,
                    duration_seconds=render_meta.get("duration_seconds", total_duration),
                    file_size_bytes=file_size,
                    checksum_sha256=checksum_sha256,
                    name=f"export_{preset_id}_v{job.timeline_version}.mp4",
                    asset_type="EXPORT_VIDEO",
                    original_filename=f"{preset_id}.mp4",
                )
            else:
                asset = RenderJobService.create_render_output_asset(
                    db=db,
                    project_id=job.project_id,
                    storage_bucket=bucket,
                    storage_key=storage_key,
                    duration_seconds=render_meta.get("duration_seconds", total_duration),
                    file_size_bytes=file_size,
                    checksum_sha256=checksum_sha256,
                )

            # Complete render job and reconcile usage ledger cost
            actual_cost = round(file_size / (1024 * 1024) * 0.01 + 0.05, 4)
            RenderJobService.complete_render_job(
                db=db,
                render_job_id=job.id,
                claim_token=job.claim_token,
                output_asset_id=asset.id,
                actual_cost_usd=actual_cost,
                render_metadata={
                    **render_meta,
                    "storage_bucket": bucket,
                    "storage_key": storage_key,
                    "checksum_sha256": checksum_sha256,
                    "file_size_bytes": file_size,
                },
            )
            logger.info(f"Worker {self.worker_id} successfully completed RenderJob {job.id}")
            return True

        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed RenderJob {job.id}: {e}", exc_info=True)
            RenderJobService.fail_render_job(
                db=db,
                render_job_id=job.id,
                claim_token=job.claim_token,
                error_message=str(e),
                ambiguous=upload_succeeded,
            )
            return True

        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)
