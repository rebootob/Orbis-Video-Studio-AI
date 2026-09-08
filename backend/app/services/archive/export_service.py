"""Project export service for generating .orbis archives.

Serializes the full bounded project graph (entities, history, audits, ledgers),
fetches required media binaries from object storage, validates checksums,
strips sensitive secrets, and packages into a tamper-evident .orbis container.
"""
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.story import Story
from app.models.story_version import StoryVersion
from app.models.scene import Scene
from app.models.shot import Shot
from app.models.asset import Asset
from app.models.document_extraction import DocumentExtraction
from app.models.reference_library import (
    ProjectReference,
    CharacterBible,
    LocationBible,
    StyleBible,
    BrandBible,
)
from app.models.asset_lock import AssetLock
from app.models.audio_plan import AudioPlan
from app.models.audio_history import AudioPlanVersion, AudioClipHistory
from app.models.audio_clip import AudioClip
from app.models.assembly import (
    AssemblyTimeline,
    AssemblyScene,
    AssemblyShotPlacement,
    TimelineCheckpoint,
    TimelineAudit,
)
from app.models.qc import (
    QCRun,
    QCFinding,
    WarningDecision,
    ApprovalRecord,
)
from app.models.render_batch import RenderBatch
from app.models.render_job import RenderJob
from app.models.generation_job import GenerationJob
from app.models.batch_run import BatchRun, BatchRunItem
from app.models.generation_audit import GenerationAuditLog
from app.models.orchestration_audit import OrchestrationAudit
from app.models.usage_ledger import UsageLedger, LedgerAdjustment
from app.services.storage import get_storage_provider, ObjectStorageProvider
from app.services.archive.constants import (
    ARCHIVE_FORMAT_VERSION,
    SCHEMA_VERSION,
    ALLOWED_ASSET_EXTENSIONS,
)
from app.services.archive.checksums import ArchiveChecksumService

SENSITIVE_KEY_PATTERNS = re.compile(
    r"(api_?key|secret|token|password|auth|bearer|credentials|private_key)",
    re.IGNORECASE,
)


class ArchiveExportError(Exception):
    """Raised when project archive export fails."""
    pass


def model_to_dict(model_inst: Any, exclude_keys: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Converts a SQLAlchemy model instance into a clean JSON-serializable dictionary."""
    if not model_inst:
        return {}
    exclude = exclude_keys or set()
    data = {}
    for col in model_inst.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(model_inst, col.name)
        if isinstance(val, uuid.UUID):
            data[col.name] = str(val)
        elif isinstance(val, datetime):
            data[col.name] = val.isoformat()
        else:
            data[col.name] = sanitize_secrets(val)
    return data


def sanitize_secrets(val: Any) -> Any:
    """Recursively removes sensitive keys and presigned query authentication tokens."""
    if isinstance(val, dict):
        cleaned = {}
        for k, v in val.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                continue
            cleaned[k] = sanitize_secrets(v)
        return cleaned
    elif isinstance(val, list):
        return [sanitize_secrets(item) for item in val]
    elif isinstance(val, str):
        if ("X-Amz-Signature=" in val or "Signature=" in val) and ("http://" in val or "https://" in val):
            return val.split("?")[0]
        return val
    return val


class ProjectExportService:
    """Orchestrates full bounded project graph export and .orbis archive generation."""

    def __init__(self, storage_provider: Optional[ObjectStorageProvider] = None):
        self.storage = storage_provider or get_storage_provider()

    def export_project(
        self,
        db: Session,
        project_id: uuid.UUID,
        package_type: str = "FULL_SELF_CONTAINED",
        include_history: bool = True,
        include_renders: bool = True,
        output_path: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Exports the full project graph and returns (archive_path, manifest_dict)."""
        archive_path = self.export_project_archive(
            db=db,
            project_id=project_id,
            package_type=package_type,
            include_history=include_history,
            include_renders=include_renders,
            output_path=output_path,
        )
        with zipfile.ZipFile(archive_path, "r") as zf:
            manifest_bytes = zf.read("manifest.json")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        return archive_path, manifest

    def export_project_archive(
        self,
        db: Session,
        project_id: uuid.UUID,
        package_type: str = "FULL_SELF_CONTAINED",
        include_history: bool = True,
        include_renders: bool = True,
        output_path: Optional[str] = None,
    ) -> str:
        """Exports the full project graph into a validated .orbis archive."""
        project = db.get(Project, project_id)
        if not project:
            raise ArchiveExportError(f"Project '{project_id}' not found")

        if package_type != "FULL_SELF_CONTAINED":
            raise ArchiveExportError(
                f"Package type '{package_type}' is not supported in Core V1. "
                "Only 'FULL_SELF_CONTAINED' archives are supported."
            )

        if not include_history:
            raise ArchiveExportError(
                "include_history=False is not supported in Core V1 FULL_SELF_CONTAINED archives. "
                "Full historical lineage must be included."
            )

        if not include_renders:
            raise ArchiveExportError(
                "include_renders=False is not supported for FULL_SELF_CONTAINED archives in V1. "
                "All project assets including render outputs must be included to ensure archive self-consistency."
            )

        temp_dir = tempfile.mkdtemp(prefix="orbis_export_")
        try:
            return self._build_archive(
                db=db,
                project=project,
                temp_dir=temp_dir,
                package_type=package_type,
                include_history=include_history,
                include_renders=include_renders,
                output_path=output_path,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _build_archive(
        self,
        db: Session,
        project: Project,
        temp_dir: str,
        package_type: str,
        include_history: bool,
        include_renders: bool,
        output_path: Optional[str],
    ) -> str:
        p_id = project.id

        # Directory structure
        entities_dir = os.path.join(temp_dir, "entities")
        assets_dir = os.path.join(temp_dir, "assets")
        assets_data_dir = os.path.join(assets_dir, "data")
        history_dir = os.path.join(temp_dir, "history")

        os.makedirs(entities_dir, exist_ok=True)
        os.makedirs(assets_data_dir, exist_ok=True)
        os.makedirs(history_dir, exist_ok=True)

        file_hashes: Dict[str, str] = {}
        file_sizes: Dict[str, int] = {}

        # 1. Project metadata
        project_dict = model_to_dict(project)
        project_bytes = ArchiveChecksumService.canonical_json_dumps(project_dict)
        project_path = os.path.join(temp_dir, "project.json")
        with open(project_path, "wb") as f:
            f.write(project_bytes)
        file_hashes["project.json"] = ArchiveChecksumService.compute_sha256_bytes(project_bytes)
        file_sizes["project.json"] = len(project_bytes)

        # 2. Query entities
        story = db.query(Story).filter(Story.project_id == p_id).first()
        story_versions = (
            db.query(StoryVersion).filter(StoryVersion.project_id == p_id).order_by(StoryVersion.version_number).all()
        )
        scenes = (
            db.query(Scene)
            .filter((Scene.project_id == p_id) | (Scene.story.has(project_id=p_id)))
            .order_by(Scene.scene_number, Scene.id)
            .all()
        )
        scene_ids = [s.id for s in scenes]

        shots = db.query(Shot).filter(Shot.scene_id.in_(scene_ids)).order_by(Shot.shot_number).all() if scene_ids else []
        assets = db.query(Asset).filter(Asset.project_id == p_id).all()
        asset_ids = [a.id for a in assets]

        doc_extractions = (
            db.query(DocumentExtraction).filter(DocumentExtraction.asset_id.in_(asset_ids)).all() if asset_ids else []
        )
        project_refs = db.query(ProjectReference).filter(ProjectReference.project_id == p_id).all()
        char_bibles = db.query(CharacterBible).filter(CharacterBible.project_id == p_id).all()
        loc_bibles = db.query(LocationBible).filter(LocationBible.project_id == p_id).all()
        style_bibles = db.query(StyleBible).filter(StyleBible.project_id == p_id).all()
        brand_bibles = db.query(BrandBible).filter(BrandBible.project_id == p_id).all()
        locks = db.query(AssetLock).filter(AssetLock.project_id == p_id).all()

        audio_plans = db.query(AudioPlan).filter(AudioPlan.project_id == p_id).all()
        plan_ids = [p.id for p in audio_plans]
        audio_plan_versions = (
            db.query(AudioPlanVersion).filter(AudioPlanVersion.audio_plan_id.in_(plan_ids)).all() if plan_ids else []
        )
        audio_clips = db.query(AudioClip).filter(AudioClip.project_id == p_id).all()
        clip_ids = [c.id for c in audio_clips]
        audio_clip_histories = (
            db.query(AudioClipHistory).filter(AudioClipHistory.clip_id.in_(clip_ids)).all() if clip_ids else []
        )

        timelines = db.query(AssemblyTimeline).filter(AssemblyTimeline.project_id == p_id).order_by(AssemblyTimeline.version).all()
        timeline_ids = [t.id for t in timelines]
        assembly_scenes = (
            db.query(AssemblyScene).filter(AssemblyScene.timeline_id.in_(timeline_ids)).all() if timeline_ids else []
        )
        assembly_shot_placements = (
            db.query(AssemblyShotPlacement).filter(AssemblyShotPlacement.timeline_id.in_(timeline_ids)).all()
            if timeline_ids else []
        )
        checkpoints = (
            db.query(TimelineCheckpoint).filter(TimelineCheckpoint.timeline_id.in_(timeline_ids)).all()
            if timeline_ids else []
        )
        timeline_audits = (
            db.query(TimelineAudit).filter(TimelineAudit.timeline_id.in_(timeline_ids)).all()
            if timeline_ids else []
        )

        qc_runs = db.query(QCRun).filter(QCRun.project_id == p_id).all()
        qc_run_ids = [q.id for q in qc_runs]
        qc_findings = db.query(QCFinding).filter(QCFinding.qc_run_id.in_(qc_run_ids)).all() if qc_run_ids else []
        finding_ids = [f.id for f in qc_findings]
        warning_decisions = (
            db.query(WarningDecision).filter(WarningDecision.finding_id.in_(finding_ids)).all() if finding_ids else []
        )
        approvals = db.query(ApprovalRecord).filter(ApprovalRecord.project_id == p_id).all()

        render_batches = db.query(RenderBatch).filter(RenderBatch.project_id == p_id).all()
        render_jobs = db.query(RenderJob).filter(RenderJob.project_id == p_id).all()
        shot_ids = [s.id for s in shots]
        generation_jobs = db.query(GenerationJob).filter(GenerationJob.shot_id.in_(shot_ids)).all() if shot_ids else []
        batch_runs = db.query(BatchRun).filter(BatchRun.project_id == p_id).all()
        batch_run_ids = [b.id for b in batch_runs]
        batch_run_items = db.query(BatchRunItem).filter(BatchRunItem.batch_run_id.in_(batch_run_ids)).all() if batch_run_ids else []

        gen_audits = db.query(GenerationAuditLog).filter(GenerationAuditLog.project_id == p_id).all()
        orch_audits = db.query(OrchestrationAudit).filter(OrchestrationAudit.project_id == p_id).all()
        ledgers = db.query(UsageLedger).filter(UsageLedger.project_id == p_id).all()
        ledger_ids = [l.id for l in ledgers]
        adjustments = db.query(LedgerAdjustment).filter(LedgerAdjustment.ledger_id.in_(ledger_ids)).all() if ledger_ids else []

        # 3. Write entity JSON datasets
        entity_datasets = {
            "entities/story.json": {
                "story": model_to_dict(story) if story else None,
                "story_versions": [model_to_dict(v) for v in story_versions],
            },
            "entities/scenes.json": [model_to_dict(s) for s in scenes],
            "entities/shots.json": [model_to_dict(s) for s in shots],
            "entities/assets.json": [model_to_dict(a) for a in assets],
            "entities/document_extractions.json": [model_to_dict(d) for d in doc_extractions],
            "entities/reference_library.json": {
                "project_references": [model_to_dict(r) for r in project_refs],
                "character_bibles": [model_to_dict(b) for b in char_bibles],
                "location_bibles": [model_to_dict(b) for b in loc_bibles],
                "style_bibles": [model_to_dict(b) for b in style_bibles],
                "brand_bibles": [model_to_dict(b) for b in brand_bibles],
            },
            "entities/asset_locks.json": [model_to_dict(l) for l in locks],
            "entities/audio.json": {
                "audio_plans": [model_to_dict(p) for p in audio_plans],
                "audio_plan_versions": [model_to_dict(v) for v in audio_plan_versions],
                "audio_clips": [model_to_dict(c) for c in audio_clips],
                "audio_clip_histories": [model_to_dict(h) for h in audio_clip_histories],
            },
            "entities/assembly.json": {
                "timelines": [model_to_dict(t) for t in timelines],
                "assembly_scenes": [model_to_dict(s) for s in assembly_scenes],
                "assembly_shot_placements": [model_to_dict(p) for p in assembly_shot_placements],
                "checkpoints": [model_to_dict(c) for c in checkpoints],
            },
            "entities/qc.json": {
                "qc_runs": [model_to_dict(q) for q in qc_runs],
                "qc_findings": [model_to_dict(f) for f in qc_findings],
                "warning_decisions": [model_to_dict(w) for w in warning_decisions],
                "approvals": [model_to_dict(a) for a in approvals],
            },
            "entities/render_jobs.json": {
                "render_batches": [model_to_dict(b) for b in render_batches],
                "render_jobs": [model_to_dict(r) for r in render_jobs],
            },
            "entities/generation_jobs.json": {
                "generation_jobs": [model_to_dict(g) for g in generation_jobs],
                "batch_runs": [model_to_dict(b) for b in batch_runs],
                "batch_run_items": [model_to_dict(i) for i in batch_run_items],
            },
            "history/usage_ledger.json": {
                "entries": [model_to_dict(l) for l in ledgers],
                "adjustments": [model_to_dict(a) for a in adjustments],
            },
            "history/orchestration_audit.json": [model_to_dict(o) for o in orch_audits],
            "history/generation_audit.json": [model_to_dict(g) for g in gen_audits],
            "history/timeline_audits.json": [model_to_dict(t) for t in timeline_audits],
        }

        for rel_path, data in entity_datasets.items():
            content = ArchiveChecksumService.canonical_json_dumps(data)
            full_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(content)
            file_hashes[rel_path] = ArchiveChecksumService.compute_sha256_bytes(content)
            file_sizes[rel_path] = len(content)

        # 4. Stream & Package Media Assets
        asset_manifest_entries: Dict[str, Any] = {}
        embedded_asset_count = 0
        total_asset_bytes = 0

        for asset in assets:
            _, ext = os.path.splitext(asset.original_filename)
            ext = ext.lower() if ext else ".bin"
            if ext not in ALLOWED_ASSET_EXTENSIONS:
                ext = ".bin"

            # Check if asset exists in storage
            if not self.storage.object_exists(asset.storage_bucket, asset.storage_key):
                raise ArchiveExportError(
                    f"Required asset file missing from storage: asset {asset.id} "
                    f"('{asset.name}'), bucket '{asset.storage_bucket}', key '{asset.storage_key}'"
                )

            # Content-addressed path under assets/data/{checksum}.{ext}
            # Download file
            staging_asset_file = os.path.join(assets_data_dir, f"tmp_{asset.id}{ext}")
            self.storage.download_file_object(asset.storage_bucket, asset.storage_key, staging_asset_file)

            actual_sha = ArchiveChecksumService.compute_sha256_file(staging_asset_file)
            final_filename = f"{actual_sha}{ext}"
            final_data_path = os.path.join(assets_data_dir, final_filename)

            if os.path.exists(final_data_path):
                os.remove(staging_asset_file)
            else:
                os.rename(staging_asset_file, final_data_path)

            rel_asset_path = f"assets/data/{final_filename}"
            size_bytes = os.path.getsize(final_data_path)

            file_hashes[rel_asset_path] = actual_sha
            file_sizes[rel_asset_path] = size_bytes
            embedded_asset_count += 1
            total_asset_bytes += size_bytes

            asset_manifest_entries[str(asset.id)] = {
                "relative_path": rel_asset_path,
                "sha256": actual_sha,
                "size_bytes": size_bytes,
                "original_filename": asset.original_filename,
                "content_type": asset.content_type,
                "asset_type": asset.asset_type,
            }

        # Write assets/manifest.json
        assets_manifest_bytes = ArchiveChecksumService.canonical_json_dumps(asset_manifest_entries)
        assets_manifest_path = os.path.join(assets_dir, "manifest.json")
        with open(assets_manifest_path, "wb") as f:
            f.write(assets_manifest_bytes)
        file_hashes["assets/manifest.json"] = ArchiveChecksumService.compute_sha256_bytes(assets_manifest_bytes)
        file_sizes["assets/manifest.json"] = len(assets_manifest_bytes)

        # 5. Build Root manifest.json
        file_manifest = {
            rel_path: {
                "sha256": file_hashes[rel_path],
                "size_bytes": file_sizes[rel_path],
            }
            for rel_path in sorted(file_hashes.keys())
        }

        manifest_obj = {
            "$schema": "https://orbis.video/schemas/v1/archive-manifest.json",
            "archive_format_version": ARCHIVE_FORMAT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "generator": {
                "system": "Orbis Video Studio AI",
                "version": "1.0.0-core-v1",
                "exported_at": datetime.now(timezone.utc).isoformat(),
            },
            "project": {
                "original_project_id": str(project.id),
                "title": project.title,
                "video_mode": project.video_mode,
                "automation_mode": project.automation_mode,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            },
            "archive_options": {
                "package_type": package_type,
                "include_history": include_history,
                "include_renders": include_renders,
            },
            "entity_counts": {
                "scenes": len(scenes),
                "shots": len(shots),
                "assets": len(assets),
                "locks": len(locks),
                "audio_clips": len(audio_clips),
                "timelines": len(timelines),
                "qc_runs": len(qc_runs),
                "approvals": len(approvals),
                "render_jobs": len(render_jobs),
                "generation_jobs": len(generation_jobs),
                "usage_ledger_entries": len(ledgers),
            },
            "assets_summary": {
                "total_count": len(assets),
                "total_size_bytes": total_asset_bytes,
                "embedded_count": embedded_asset_count,
                "reference_only_count": len(assets) - embedded_asset_count,
            },
            "file_manifest": file_manifest,
        }

        manifest_bytes = ArchiveChecksumService.canonical_json_dumps(manifest_obj)
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "wb") as f:
            f.write(manifest_bytes)
        manifest_sha = ArchiveChecksumService.compute_sha256_bytes(manifest_bytes)

        # 6. Build checksums.sha256
        # Include all payload files + manifest.json; exclude checksums.sha256
        checksum_payload_map = dict(file_hashes)
        checksum_payload_map["manifest.json"] = manifest_sha
        checksums_bytes = ArchiveChecksumService.generate_checksums_content(checksum_payload_map)
        checksums_path = os.path.join(temp_dir, "checksums.sha256")
        with open(checksums_path, "wb") as f:
            f.write(checksums_bytes)

        # 7. Package ZIP Container
        final_zip_path = output_path or os.path.join(
            tempfile.gettempdir(), f"project_{project.id}_{int(datetime.now().timestamp())}.orbis"
        )
        os.makedirs(os.path.dirname(os.path.abspath(final_zip_path)), exist_ok=True)

        with zipfile.ZipFile(final_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest.json and checksums.sha256
            zf.write(manifest_path, arcname="manifest.json", compress_type=zipfile.ZIP_DEFLATED)
            zf.write(checksums_path, arcname="checksums.sha256", compress_type=zipfile.ZIP_DEFLATED)

            # Add all payload files
            for rel_path in sorted(file_hashes.keys()):
                src_file = os.path.join(temp_dir, rel_path)
                # Media assets under assets/data can be stored uncompressed for efficiency
                compress_mode = (
                    zipfile.ZIP_STORED if rel_path.startswith("assets/data/") else zipfile.ZIP_DEFLATED
                )
                zf.write(src_file, arcname=rel_path, compress_type=compress_mode)

        return final_zip_path
