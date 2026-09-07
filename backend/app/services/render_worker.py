import os
import socket
import tempfile
import shutil
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.render import RenderExecutor, FFmpegRenderExecutor
from app.services.storage import get_storage_provider, ObjectStorageProvider
from app.services.render_job import RenderJobService
from app.models.render_job import RenderJob

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

        logger.info(f"Worker {self.worker_id} claimed RenderJob {job.id} (Project {job.project_id}, Timeline {job.timeline_id} v{job.timeline_version})")

        scratch_dir = tempfile.mkdtemp(prefix=f"orbis_render_{job.id}_")
        output_file_path = os.path.join(scratch_dir, f"render_{job.id}.mp4")

        try:
            # Build timeline spec from job metadata and timeline
            timeline_spec = {
                "project_id": str(job.project_id),
                "timeline_id": str(job.timeline_id),
                "timeline_version": job.timeline_version,
                "render_profile": job.render_profile,
                "total_duration": 10.0,  # Default timeline duration
                "placements": [],
                "audio_clips": [],
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

            # Read and upload rendered MP4 file to object storage
            with open(output_file_path, "rb") as f:
                file_bytes = f.read()

            storage_key = f"projects/{job.project_id}/renders/render_{job.id}_v{job.timeline_version}.mp4"
            bucket = getattr(settings, "OBJECT_STORAGE_BUCKET", "orbis-assets")
            self.storage_provider.ensure_bucket_exists(bucket)
            self.storage_provider.put_object(
                bucket=bucket,
                key=storage_key,
                data=file_bytes,
                content_type="video/mp4",
            )

            # Create output Asset row
            asset = RenderJobService.create_render_output_asset(
                db=db,
                project_id=job.project_id,
                storage_key=storage_key,
                duration_seconds=render_meta.get("duration_seconds", 10.0),
                file_size_bytes=len(file_bytes),
            )

            # Complete render job and reconcile usage ledger cost
            actual_cost = round(len(file_bytes) / (1024 * 1024) * 0.01 + 0.05, 4)
            RenderJobService.complete_render_job(
                db=db,
                render_job_id=job.id,
                claim_token=job.claim_token,
                output_asset_id=asset.id,
                actual_cost_usd=actual_cost,
                render_metadata=render_meta,
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
                ambiguous=False,
            )
            return True

        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)
