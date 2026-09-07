"""Project import service for validating and extracting .orbis archive packages.

Enforces:
1. Strict 4-phase validation pipeline
2. CLONE (default, fresh UUIDs, remapped FKs, lineage) vs RESTORE (original UUIDs, fail-closed on collision)
3. Atomic database transaction with storage upload compensation rollback
4. Bit-for-bit preservation of historical execution records tagged with imported_historical=True and execution_disabled=True
"""
import json
import logging
import os
import shutil
import tempfile
import uuid
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
from app.services.archive.constants import SUPPORTED_MAJOR_VERSIONS
from app.services.archive.security import ArchiveSecurityValidator, ArchiveSecurityError
from app.services.archive.checksums import ArchiveChecksumService, ChecksumVerificationError

logger = logging.getLogger(__name__)


class ArchiveImportError(Exception):
    """Base error for import failures."""
    pass


class ProjectCollisionError(ArchiveImportError):
    """Raised when RESTORE mode collides with an existing project in the database."""
    pass


class VersionIncompatibilityError(ArchiveImportError):
    """Raised when archive format version is unsupported."""
    pass


def parse_datetime(dt_val: Any) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    try:
        return datetime.fromisoformat(str(dt_val))
    except Exception:
        return None


def parse_uuid(u_val: Any) -> Optional[uuid.UUID]:
    if not u_val:
        return None
    if isinstance(u_val, uuid.UUID):
        return u_val
    try:
        return uuid.UUID(str(u_val))
    except Exception:
        return None


class RemapContext:
    """Manages identifier remapping for CLONE mode."""

    def __init__(self, mode: str, original_project_id: uuid.UUID, new_project_id: Optional[uuid.UUID] = None):
        self.mode = mode.upper()
        self.original_project_id = original_project_id
        self.id_map: Dict[uuid.UUID, uuid.UUID] = {}
        self.entity_type_map: Dict[Tuple[str, uuid.UUID], uuid.UUID] = {}

        if self.mode == "CLONE":
            self.new_project_id = new_project_id or uuid.uuid4()
            self.id_map[original_project_id] = self.new_project_id
        else:
            self.new_project_id = original_project_id

    def get_or_create(self, old_id: Optional[uuid.UUID], entity_type: str = "") -> Optional[uuid.UUID]:
        if old_id is None:
            return None
        if self.mode == "RESTORE":
            return old_id

        if old_id not in self.id_map:
            new_id = uuid.uuid4()
            self.id_map[old_id] = new_id
            if entity_type:
                self.entity_type_map[(entity_type.upper(), old_id)] = new_id
        return self.id_map[old_id]

    def remap_polymorphic(self, entity_type: str, old_entity_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
        if old_entity_id is None:
            return None
        if self.mode == "RESTORE":
            return old_entity_id

        key = (entity_type.upper(), old_entity_id)
        if key in self.entity_type_map:
            return self.entity_type_map[key]
        # Fallback to general id_map
        return self.id_map.get(old_entity_id, old_entity_id)


class ProjectImportService:
    """Orchestrates safe validation and atomic execution of project imports."""

    def __init__(self, storage_provider: Optional[ObjectStorageProvider] = None):
        self.storage = storage_provider or get_storage_provider()

    def validate_project_archive(self, archive_path: str, db: Session) -> Dict[str, Any]:
        """Pre-flights an archive (Phases 1-3) without modifying the database or storage."""
        temp_dir = tempfile.mkdtemp(prefix="orbis_import_val_")
        try:
            # Phase 1: Security inspection & extraction
            zf = ArchiveSecurityValidator.inspect_archive(archive_path)
            try:
                for member in zf.infolist():
                    target = ArchiveSecurityValidator.resolve_safe_extraction_path(temp_dir, member.filename)
                    if member.filename.endswith("/"):
                        os.makedirs(target, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            finally:
                zf.close()

            # Phase 2: Checksum verification
            _, manifest = ArchiveChecksumService.verify_sandbox_checksums(temp_dir)

            # Version check
            archive_version_str = manifest.get("archive_format_version", "1.0.0")
            major_ver = int(archive_version_str.split(".")[0])
            if major_ver not in SUPPORTED_MAJOR_VERSIONS:
                raise VersionIncompatibilityError(
                    f"Archive format version '{archive_version_str}' is not supported (supported: 1.x)"
                )

            # Phase 3: Collision check
            orig_proj_id_str = manifest.get("project", {}).get("original_project_id")
            orig_proj_id = parse_uuid(orig_proj_id_str)
            collision = False
            if orig_proj_id and db.get(Project, orig_proj_id):
                collision = True

            allowed_modes = ["CLONE"]
            if not collision:
                allowed_modes.append("RESTORE")

            return {
                "valid": True,
                "archive_format_version": archive_version_str,
                "schema_version": manifest.get("schema_version", "1.0.0"),
                "source_project_id": orig_proj_id_str,
                "title": manifest.get("project", {}).get("title"),
                "video_mode": manifest.get("project", {}).get("video_mode"),
                "entity_counts": manifest.get("entity_counts", {}),
                "assets_summary": manifest.get("assets_summary", {}),
                "collision_detected": collision,
                "allowed_modes": allowed_modes,
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def execute_import(
        self,
        db: Session,
        archive_path: str,
        import_mode: str = "CLONE",
        override_title: Optional[str] = None,
    ) -> Project:
        """Executes full import pipeline (Phases 1-4) with atomic rollback and compensation."""
        import_mode = import_mode.upper()
        if import_mode not in ("CLONE", "RESTORE"):
            raise ArchiveImportError(f"Invalid import mode '{import_mode}'. Must be 'CLONE' or 'RESTORE'.")

        archive_checksum = ArchiveChecksumService.compute_sha256_file(archive_path)
        temp_dir = tempfile.mkdtemp(prefix="orbis_import_exec_")

        try:
            # Phase 1: Security inspection & extraction
            zf = ArchiveSecurityValidator.inspect_archive(archive_path)
            try:
                for member in zf.infolist():
                    target = ArchiveSecurityValidator.resolve_safe_extraction_path(temp_dir, member.filename)
                    if member.filename.endswith("/"):
                        os.makedirs(target, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            finally:
                zf.close()

            # Phase 2: Checksum verification
            _, manifest = ArchiveChecksumService.verify_sandbox_checksums(temp_dir)

            archive_version_str = manifest.get("archive_format_version", "1.0.0")
            major_ver = int(archive_version_str.split(".")[0])
            if major_ver not in SUPPORTED_MAJOR_VERSIONS:
                raise VersionIncompatibilityError(
                    f"Archive format version '{archive_version_str}' is not supported (supported: 1.x)"
                )

            # Phase 3: Project identity and collision validation
            orig_proj_id = parse_uuid(manifest.get("project", {}).get("original_project_id"))
            if not orig_proj_id:
                raise ArchiveImportError("Missing original_project_id in archive manifest")

            existing_project = db.get(Project, orig_proj_id)
            if import_mode == "RESTORE" and existing_project:
                raise ProjectCollisionError(
                    f"Cannot restore: project '{orig_proj_id}' already exists in database. "
                    "Use CLONE mode to import as a new project."
                )

            # Phase 4: Staged DB mutation & storage upload
            return self._stage_and_commit(
                db=db,
                temp_dir=temp_dir,
                manifest=manifest,
                import_mode=import_mode,
                orig_proj_id=orig_proj_id,
                archive_checksum=archive_checksum,
                override_title=override_title,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _stage_and_commit(
        self,
        db: Session,
        temp_dir: str,
        manifest: Dict[str, Any],
        import_mode: str,
        orig_proj_id: uuid.UUID,
        archive_checksum: str,
        override_title: Optional[str],
    ) -> Project:
        remap = RemapContext(mode=import_mode, original_project_id=orig_proj_id)
        new_project_id = remap.new_project_id
        uploaded_storage_keys: List[Tuple[str, str]] = []

        try:
            # 1. Load project.json
            with open(os.path.join(temp_dir, "project.json"), "r", encoding="utf-8") as f:
                project_raw = json.load(f)

            title = override_title
            if not title:
                if import_mode == "CLONE":
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                    title = f"{project_raw.get('title', 'Project')} (Imported {date_str})"
                else:
                    title = project_raw.get("title", "Project")

            mode_config = project_raw.get("mode_config") or {}
            if import_mode == "CLONE":
                mode_config["clone_lineage"] = {
                    "source_project_id": str(orig_proj_id),
                    "source_archive_checksum": archive_checksum,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }

            imported_project = Project(
                id=new_project_id,
                title=title,
                description=project_raw.get("description"),
                status=project_raw.get("status", "DRAFT"),
                video_mode=project_raw.get("video_mode", "STORY"),
                automation_mode=project_raw.get("automation_mode", "MANUAL"),
                purpose=project_raw.get("purpose"),
                target_platform=project_raw.get("target_platform"),
                target_duration_seconds=project_raw.get("target_duration_seconds"),
                preferred_aspect_ratio=project_raw.get("preferred_aspect_ratio"),
                mode_config=mode_config,
                default_config=project_raw.get("default_config"),
                budget_limit=project_raw.get("budget_limit"),
                budget_currency=project_raw.get("budget_currency", "USD"),
                budget_threshold_percentage=project_raw.get("budget_threshold_percentage", 80.0),
                source_project_id=orig_proj_id if import_mode == "CLONE" else None,
                source_archive_checksum=archive_checksum,
                imported_at=datetime.now(timezone.utc),
                created_at=parse_datetime(project_raw.get("created_at")) or datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(imported_project)

            # 2. Upload and register Assets
            assets_manifest_path = os.path.join(temp_dir, "assets", "manifest.json")
            assets_catalog: Dict[str, Any] = {}
            if os.path.exists(assets_manifest_path):
                with open(assets_manifest_path, "r", encoding="utf-8") as f:
                    assets_catalog = json.load(f)

            assets_json_path = os.path.join(temp_dir, "entities", "assets.json")
            assets_raw: List[Dict[str, Any]] = []
            if os.path.exists(assets_json_path):
                with open(assets_json_path, "r", encoding="utf-8") as f:
                    assets_raw = json.load(f)

            bucket = settings.S3_BUCKET_NAME if hasattr(settings, "S3_BUCKET_NAME") and settings.S3_BUCKET_NAME else "orbis-studio-assets"

            for a_raw in assets_raw:
                old_aid = parse_uuid(a_raw["id"])
                new_aid = remap.get_or_create(old_aid, "ASSET")
                orig_filename = a_raw.get("original_filename", "asset.bin")

                # Fresh storage key
                new_storage_key = f"projects/{new_project_id}/assets/{new_aid}/{orig_filename}"

                # Upload binary if present in archive
                catalog_entry = assets_catalog.get(str(old_aid))
                if catalog_entry:
                    rel_data_path = catalog_entry["relative_path"]
                    local_binary_path = os.path.join(temp_dir, rel_data_path)
                    if os.path.exists(local_binary_path):
                        content_type = catalog_entry.get("content_type", "application/octet-stream")
                        self.storage.upload_file_object(bucket, new_storage_key, local_binary_path, content_type)
                        uploaded_storage_keys.append((bucket, new_storage_key))

                asset_record = Asset(
                    id=new_aid,
                    project_id=new_project_id,
                    name=a_raw.get("name", orig_filename),
                    original_filename=orig_filename,
                    asset_type=a_raw.get("asset_type", "REFERENCE"),
                    content_type=a_raw.get("content_type", "application/octet-stream"),
                    file_size_bytes=a_raw.get("file_size_bytes", 0),
                    checksum_sha256=a_raw.get("checksum_sha256", ""),
                    storage_bucket=bucket,
                    storage_key=new_storage_key,
                    is_locked=a_raw.get("is_locked", False),
                    created_at=parse_datetime(a_raw.get("created_at")) or datetime.now(timezone.utc),
                    updated_at=parse_datetime(a_raw.get("updated_at")) or datetime.now(timezone.utc),
                )
                db.add(asset_record)

            # 3. Document Extractions
            doc_ext_path = os.path.join(temp_dir, "entities", "document_extractions.json")
            if os.path.exists(doc_ext_path):
                with open(doc_ext_path, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                for d in docs:
                    db.add(DocumentExtraction(
                        id=remap.get_or_create(parse_uuid(d["id"]), "DOCUMENT_EXTRACTION"),
                        asset_id=remap.get_or_create(parse_uuid(d["asset_id"]), "ASSET"),
                        raw_text=d.get("raw_text", ""),
                        segments=d.get("segments"),
                        character_count=d.get("character_count", 0),
                        token_count=d.get("token_count", 0),
                        created_at=parse_datetime(d.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 4. Story & Story Versions
            story_path = os.path.join(temp_dir, "entities", "story.json")
            if os.path.exists(story_path):
                with open(story_path, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                story_raw = s_data.get("story")
                if story_raw:
                    old_sid = parse_uuid(story_raw["id"])
                    new_sid = remap.get_or_create(old_sid, "STORY")
                    db.add(Story(
                        id=new_sid,
                        project_id=new_project_id,
                        title=story_raw.get("title", ""),
                        premise=story_raw.get("premise"),
                        synopsis=story_raw.get("synopsis"),
                        target_duration=story_raw.get("target_duration"),
                        target_audience=story_raw.get("target_audience"),
                        visual_style=story_raw.get("visual_style"),
                        logline=story_raw.get("logline"),
                        version_number=story_raw.get("version_number", 1),
                        status=story_raw.get("status", "DRAFT"),
                        is_locked=story_raw.get("is_locked", False),
                        created_at=parse_datetime(story_raw.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(story_raw.get("updated_at")) or datetime.now(timezone.utc),
                    ))

                for sv in s_data.get("story_versions", []):
                    db.add(StoryVersion(
                        id=remap.get_or_create(parse_uuid(sv["id"]), "STORY_VERSION"),
                        story_id=remap.get_or_create(parse_uuid(sv["story_id"]), "STORY"),
                        project_id=new_project_id,
                        version_number=sv.get("version_number", 1),
                        title=sv.get("title", ""),
                        logline=sv.get("logline"),
                        synopsis=sv.get("synopsis"),
                        character_profiles=sv.get("character_profiles"),
                        world_setting=sv.get("world_setting"),
                        style_rules=sv.get("style_rules"),
                        status=sv.get("status", "SUPERSEDED"),
                        created_at=parse_datetime(sv.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 5. Scenes
            scenes_path = os.path.join(temp_dir, "entities", "scenes.json")
            if os.path.exists(scenes_path):
                with open(scenes_path, "r", encoding="utf-8") as f:
                    scenes_raw = json.load(f)
                for sc in scenes_raw:
                    old_scid = parse_uuid(sc["id"])
                    new_scid = remap.get_or_create(old_scid, "SCENE")
                    db.add(Scene(
                        id=new_scid,
                        project_id=new_project_id,
                        scene_number=sc.get("scene_number", 1),
                        heading=sc.get("heading"),
                        description=sc.get("description") or sc.get("summary"),
                        purpose=sc.get("purpose") or sc.get("narrative_intent"),
                        setting=sc.get("setting"),
                        duration_seconds=sc.get("duration_seconds") or sc.get("estimated_duration_seconds"),
                        narration=sc.get("narration"),
                        dialogue=sc.get("dialogue"),
                        scene_config=sc.get("scene_config"),
                        is_locked=sc.get("is_locked", False),
                        created_at=parse_datetime(sc.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(sc.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 6. Shots
            shots_path = os.path.join(temp_dir, "entities", "shots.json")
            if os.path.exists(shots_path):
                with open(shots_path, "r", encoding="utf-8") as f:
                    shots_raw = json.load(f)
                for sh in shots_raw:
                    old_shid = parse_uuid(sh["id"])
                    new_shid = remap.get_or_create(old_shid, "SHOT")
                    db.add(Shot(
                        id=new_shid,
                        scene_id=remap.get_or_create(parse_uuid(sh.get("scene_id")), "SCENE"),
                        shot_number=sh.get("shot_number", 1),
                        shot_type=sh.get("shot_type", "AI_GENERATED"),
                        camera=sh.get("camera") or sh.get("camera_movement"),
                        subject=sh.get("subject"),
                        action=sh.get("action"),
                        duration_seconds=float(sh.get("duration_seconds") or 4.0),
                        visual_prompt=sh.get("visual_prompt"),
                        image_prompt=sh.get("image_prompt"),
                        video_prompt=sh.get("video_prompt"),
                        source_asset_id=remap.get_or_create(parse_uuid(sh.get("source_asset_id")), "ASSET"),
                        keyframe_asset_id=remap.get_or_create(parse_uuid(sh.get("keyframe_asset_id")), "ASSET"),
                        source_metadata=sh.get("source_metadata"),
                        provider_config=sh.get("provider_config"),
                        status=sh.get("status", "DRAFT"),
                        is_locked=sh.get("is_locked", False),
                        created_at=parse_datetime(sh.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(sh.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 7. Reference Library
            ref_path = os.path.join(temp_dir, "entities", "reference_library.json")
            if os.path.exists(ref_path):
                with open(ref_path, "r", encoding="utf-8") as f:
                    ref_data = json.load(f)
                for pr in ref_data.get("project_references", []):
                    db.add(ProjectReference(
                        id=remap.get_or_create(parse_uuid(pr["id"]), "PROJECT_REFERENCE"),
                        project_id=new_project_id,
                        asset_id=remap.get_or_create(parse_uuid(pr["asset_id"]), "ASSET"),
                        category=pr.get("category", "OTHER"),
                        tags=pr.get("tags"),
                        meta_info=pr.get("meta_info"),
                        created_at=parse_datetime(pr.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for cb in ref_data.get("character_bibles", []):
                    db.add(CharacterBible(
                        id=remap.get_or_create(parse_uuid(cb["id"]), "CHARACTER_BIBLE"),
                        project_id=new_project_id,
                        name=cb.get("name", ""),
                        description=cb.get("description"),
                        prompt_triggers=cb.get("prompt_triggers"),
                        reference_asset_ids=[str(remap.get_or_create(parse_uuid(aid), "ASSET")) for aid in (cb.get("reference_asset_ids") or [])],
                        negative_prompt_triggers=cb.get("negative_prompt_triggers"),
                        is_locked=cb.get("is_locked", False),
                        created_at=parse_datetime(cb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(cb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for lb in ref_data.get("location_bibles", []):
                    db.add(LocationBible(
                        id=remap.get_or_create(parse_uuid(lb["id"]), "LOCATION_BIBLE"),
                        project_id=new_project_id,
                        name=lb.get("name", ""),
                        description=lb.get("description"),
                        prompt_triggers=lb.get("prompt_triggers"),
                        reference_asset_ids=[str(remap.get_or_create(parse_uuid(aid), "ASSET")) for aid in (lb.get("reference_asset_ids") or [])],
                        negative_prompt_triggers=lb.get("negative_prompt_triggers"),
                        is_locked=lb.get("is_locked", False),
                        created_at=parse_datetime(lb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(lb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for sb in ref_data.get("style_bibles", []):
                    db.add(StyleBible(
                        id=remap.get_or_create(parse_uuid(sb["id"]), "STYLE_BIBLE"),
                        project_id=new_project_id,
                        style_name=sb.get("style_name", ""),
                        description=sb.get("description"),
                        prompt_preset=sb.get("prompt_preset"),
                        negative_prompt_preset=sb.get("negative_prompt_preset"),
                        reference_asset_ids=[str(remap.get_or_create(parse_uuid(aid), "ASSET")) for aid in (sb.get("reference_asset_ids") or [])],
                        is_locked=sb.get("is_locked", False),
                        created_at=parse_datetime(sb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(sb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for bb in ref_data.get("brand_bibles", []):
                    db.add(BrandBible(
                        id=remap.get_or_create(parse_uuid(bb["id"]), "BRAND_BIBLE"),
                        project_id=new_project_id,
                        brand_name=bb.get("brand_name", ""),
                        guidelines=bb.get("guidelines"),
                        logo_asset_id=remap.get_or_create(parse_uuid(bb.get("logo_asset_id")), "ASSET"),
                        colors=bb.get("colors"),
                        typography=bb.get("typography"),
                        is_locked=bb.get("is_locked", False),
                        created_at=parse_datetime(bb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(bb.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 8. Asset Locks (Polymorphic entity_id remapping)
            locks_path = os.path.join(temp_dir, "entities", "asset_locks.json")
            if os.path.exists(locks_path):
                with open(locks_path, "r", encoding="utf-8") as f:
                    locks_raw = json.load(f)
                for lk in locks_raw:
                    ent_type = lk.get("entity_type", "")
                    old_eid = parse_uuid(lk.get("entity_id"))
                    new_eid = remap.remap_polymorphic(ent_type, old_eid)
                    db.add(AssetLock(
                        id=remap.get_or_create(parse_uuid(lk["id"]), "ASSET_LOCK"),
                        project_id=new_project_id,
                        entity_type=ent_type,
                        entity_id=new_eid,
                        is_locked=lk.get("is_locked", True),
                        locked_by=lk.get("locked_by", "system"),
                        lock_reason=lk.get("lock_reason") or lk.get("reason"),
                        created_at=parse_datetime(lk.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 9. Audio Plan & Clips
            audio_path = os.path.join(temp_dir, "entities", "audio.json")
            if os.path.exists(audio_path):
                with open(audio_path, "r", encoding="utf-8") as f:
                    aud = json.load(f)
                for ap in aud.get("audio_plans", []):
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

            # 10. Timelines & Assembly
            assembly_path = os.path.join(temp_dir, "entities", "assembly.json")
            if os.path.exists(assembly_path):
                with open(assembly_path, "r", encoding="utf-8") as f:
                    asm = json.load(f)
                for tm in asm.get("timelines", []):
                    db.add(AssemblyTimeline(
                        id=remap.get_or_create(parse_uuid(tm["id"]), "TIMELINE"),
                        project_id=new_project_id,
                        version=tm.get("version", 1),
                        is_active=tm.get("is_active", False),
                        status=tm.get("status", "DRAFT"),
                        total_duration_seconds=tm.get("total_duration_seconds", 0.0),
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

            # 11. QC & Approvals
            qc_path = os.path.join(temp_dir, "entities", "qc.json")
            if os.path.exists(qc_path):
                with open(qc_path, "r", encoding="utf-8") as f:
                    qcd = json.load(f)
                for qr in qcd.get("qc_runs", []):
                    db.add(QCRun(
                        id=remap.get_or_create(parse_uuid(qr["id"]), "QC_RUN"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(qr["timeline_id"]), "TIMELINE"),
                        timeline_version=qr.get("timeline_version", 1),
                        status=qr.get("status", "PASSED"),
                        findings_count=qr.get("findings_count", 0),
                        created_at=parse_datetime(qr.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(qr.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for qf in qcd.get("qc_findings", []):
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
                for app in qcd.get("approvals", []):
                    db.add(ApprovalRecord(
                        id=remap.get_or_create(parse_uuid(app["id"]), "APPROVAL_RECORD"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(app["timeline_id"]), "TIMELINE"),
                        timeline_version=app.get("timeline_version", 1),
                        qc_run_id=remap.get_or_create(parse_uuid(app["qc_run_id"]), "QC_RUN"),
                        status=app.get("status", "APPROVED"),
                        approved_by=app.get("approved_by", "operator"),
                        notes=app.get("notes"),
                        approved_at=parse_datetime(app.get("approved_at")) or datetime.now(timezone.utc),
                        created_at=parse_datetime(app.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(app.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 12. Render Batches & Render Jobs (PRESERVE STATUS, FENCE WITH imported_historical=True)
            rj_path = os.path.join(temp_dir, "entities", "render_jobs.json")
            if os.path.exists(rj_path):
                with open(rj_path, "r", encoding="utf-8") as f:
                    rjd = json.load(f)
                for rb in rjd.get("render_batches", []):
                    db.add(RenderBatch(
                        id=remap.get_or_create(parse_uuid(rb["id"]), "RENDER_BATCH"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(rb["timeline_id"]), "TIMELINE"),
                        timeline_version=rb.get("timeline_version", 1),
                        status=rb.get("status", "COMPLETED"),
                        total_variants=rb.get("total_variants", 1),
                        completed_variants=rb.get("completed_variants", 1),
                        failed_variants=rb.get("failed_variants", 0),
                        estimated_total_cost_usd=rb.get("estimated_total_cost_usd", 0.0),
                        created_at=parse_datetime(rb.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(rb.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for rj in rjd.get("render_jobs", []):
                    # Preserve original status, but mark execution_disabled and clear worker leases
                    db.add(RenderJob(
                        id=remap.get_or_create(parse_uuid(rj["id"]), "RENDER_JOB"),
                        project_id=new_project_id,
                        timeline_id=remap.get_or_create(parse_uuid(rj["timeline_id"]), "TIMELINE"),
                        timeline_version=rj.get("timeline_version", 1),
                        approval_id=remap.get_or_create(parse_uuid(rj["approval_id"]), "APPROVAL_RECORD"),
                        batch_id=remap.get_or_create(parse_uuid(rj.get("batch_id")), "RENDER_BATCH"),
                        render_profile=rj.get("render_profile", "MASTER_HD"),
                        render_variant_key=rj.get("render_variant_key", "MASTER"),
                        status=rj.get("status", "COMPLETED"),
                        idempotency_key=f"imported_{rj.get('idempotency_key') or uuid.uuid4()}",
                        output_asset_id=remap.get_or_create(parse_uuid(rj.get("output_asset_id")), "ASSET"),
                        progress=rj.get("progress", 1.0),
                        claimed_by=None,
                        claim_token=None,
                        claim_expires_at=None,
                        retry_count=rj.get("retry_count", 0),
                        max_retries=rj.get("max_retries", 3),
                        estimated_cost_usd=rj.get("estimated_cost_usd", 0.0),
                        actual_cost_usd=rj.get("actual_cost_usd"),
                        error_message=rj.get("error_message"),
                        current_usage_ledger_id=None,
                        render_metadata=rj.get("render_metadata"),
                        imported_historical=True,
                        execution_disabled=True,
                        created_at=parse_datetime(rj.get("created_at")) or datetime.now(timezone.utc),
                        started_at=parse_datetime(rj.get("started_at")),
                        completed_at=parse_datetime(rj.get("completed_at")),
                        updated_at=parse_datetime(rj.get("updated_at")) or datetime.now(timezone.utc),
                    ))

            # 13. Generation Jobs & Batch Runs (PRESERVE STATUS, FENCE WITH imported_historical=True)
            gj_path = os.path.join(temp_dir, "entities", "generation_jobs.json")
            if os.path.exists(gj_path):
                with open(gj_path, "r", encoding="utf-8") as f:
                    gjd = json.load(f)
                for gj in gjd.get("generation_jobs", []):
                    db.add(GenerationJob(
                        id=remap.get_or_create(parse_uuid(gj["id"]), "GENERATION_JOB"),
                        shot_id=remap.get_or_create(parse_uuid(gj["shot_id"]), "SHOT"),
                        job_type=gj.get("job_type", "VIDEO"),
                        provider_name=gj.get("provider_name", "vidu"),
                        provider_job_id=gj.get("provider_job_id"),
                        status=gj.get("status", "COMPLETED"),
                        idempotency_key=f"imported_{gj.get('idempotency_key') or uuid.uuid4()}",
                        error_message=gj.get("error_message"),
                        retry_count=gj.get("retry_count", 0),
                        max_retries=gj.get("max_retries", 3),
                        claimed_by=None,
                        claim_token=None,
                        claim_expires_at=None,
                        submission_attempt_id=None,
                        payload=gj.get("payload"),
                        result=gj.get("result"),
                        output_asset_id=remap.get_or_create(parse_uuid(gj.get("output_asset_id")), "ASSET"),
                        imported_historical=True,
                        execution_disabled=True,
                        created_at=parse_datetime(gj.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(gj.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for br in gjd.get("batch_runs", []):
                    db.add(BatchRun(
                        id=remap.get_or_create(parse_uuid(br["id"]), "BATCH_RUN"),
                        project_id=new_project_id,
                        total_shots=br.get("total_shots", 0),
                        dispatched_shots=br.get("dispatched_shots", 0),
                        skipped_shots=br.get("skipped_shots", 0),
                        failed_shots=br.get("failed_shots", 0),
                        created_at=parse_datetime(br.get("created_at")) or datetime.now(timezone.utc),
                    ))
                for bri in gjd.get("batch_run_items", []):
                    db.add(BatchRunItem(
                        id=remap.get_or_create(parse_uuid(bri["id"]), "BATCH_RUN_ITEM"),
                        batch_run_id=remap.get_or_create(parse_uuid(bri["batch_run_id"]), "BATCH_RUN"),
                        shot_id=remap.get_or_create(parse_uuid(bri["shot_id"]), "SHOT"),
                        job_id=remap.get_or_create(parse_uuid(bri.get("job_id")), "GENERATION_JOB"),
                        status=bri.get("status", "DISPATCHED"),
                        skip_reason=bri.get("skip_reason"),
                        created_at=parse_datetime(bri.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 14. Usage Ledger & Adjustments (PRESERVE COSTS, FENCE WITH imported_historical=True)
            ul_path = os.path.join(temp_dir, "history", "usage_ledger.json")
            if os.path.exists(ul_path):
                with open(ul_path, "r", encoding="utf-8") as f:
                    uld = json.load(f)
                for ul in uld.get("entries", []):
                    db.add(UsageLedger(
                        id=remap.get_or_create(parse_uuid(ul["id"]), "USAGE_LEDGER"),
                        project_id=new_project_id,
                        shot_id=remap.get_or_create(parse_uuid(ul.get("shot_id")), "SHOT"),
                        job_id=remap.get_or_create(parse_uuid(ul.get("job_id")), "GENERATION_JOB"),
                        render_job_id=remap.get_or_create(parse_uuid(ul.get("render_job_id")), "RENDER_JOB"),
                        provider=ul.get("provider", "vidu"),
                        operation=ul.get("operation", "VIDEO_GENERATION"),
                        model=ul.get("model"),
                        usage_units=ul.get("usage_units"),
                        estimated_cost=ul.get("estimated_cost"),
                        actual_cost=ul.get("actual_cost"),
                        currency=ul.get("currency", "USD"),
                        cost_status=ul.get("cost_status", "CONFIRMED"),
                        provider_event_id=ul.get("provider_event_id"),
                        idempotency_key=f"imported_{ul.get('idempotency_key') or uuid.uuid4()}",
                        description=ul.get("description"),
                        imported_historical=True,
                        created_at=parse_datetime(ul.get("created_at")) or datetime.now(timezone.utc),
                        updated_at=parse_datetime(ul.get("updated_at")) or datetime.now(timezone.utc),
                    ))
                for adj in uld.get("adjustments", []):
                    db.add(LedgerAdjustment(
                        id=remap.get_or_create(parse_uuid(adj["id"]), "LEDGER_ADJUSTMENT"),
                        ledger_id=remap.get_or_create(parse_uuid(adj.get("ledger_id") or adj.get("ledger_entry_id")), "USAGE_LEDGER"),
                        previous_cost=adj.get("previous_cost") or adj.get("previous_actual_cost", 0.0),
                        adjusted_cost=adj.get("adjusted_cost") or adj.get("new_actual_cost", 0.0),
                        reason=adj.get("reason", "Imported historical adjustment"),
                        actor=adj.get("actor") or adj.get("adjusted_by", "system"),
                        created_at=parse_datetime(adj.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # 15. History & Audits
            oa_path = os.path.join(temp_dir, "history", "orchestration_audit.json")
            if os.path.exists(oa_path):
                with open(oa_path, "r", encoding="utf-8") as f:
                    oas = json.load(f)
                for oa in oas:
                    db.add(OrchestrationAudit(
                        id=remap.get_or_create(parse_uuid(oa["id"]), "ORCHESTRATION_AUDIT"),
                        project_id=new_project_id,
                        from_stage=oa.get("from_stage"),
                        to_stage=oa.get("to_stage", "DRAFT"),
                        actor=oa.get("actor", "system"),
                        event_type=oa.get("event_type", "STAGE_TRANSITION"),
                        meta_info=oa.get("meta_info"),
                        created_at=parse_datetime(oa.get("created_at")) or datetime.now(timezone.utc),
                    ))

            ga_path = os.path.join(temp_dir, "history", "generation_audit.json")
            if os.path.exists(ga_path):
                with open(ga_path, "r", encoding="utf-8") as f:
                    gas = json.load(f)
                for ga in gas:
                    db.add(GenerationAuditLog(
                        id=remap.get_or_create(parse_uuid(ga["id"]), "GENERATION_AUDIT_LOG"),
                        project_id=new_project_id,
                        shot_id=remap.get_or_create(parse_uuid(ga.get("shot_id")), "SHOT"),
                        provider_name=ga.get("provider_name", "vidu"),
                        operation=ga.get("operation", "VIDEO"),
                        status=ga.get("status", "SUCCESS"),
                        latency_ms=ga.get("latency_ms"),
                        tokens_used=ga.get("tokens_used"),
                        request_payload=ga.get("request_payload"),
                        response_payload=ga.get("response_payload"),
                        created_at=parse_datetime(ga.get("created_at")) or datetime.now(timezone.utc),
                    ))

            ta_path = os.path.join(temp_dir, "history", "timeline_audits.json")
            if os.path.exists(ta_path):
                with open(ta_path, "r", encoding="utf-8") as f:
                    tas = json.load(f)
                for ta in tas:
                    db.add(TimelineAudit(
                        id=remap.get_or_create(parse_uuid(ta["id"]), "TIMELINE_AUDIT"),
                        timeline_id=remap.get_or_create(parse_uuid(ta["timeline_id"]), "TIMELINE"),
                        action=ta.get("action", "UPDATE"),
                        details=ta.get("details"),
                        created_at=parse_datetime(ta.get("created_at")) or datetime.now(timezone.utc),
                    ))

            # Commit the atomic transaction
            db.commit()
            db.refresh(imported_project)
            logger.info(f"Successfully imported project '{imported_project.id}' in mode {import_mode}")
            return imported_project

        except Exception as e:
            db.rollback()
            logger.error(f"Import failed during staged execution: {str(e)}. Compensating storage uploads...")
            # Storage compensation: purge newly uploaded S3 objects
            for b, k in uploaded_storage_keys:
                try:
                    self.storage.delete_object(b, k)
                except Exception as del_err:
                    logger.warning(f"Failed to delete compensated storage object '{k}' in bucket '{b}': {del_err}")
            raise ArchiveImportError(f"Import failed during staged execution: {str(e)}") from e
